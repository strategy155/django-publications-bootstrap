__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io> and Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from publications.models import Publication, Type
from cStringIO import StringIO
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode, author, keyword
from django.forms.models import model_to_dict
import latexcodec, re

# mapping of months
MONTHS = {
	'jan': 1, 'january': 1,
	'feb': 2, 'february': 2,
	'mar': 3, 'march': 3,
	'apr': 4, 'april': 4,
	'may': 5,
	'jun': 6, 'june': 6,
	'jul': 7, 'july': 7,
	'aug': 8, 'august': 8,
	'sep': 9, 'september': 9,
	'oct': 10, 'october': 10,
	'nov': 11, 'november': 11,
	'dec': 12, 'december': 12}

def _replace_escaped_spaces(string):
	return string.replace(r'\ ', ' ')

def _ungroup_latex(string):
	'''Strip curly braces from a string, except for backslash-escaped ones.'''
	
	strip_unescaped_braces_regex = r'''
		(?<!\\) # not a backslash
		({)		# followed by an open curly brace
		|		# or
		(?<!\\)	# not a backslash
		(})		# followed by a closed curly brace
		'''
	string = re.sub(strip_unescaped_braces_regex, '', string, flags=re.VERBOSE)
	
	# replace escaped curly braces with unescaped ones. 
	return string.replace(r'\{', '{').replace(r'\}', '}')

def _try_latex_to_utf8(string):
	try:
		return string.encode('utf-8').decode('latex+utf-8')
	except ValueError:
		return string

def _latex_to_text(string):
	string = _try_latex_to_utf8(string)
	string = _ungroup_latex(string)
	string = _replace_escaped_spaces(string)
	return string

def _delatex(record):
	for key in record:
		val = record[key]
		if isinstance(val, list):
			val = [_latex_to_text(part) for part in val]
		else:
			val = _latex_to_text(val)
		record[key] = val
	return record

def _bibtexparser_customizations(record):
	record = convert_to_unicode(record)
	record = author(record)
	record = keyword(record)
	record = _delatex(record)
	return record

def import_bibtex(bibtex):
	'''
	Import BibTeX data from a file-like object or a string
	'''
	
	# BibTexParser expects a utf-8 byte-string
	if isinstance(bibtex, unicode):
		bibtex = StringIO(bibtex.encode('utf-8'))
	elif isinstance(bibtex, str):
		bibtex = StringIO(bibtex)
		
	# try to parse BibTex
	bib = BibTexParser(bibtex, customization=_bibtexparser_customizations).get_entry_list()

	# container for error messages
	errors = []

	# publication types
	types = Type.objects.all()

	publications = []

	integer_keys = [
		'volume',
		'number',
		'year']

	# try adding publications
	for entry in bib:
		
		# first fix integers - 'year' needs to be checked for int-ness in particular
		for key in integer_keys:
			try:
				val = int(entry.get(key, ''))
				entry[key] = val
			except ValueError:
				entry[key] = None

		if entry.has_key('title') and \
		   entry.has_key('author') and \
		   entry.has_key('year') and \
		   entry['year'] != None:
			
			# join parsed authors
			def reverse_and_unseparate_name(n):
				if ',' in n:
					return ' '.join([p.strip() for p in n.split(',')][::-1])
				return n			
			authors = ', '.join([reverse_and_unseparate_name(n) for n in entry['author']])
			
			# add missing keys
			keys = [
				'journal',
				'booktitle',
				'publisher',
				'institution',
				'url',
				'doi',
				'isbn',
				'keywords',
				'note',
				'abstract',
				'month']

			for key in keys:
				if not entry.has_key(key):
					entry[key] = u''

			# map month
			entry['month'] = MONTHS.get(entry['month'].lower(), 0)

			# determine type
			type_id = None

			for t in types:
				if entry['type'] in t.bibtex_type_list:
					type_id = t.id
					break

			if type_id is None:
				errors.append('Type "' + entry['type'] + '" unknown.')
				continue
			
			# Handle case where 'Volume' key contains DOI reference
			volume = entry.get('volume', None)
			if volume:
				try:
					int(volume)
				except ValueError:
					if 'doi' in volume.lower():
						entry['doi'] = entry['volume']
					entry['volume'] = None

			# Handle case where 'Number' key is not a number (eg. {-})
			number = entry.get('number', None)
			if number:
				try:
					int(number)
				except ValueError:
					entry['number'] = None


			publication_data = dict(type_id=type_id,
				title=unicode(entry['title']),
				authors=unicode(authors),
				year=entry['year'],
				month=entry['month'],
				journal=unicode(entry['journal']),
				book_title=unicode(entry['booktitle']),
				publisher=unicode(entry['publisher']),
				institution=unicode(entry['institution']),
				volume=entry['volume'],
				number=entry['number'],
				note=unicode(entry['note']),
				url=unicode(entry['url']),
				doi=unicode(entry['doi']),
				isbn=unicode(entry['isbn']),
				abstract=unicode(entry['abstract']),
				keywords=unicode(u', '.join(entry['keywords'])))
			
			publication = Publication(**publication_data)
			try:
				converted_data = model_to_dict(publication, exclude=['lists', 'image', 'pdf', 'banner', 'id', 'citekey'])
				publication = Publication.objects.get(**converted_data)
			except Publication.DoesNotExist:
				publication.citekey = entry['id']
				publication.save()
			
			# add publication
			publications.append(publication)
		else:
			key = entry['id'] if 'id' in entry else '<unnamed>'
			errors.append('BibTeX entry "%s" is missing mandatory key "title", "author" or "year".' % key)
			continue

	# save publications
	saved_publications = []
	for publication in publications:
		try:
			publication.save()
			saved_publications.append(publication)
		except Exception, e:
			# show error message
			key = publication.citekey
			if not key:
				key = '<unnamed>'
			errors.append('An error occurred saving publication "%s": %s' % (key, e))
			break

	return saved_publications, errors
