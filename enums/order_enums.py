from django.db import models


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class PaymentMethod(models.TextChoices):
    COD = "cod", "Cash on delivery"
    KBZ = "kbz", "KBZ Pay / Wave Money"
    BANK = "card", "Bank transfer"


class ShippingMethod(models.TextChoices):
    STANDARD = "standard", "Standard"
    EXPRESS = "express", "Express"
