# -*- encoding: utf-8 -*-

__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io> and Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from publications.models import Publication, Type
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import author, keyword
from django.forms.models import model_to_dict

import re

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

special_chars = (
	(r'\"{a}', 'ä'), (r'{\"a}', 'ä'), (r'\"a', 'ä'), (r'H{a}', 'ä'),
	(r'\"{A}', 'Ä'), (r'{\"A}', 'Ä'), (r'\"A', 'Ä'), (r'H{A}', 'Ä'),
	(r'\"{o}', 'ö'), (r'{\"o}', 'ö'), (r'\"o', 'ö'), (r'H{o}', 'ö'),
	(r'\"{O}', 'Ö'), (r'{\"O}', 'Ö'), (r'\"O', 'Ö'), (r'H{O}', 'Ö'),
	(r'\"{u}', 'ü'), (r'{\"u}', 'ü'), (r'\"u', 'ü'), (r'H{u}', 'ü'),
	(r'\"{U}', 'Ü'), (r'{\"U}', 'Ü'), (r'\"U', 'Ü'), (r'H{U}', 'Ü'),
	(r'{‘a}', 'à'), (r'\‘A', 'À'),
	(r'{‘e}', 'è'), (r'\‘E', 'È'),
	(r'{‘o}', 'ò'), (r'\‘O', 'Ò'),
	(r'{‘u}', 'ù'), (r'\‘U', 'Ù'),
	(r'{’a}', 'á'), (r'\’A', 'Á'),
	(r'{’e}', 'é'), (r'\’E', 'É'),
	(r'{’o}', 'ó'), (r'\’O', 'Ó'),
	(r'{’u}', 'ú'), (r'\’U', 'Ú'),
	(r'\`a', 'à'), (r'\`A', 'À'),
	(r'\`e', 'è'), (r'\`E', 'È'),
	(r'\`u', 'ù'), (r'\`U', 'Ù'),
	(r'\`o', 'ò'), (r'\`O', 'Ò'),
	(r'\^o', 'ô'), (r'\^O', 'Ô'),
	(r'\ss', 'ß'),
	(r'\ae', 'æ'), (r'\AE', 'Æ'))

def _fix_text_grouping(record):
	'''Turns \text{\'e} into the correct \text{{\'e}} (\text{} being the amsmath command).
	'''

	def wrap_in_group_re_clble(match):
		return '{%s}' % match

	def wrap_in_group(text):
		return re.sub(r'''(\\text{)(\\.*?)(})''', lambda match: match.expand(r'\1{\2}\3'), text)

	for key, value in record.iteritems():
		if isinstance(value, list):
			new_value = [wrap_in_group(element) for element in value]
		else:
			new_value = wrap_in_group(value)

		record[key] = new_value

	return record

def _bibtexparser_customizations(record):
	record = author(record)
	record = keyword(record)
	record = _fix_text_grouping(record)
	return record

def import_bibtex(bibtex, bibtexparser_customization=None):
	'''
	Import BibTeX data from a file-like object or a string
	'''

	# BibTexParser expects a utf-8 byte-string
	if isinstance(bibtex, unicode):
		bibtex = bibtex.encode('utf-8')

	for key, value in special_chars:
		bibtex = bibtex.replace(key, value)

	# add trailing newline if not present, otherwise bibtexparser will not parse fully
	if not bibtex.endswith('\n'):
		bibtex = bibtex + '\n'

	# try to parse BibTex
	def _cust(record):
		record = _bibtexparser_customizations(record)
		if bibtexparser_customization:
			record = bibtexparser_customization(record)
		return record
	bib = BibTexParser(bibtex, customization=_cust, ignore_nonstandard_types=False).get_entry_list()

	# container for error messages
	errors = []

	# publication types
	types = Type.objects.all()

	integer_keys = [
		'volume',
		'number',
		'year']

	saved_publications = []

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

			# handle case where 'volume' key contains DOI reference
			volume = entry.get('volume', None)

			if volume:
				try:
					int(volume)
				except ValueError:
					if 'doi' in volume.lower():
						entry['doi'] = entry['volume']
					entry['volume'] = None

			# handle case where 'number' key is not a number (eg. {-})
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
				saved_publications.append(publication)

			except Publication.DoesNotExist:
				publication.citekey = entry['id']

				try:
					publication.save()
					saved_publications.append(publication)

				except Exception, e:
					# show error message
					key = publication.citekey
					if not key:
						key = '<unnamed>'
					errors.append('An error occurred saving publication "%s": %s' % (key, e))

		else:
			key = entry['id'] if 'id' in entry else '<unnamed>'
			from pprint import pprint
			pprint(entry)
			missing_keys = []

			for k in ('title', 'author', 'year'):
				if not k in entry or entry[k] == None:
					missing_keys.append(k)

			errors.append('BibTeX entry "%s" is missing following mandatory keys: %s' % (key, ', '.join(missing_keys)))

			continue

	return saved_publications, errors
