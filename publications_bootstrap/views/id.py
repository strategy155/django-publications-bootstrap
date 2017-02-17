__license__ = 'MIT License <http://www.opensource.org/licenses/mit-license.php>'
__author__ = 'Lucas Theis <lucas@theis.io>'
__docformat__ = 'epytext'

from django.shortcuts import render

from ..models import Publication


def id(request, publication_id):
    try:
        publication = Publication.objects.get(pk=publication_id)

        if 'plain' in request.GET:
            return render(request, 'publications-bootstrap/export/publications-bootstrap.txt', {
                'publications-bootstrap': [publication]
            }, content_type='text/plain; charset=UTF-8')

        if 'bibtex' in request.GET:
            return render(request, 'publications-bootstrap/export/publications-bootstrap.bib', {
                'publications-bootstrap': [publication]
            }, content_type='text/x-bibtex; charset=UTF-8')

        if 'mods' in request.GET:
            return render(request, 'publications-bootstrap/export/publications-bootstrap.mods', {
                'publications-bootstrap': [publication]
            }, content_type='application/xml; charset=UTF-8')

        if 'ris' in request.GET:
            return render(request, 'publications-bootstrap/export/publications-bootstrap.ris', {
                'publications-bootstrap': [publication]
            }, content_type='application/x-research-info-systems; charset=UTF-8')

        publication.links = publication.customlink_set.all()
        publication.files = publication.customfile_set.all()

        return render(request, 'publications-bootstrap/pages/id.html', {
            'publication': publication,
            'title': publication.type,
        })
    except Publication.DoesNotExist:
        return render(request, 'publications-bootstrap/base.html', {
            'error': True,
            'alert': {
                'message': "There is no publication with this id: {}".format(publication_id)},
        }, status=404)