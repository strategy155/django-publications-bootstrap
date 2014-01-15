__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from django.core.management.base import BaseCommand
from django.db import transaction

from publications.utils import import_bibtex

from pprint import pprint

class Command(BaseCommand):
    help = u'Imports a BibTeX file into django-publications.'

    def handle(self, *args, **options):
        with file(args[0], 'rb') as f:
            with transaction.atomic():
                publications, errors = import_bibtex(f)

        print 'Imported %i Publication(s)' % len(publications)    
        pprint(errors)
            
