from django.db import models

from enums.content_enums import ContactSubject
from models.base_models import BaseModel


class ContactMessageModel(BaseModel):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(
        max_length=20,
        choices=ContactSubject.choices,
        default=ContactSubject.OTHER,
    )
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject}"


class NewsletterSubscriberModel(BaseModel):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
