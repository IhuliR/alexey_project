from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TextDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='documents')
    title = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f'Документ {self.id}'


class Label(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#ffff00')

    def __str__(self):
        return self.name


class Annotation(models.Model):
    document = models.ForeignKey(TextDocument, on_delete=models.CASCADE,
                                 related_name='annotations')
    label = models.ForeignKey(Label, on_delete=models.PROTECT)
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.label.name}: {self.text[:30]}...'
