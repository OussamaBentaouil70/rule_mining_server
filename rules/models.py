# models.py
from django.db import models

class Node(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    type = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    description = models.TextField()
    position_x = models.FloatField()
    position_y = models.FloatField()

class Edge(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    source = models.CharField(max_length=100)
    target = models.CharField(max_length=100)
    type = models.CharField(max_length=100)
    label = models.CharField(max_length=100, null=True, blank=True)
