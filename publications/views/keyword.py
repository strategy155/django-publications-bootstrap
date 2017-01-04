# -*- coding: utf-8 -*-

__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__authors__ = ['Lucas Theis <lucas@theis.io>', 'Marc Bourqui']
__docformat__ = 'epytext'

from django.shortcuts import render

from publications.models import Publication
from publications.utils import populate


def keyword(request, keyword):
    keyword = keyword.lower().replace(' ', '+')
    candidates = Publication.objects.filter(keywords__icontains=keyword.split('+')[0], external=False)
    publications = []

    for i, publication in enumerate(candidates):
        if keyword in [k[1] for k in publication.keywords_escaped()]:
            publications.append(publication)

    if 'plain' in request.GET:
        return render(request, 'publications/export/publications.txt', {
            'publications': publications
        }, content_type='text/plain; charset=UTF-8')

    if 'bibtex' in request.GET:
        return render(request, 'publications/export/publications.bib', {
            'publications': publications
        }, content_type='text/x-bibtex; charset=UTF-8')

    if 'mods' in request.GET:
        return render(request, 'publications/export/publications.mods', {
            'publications': publications
        }, content_type='application/xml; charset=UTF-8')

    if 'ris' in request.GET:
        return render(request, 'publications/export/publications.ris', {
            'publications': publications
        }, content_type='application/x-research-info-systems; charset=UTF-8')

    # load custom links and files
    populate(publications)

    return render(request, 'publications/pages/keyword.html', {
        'publications': publications,
        'keyword': keyword.replace('+', ' '),
        'title': "publications for keyword {}".format(keyword.replace('+', ' ')),
    })
