# -*- coding: utf-8 -*-

import re

from django.template import RequestContext
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseRedirect
from django.shortcuts import render

from django.db import transaction

from ..utils import import_bibtex as do_import_bibtex
from ..models import Publication, Type


def import_bibtex(request):
    if request.method == 'POST':
        # try to import BibTex
        publications = parse_upload_bibtex(request)

        # redirect to publication listing
        return HttpResponseRedirect('../')
    else:
        response = get_response(request)
        return response

def get_response(request):
    response = render(request,
                  'admin/publications_bootstrap/import_bibtex.html',
                  {'title': 'Import BibTex',
                   'types': Type.objects.all(),
                   'request': request},
                  )
    return response

def parse_upload_bibtex(request):
    bibtex = request.POST['bibliography']

    with transaction.atomic():
        publications, errors = do_import_bibtex(bibtex)

    status = messages.SUCCESS
    if len(publications) == 0:
        status = messages.ERROR
        msg = 'No publications were added, %i errors occurred' % len(errors)
    elif len(publications) > 1:
        msg = 'Successfully added %i publications (%i skipped due to errors)' % (len(publications), len(errors))
    else:
        msg = 'Successfully added %i publication (%i error(s) occurred)' % (len(publications), len(errors))

    # show message
    messages.add_message(request, status, msg)

    for error in errors:
        messages.add_message(request, messages.ERROR, error)

    return publications

import_bibtex = staff_member_required(import_bibtex)
