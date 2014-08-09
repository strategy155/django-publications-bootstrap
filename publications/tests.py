# -*- encoding: utf-8 -*-

from django.test import TestCase
from publications.utils import import_bibtex

class UnicodeCharMacroTestCase(TestCase):
    
    fixtures = ('initial_data.json', )

    def test_import_and_rendering_biber_compatible(self):
        '''orbilu.uni.lu exports BibTeX data in which unicode characters have
        been replaced with LaTeX macros, and wrapped in \text{}, but incorrectly.
        
        For example, \text{\^e} is used to produce the 'ê' character. The grouping
        is incorrect in this, as the character macro should have braces, and the
        \text command as well, ie. it should be \text{{\^e}}.
        
        For reasons of simplicity, we fix this case with a bibtexparser customization
        in import_bibtex. This test checks for that. 
        '''
        
        bibtex = ur'''
@article{10993/15381,
    title = {Faster Print on Demand for Pr\text{\^e}t \text{\`a} Voter},
    author = {Culnane, C. and Heather, J. and Joaquim, R. and Ryan, P. and Schneider, S. and Teague, V.},
    abstract = {Printing Pr\text{\^e}t \text{\`a} Voter ballots on demand is desirable both for convenience and security. It allows a polling station to serve numerous different ballots, and it avoids many problems associated with the custody of the printouts. This paper describes a new proposal for printing Pr\text{\^e}t \text{\`a} Voter ballots on demand. The emphasis is on computational efficiency suitable for real elections, and on very general ballot types.},
    organization = {UK Engineering and Physical Sciences Research Council and Fonds National de la Recherche - FnR},
    publisher = {USENIX},
    year = 2013,
    url = {https://www.usenix.org/jets/issues/0201}
}
        '''
        
        pubs, errors = import_bibtex(bibtex)
        
        self.assertEqual(len(pubs), 1, errors)
        self.assertEqual(len(errors), 0)
        
        pub = pubs[0]
        
        self.assertEqual(pub.title, ur'''Faster Print on Demand for Pr\text{{\^e}}t \text{{\`a}} Voter''')
