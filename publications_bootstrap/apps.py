from django.apps import AppConfig
from django.conf import settings


class PublicationsBootstrapConfig(AppConfig):
    name = 'publications_bootstrap'
    verbose_name = "Управление библиографией"

    # TODO: check if dependencies are met

    defaults = {}
    for param in ['bibliography', 'citation', 'marker', 'sorting']:
        try:
            defaults[param] = getattr(settings, '{}_{}'.format(name.upper(), param.upper()))
        except AttributeError:
            pass
