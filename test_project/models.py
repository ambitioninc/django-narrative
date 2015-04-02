from django.db import models
import six


@six.python_2_unicode_compatible
class TestModel(models.Model):
    def __str__(self):
        return 'TestModel-{0}'.format(self.pk)
