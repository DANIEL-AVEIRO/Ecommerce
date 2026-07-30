from django.db import models


class ContactSubject(models.TextChoices):
    ORDER = "order", "Order support"
    PRODUCT = "product", "Product question"
    RETURNS = "returns", "Returns"
    OTHER = "other", "Other"
