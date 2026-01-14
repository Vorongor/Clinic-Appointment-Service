from django.db import models


class Specialization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.SlugField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
