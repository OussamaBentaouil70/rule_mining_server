from django.db import models

class Owner(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=100)
    fonction = models.CharField(max_length=100)

    def __str__(self):
        return self.username

class Member(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=100)
    fonction = models.CharField(max_length=100)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='members')

    def __str__(self):
        return self.username

class Rule(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    tag = models.CharField(max_length=50)

    def __str__(self):
        return self.name
