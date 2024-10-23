from django.db import models


class Repository(models.Model):
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)


class Analysis(models.Model):
    repository = models.ForeignKey(Repository, on_delete=models.CASCADE)
    recommendations = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
