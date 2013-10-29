"""
Admin for platform integration.
"""
from django.contrib.admin import site

from . import models


site.register(models.Datum)
site.register(models.AssertionMeta)
site.register(models.EventMeta)
site.register(models.NarrativeConfig)
