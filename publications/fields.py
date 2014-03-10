__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io> and Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from django import forms
from django.forms import widgets
from django.db.models import ManyToManyField, Field
from django.db.models.signals import post_save, m2m_changed
import re
import publications.models

class PagesWidget(widgets.MultiWidget):
	def __init__(self, *args, **kwargs):
		attrs = {'style': 'width: 40px; text-align: center;'}
		forms.widgets.MultiWidget.__init__(self,
			[widgets.TextInput(attrs), widgets.TextInput(attrs)], *args, **kwargs)


	def format_output(self, rendered_widgets):
		to = ' <span style="vertical-align: middle;">to</span> '
		return rendered_widgets[0] + to + rendered_widgets[1]


	def decompress(self, value):
		if value:
			values = value.split('-')

			if len(values) > 1:
				return values
			if len(values) > 0:
				return [values[0], values[0]]
		return [None, None]


class PagesForm(forms.MultiValueField):
	widget = PagesWidget

	def __init__(self, *args, **kwargs):
		forms.MultiValueField.__init__(self, [
			forms.IntegerField(),
			forms.IntegerField()], *args, **kwargs)


	def compress(self, data_list):
		if data_list:
			if data_list[0] and data_list[1]:
				if data_list[0] == data_list[1]:
					return str(data_list[0])
				return str(data_list[0]) + '-' + str(data_list[1])
			if data_list[0]:
				return str(data_list[0])
			if data_list[1]:
				return str(data_list[1])
		return ''


class PagesField(Field):
	def formfield(self, **kwargs):
		kwargs['form_class'] = PagesForm
		return Field.formfield(self, **kwargs)


	def get_internal_type(self):
		return 'CharField'

def latex_citekey_extractor(latex):
	if not latex:
		return
	cite_sets = re.findall(r'.*?\\cite{(.*?)}.*?', latex)
	for cite_set in cite_sets:
		for cite in cite_set.split(','):
			yield cite.strip()

class CitationsField(ManyToManyField):
	'''A many-to-many field pointing to publications.Citation objects that
	   automatically maintains a collection of Citation objects that correspond
	   to citations (ie. mentions of a citekey) in the value of a given field
	   (as determined by an extractor function).
	   
	   Example
	   -------
	   Given a model for a book chapter:
	    
	       class Chapter(models.Model):
	           text = models.TextField()
	   
	   you can add a CitationsField:
	   
	           text_citations = CitationsField('text')
	       
	   and thereafter you can use text_citations like a ManyToManyField that
	   points to publications.Citation objects (one for each citekey mentioned
	   in the 'text' of the chapter). The Citation objects have a 'publication'
	   field that will point to the first Publication with the corresponding citekey
	   (or None if no Publication has that citekey). The CitationsField maintains
	   the collection of Citation objects automatically when the text of the chapter
	   changes, or when the Publications themselves change.
	'''
	
	_publication_save_listener_connected = False
	
	def __init__(self, text_field_name, citekey_extractor=latex_citekey_extractor, **kwargs):
		'''@param text_field_name: the name of the field in which to look for citations
		   @type text_field_name: str or unicode
		   @param citekey_extractor: a function that takes the value of the field named by 'text_field_name'
		                              as parameter and returns a list of citekeys. The default
		                              function parses LaTeX citations (eg. \\cite{key}). 
		   @type citekey_extractor: callable returning a list of strings or unicode objects.
		   @return a new CitationsField
		'''
		kwargs.update(to='publications.Citation', blank=True)
		ManyToManyField.__init__(self, **kwargs)

		self.text_field_name = text_field_name
		self.citekey_extractor = citekey_extractor
		self._is_updating_m2m = False

	def contribute_to_class(self, cls, name):
		ManyToManyField.contribute_to_class(self, cls, name)
		
		# Connect a post_save signal that will handle regular calls of the save() method
		# of cls instances. This will not produce a correct result when an instance
		# is saved in the admin interface. In that case, the m2m_changed signal will
		# fix the problem. 
		post_save.connect(self._instance_saved, sender=cls)
		
		# Connect an m2m_changed signal that will handle saves done through the
		# admin interface. In such a save, during post_save signal, the m2m field
		# is empty, and thus we can't remove obsolete Citation instances.
		m2m_changed.connect(self._m2m_changed, sender=self.rel.through)
		
		# Connect another post_save signal that will update Citation objects
		# when a Publication object changes.
		if not CitationsField._publication_save_listener_connected:
			# This is required only once, not for each instance of CitationField
			post_save.connect(self._publication_saved, sender=publications.models.Publication)
			CitationsField._publication_save_listener_connected = True

	def _m2m_changed(self, sender, instance, action, **kwargs):
		# Prevent infinite recursion due to being notified of our own changes.
		if self._is_updating_m2m:
			return

		if action == 'pre_clear':
			# This signal happens after post_save, when the m2m field is about
			# to be rewritten with form data. We delete Citation instances,
			# because we don't want dangling Citations that are not in a relation
			# with some model object through a CitationsField.
			manager = getattr(instance, self.name)
			manager.all().delete()
			return 

		# required because of admin behaviour (change of m2m fields after save of instance)
		if action == 'post_clear':
			# This signal happens at the end of a save operation in the model admin, and
			# after the changes to the m2m field. We reset the m2m field references to
			# citation objects.
			try:
				self._is_updating_m2m = True
				self._update_citations(instance)
			finally:
				self._is_updating_m2m = False
		
	def _instance_saved(self, instance, **kwargs):
		# Prevent infinite recursion due to being notified of our own changes.
		if self._is_updating_m2m:
			return
		
		try:
			self._is_updating_m2m = True
			self._update_citations(instance)
		finally:
			self._is_updating_m2m = False
		
	def _update_citations(self, instance):
		text = getattr(instance, self.text_field_name)
		manager = getattr(instance, self.name)
		
		# Find citekeys in the given field using the given citekey_extractor
		citekeys = self.citekey_extractor(text)

		# Delete existing citation objects		
		manager.all().delete()
		manager.clear()
		
		citations = []
		for key in citekeys:
			# Create a Citation object for each citekey
			pub = None
			
			# We use the first Publication with a matching citekey
			db_pubs = publications.models.Publication.objects.filter(citekey=key)
			if db_pubs:
				pub = db_pubs.first()
			
			citation = publications.models.Citation(citekey=key, field_name=self.text_field_name, publication=pub)
			citation.save()
			citations.append(citation)
		# Add all citations in one go
		manager.add(*citations)

	def _publication_saved(self, instance, **kwargs):
		# When a publication changes, we change Citation instances that point to it via their citekey.
		
		publication = instance
		# Update those citations that point to this publication but whose
		# citekey does no longer match. Set their publication to None.
		# (Note: qs.update() does not call Citation.save() and does not emit signals).
		publications.models.Citation.objects.filter(publication=publication).exclude(citekey=publication.citekey).update(publication=None)

		# Update those citations that have a matching citekey but which
		# don't point to the correct publication.
		publications.models.Citation.objects.filter(citekey=publication.citekey).exclude(publication=publication).update(publication=publication)

try:
	from south.modelsinspector import add_introspection_rules
	add_introspection_rules([], ["^publications\.fields\.PagesField"])
	add_introspection_rules([([CitationsField], [], { 'text_field_name' : ('text_field_name', {}) })], ["^publications\.fields\.CitationsField"])
except:
	pass
