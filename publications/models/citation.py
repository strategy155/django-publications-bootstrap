# -*- coding: utf-8 -*-

__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Christian Glodt <chris@mind.lu>'
__docformat__ = 'epytext'

from django.db import models
from publications.models import Publication

class Citation(models.Model):
    
    class Meta:
        app_label = 'publications'
        verbose_name_plural = 'Citations'
    
    citekey = models.CharField(max_length=256, blank=False, null=False)
    field_name = models.CharField(max_length=256, blank=False, null=False)
    publication = models.ForeignKey(Publication, blank=True, null=True)

    def __repr__(self):
        return '<Citation citekey=%r field_name=%r publication=%r>' % (self.citekey, self.field_name, self.publication)
    
    def __str__(self):
        return repr(self)