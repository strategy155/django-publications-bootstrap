__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io>'
__docformat__ = 'epytext'

from publications.bibtex import parse
from publications.models import Publication, Type
from string import split, join

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

def import_bibtex(bibtex):
	# try to parse BibTex
	bib = parse(bibtex) # always returns a list

	# container for error messages
	errors = []

	# publication types
	types = Type.objects.all()

	publications = []

	# try adding publications
	for entry in bib:
		if entry.has_key('title') and \
		   entry.has_key('author') and \
		   entry.has_key('year'):
			# parse authors
			authors = split(entry['author'], ' and ')
			for i in range(len(authors)):
				author = split(authors[i], ',')
				author = [author[-1]] + author[:-1]
				authors[i] = join(author, ' ')
			authors = join(authors, ', ')

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
					entry[key] = ''

			# map integer fields to integers
			entry['month'] = MONTHS.get(entry['month'].lower(), 0)
			entry['volume'] = entry.get('volume', None)
			entry['number'] = entry.get('number', None)

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

			# add publication
			publications.append(Publication(
				type_id=type_id,
				citekey=entry['key'],
				title=entry['title'],
				authors=authors,
				year=entry['year'],
				month=entry['month'],
				journal=entry['journal'],
				book_title=entry['booktitle'],
				publisher=entry['publisher'],
				institution=entry['institution'],
				volume=entry['volume'],
				number=entry['number'],
				note=entry['note'],
				url=entry['url'],
				doi=entry['doi'],
				isbn=entry['isbn'],
				abstract=entry['abstract'],
				keywords=entry['keywords']))
		else:
			errors.append('BibTeX entry %s is missing mandatory key title, author or year.' % entry['key'])
			continue

	# save publications
	saved_publications = []
	for publication in publications:
		try:
			publication.save()
			saved_publications.append(publication)
		except Exception, e:
			# show error message
			errors.append('An error occurred saving publication %s: %s' % (publication.citekey, e))

	return saved_publications, errors
