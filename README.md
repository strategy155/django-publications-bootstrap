[![Python](https://img.shields.io/badge/Python-3.4,3.5,3.6-blue.svg?style=flat-square)](/)
[![Django](https://img.shields.io/badge/Django-1.10,1.11-blue.svg?style=flat-square)](/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](/LICENSE)
# Bootstrap-powered scientific publications for Django

A Django app for managing scientific publications, providing a Bootstrap-powered UI.


## Screenshots

[![frontend][3]][1]
[![backend][4]][2]

[1]: https://raw.githubusercontent.com/mbourqui/django-publications-bootstrap/media/frontend.png
[2]: https://raw.githubusercontent.com/lucastheis/django-publications/media/backend.png
[3]: https://raw.githubusercontent.com/mbourqui/django-publications-bootstrap/media/frontend_small.png
[4]: https://raw.githubusercontent.com/lucastheis/django-publications/media/backend_small.png


## Features

* automatically creates lists for individual authors and tags
* BibTex import/export
* RIS export (EndNote, Reference Manager)
* unAPI support (Zotero)
* customizable publication categories/BibTex entry types
* PDF upload
* RSS feeds
* support for images
* embeddable references
* in-text citations, inspired by LaTeX
* automatic bibliography, inspired by LaTeX


## Requirements

* Python >= 3.4
* Django >= 1.10
* Pillow >= 2.4.0
* django-countries >= 4.0
* django-ordered-model >= 1.4.1
* six >= 1.10.0
* Bootstrap v4.0.0-beta
* django-echoices >= 2.2.5


## Installation

1. Run `pip install django-publications-bootstrap`.

1. Add `publications-bootstrap` to the `INSTALLED_APPS` in your project's settings (usually `settings.py`).

1. Add the following to your project's `urls.py`:

        url(r'^publications/', include('publications_bootstrap.urls')),

1. Run `./manage.py migrate publications_bootstrap`.

1. In your project's base template, make sure the following blocks are available in the `<head>` tag:
    * `head`, to provide xml content
    * `css`, to provide CSS specific to this application
  
    The content itself will be inserted in the `content` block.


## Credits

This is a fork [django-publications-bootstrap](https://github.com/mbourqui/django-publications-bootstrap) 
of a fork of [django-publications](https://github.com/lucastheis/django-publications) from
[lucastheis](https://github.com/lucastheis).
The bibtex-import was derived (and modified) from 
[christianglodt] (https://github.com/christianglodt/django-publications)
