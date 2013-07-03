from django.db import models


class TestModel(models.Model):
    def __unicode__(self):
        return u'TestModel-{0}'.format(self.pk)
