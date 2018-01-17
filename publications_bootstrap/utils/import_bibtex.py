# -*- encoding: utf-8 -*-

__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io> and Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from publications_bootstrap.models import Publication, Type
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import author, keyword
from django.forms.models import model_to_dict
from django.core.exceptions import FieldDoesNotExist

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

def _fix_text_grouping(record):
    '''Turns \text{\'e} into the correct \text{{\'e}} (\text{} being the amsmath command).
    '''

    def wrap_in_group_re_clble(match):
        return '{%s}' % match

    def wrap_in_group(text):
        return re.sub(r'''(\\text{)(\\.*?)(})''', lambda match: match.expand(r'\1{\2}\3'), text)

    for key, value in record.items():

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

    # BibTexParser expects a utf-8 byte-string or unicode
    #if isinstance(bibtex, str):
        #bibtex = bibtex.encode('utf-8')

    if isinstance(bibtex, bytes):
        bibtex = bibtex.decode('utf-8')

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

        if 'title' in entry and \
           'author' in entry and \
           'year' in entry and \
            entry['year'] != None:

            # join parsed authors
            def reverse_and_unseparate_name(n):
                if ',' in n:
                    return ' '.join([p.strip() for p in n.split(',')][::-1])
                return n
            author = entry.pop('author', [])
            authors = ', '.join([reverse_and_unseparate_name(n) for n in author])


            citekey = entry.pop('ID', '')

            # map month
            entry['month'] = MONTHS.get(entry['month'].lower(), 0)

            # determine type
            type_id = None

            reftype = entry.pop('ENTRYTYPE', '')
            for t in types:
                if reftype in t.bibtex_type_list:
                    type_id = t.id
                    break

            if type_id is None:
                errors.append('Type "' + reftype + '" unknown.')
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

            keywords = entry.pop('keywords', [])
            keywords.extend(entry.pop('tags', []))
            tags = ', '.join(keywords)

            file = entry.pop('file')
            if file and not 'pdf' in entry:
                entry['pdf'] = file

            fields_to_skip = []
            for field in entry:
                try:
                    _ = Publication._meta.get_field(field)
                except FieldDoesNotExist:
                    fields_to_skip.append(field)
            for field in fields_to_skip:
                entry.pop(field)

            publication_data = dict(
                type_id=type_id,
                authors=authors,
                #citekey=citekey,
                tags=tags,
                **entry
                )

            publication = Publication(**publication_data)
            try:
                converted_data = model_to_dict(publication,
                                               exclude=['lists',
                                                        'image',
                                                        'pdf',
                                                        'banner',
                                                        'id',
                                                        'citekey'])
                publication = Publication.objects.get(**converted_data)
                saved_publications.append(publication)
            except Publication.DoesNotExist:
                publication.citekey = citekey
                try:
                    publication.save()
                    saved_publications.append(publication)
                except Exception as e:
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
