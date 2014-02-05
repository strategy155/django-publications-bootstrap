__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io> and Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from django import forms
from django.forms import widgets
from django.db import transaction
from django.db.models import ManyToManyField, Field
from django.db.models.signals import pre_save, post_save, m2m_changed
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
	return re.findall(r'.*?\\cite{(.*?)}.*?', latex)

class CitationsField(ManyToManyField):
	def __init__(self, text_field_name, citekey_extractor=latex_citekey_extractor, **kwargs):
		kwargs.update(to='publications.Citation', blank=True)
		ManyToManyField.__init__(self, **kwargs)

		self.text_field_name = text_field_name
		self.citekey_extractor = citekey_extractor
		self._is_updating_m2m = False

	def contribute_to_class(self, cls, name):
		ManyToManyField.contribute_to_class(self, cls, name)
		post_save.connect(self._instance_saved, sender=cls)
		m2m_changed.connect(self._m2m_changed, sender=self.rel.through)

	def _m2m_changed(self, sender, instance, action, **kwargs):
		if self._is_updating_m2m:
			return

		if action == 'pre_clear':
			manager = getattr(instance, self.name)
			manager.all().delete()
			return 

		# required because of admin behaviour (change of m2m fields after save of instance)
		if action == 'post_add':
			try:
				self._is_updating_m2m = True
				self._update_citations(instance)
			finally:
				self._is_updating_m2m = False
		
	def _instance_saved(self, instance, **kwargs):
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
		
		citekeys = self.citekey_extractor(text)
		
		print 'Deleted', [citation.pk for citation in manager.all()]
		manager.all().delete()
		manager.clear()
		
		for key in citekeys:
			pub = None
			
			db_pubs = publications.models.Publication.objects.filter(citekey=key)
			if db_pubs:
				pub = db_pubs.first()
			
			manager.create(citekey=key, field_name=self.text_field_name, publication=pub)
		print 'Set to', [citation.pk for citation in manager.all()]

try:
	from south.modelsinspector import add_introspection_rules
	add_introspection_rules([], ["^publications\.fields\.PagesField"])
	add_introspection_rules([([CitationsField], [], { 'text_field_name' : ('text_field_name', {}) })], ["^publications\.fields\.CitationsField"])
except:
	pass
