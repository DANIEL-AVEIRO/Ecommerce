from django.db import models
from django.utils import timezone

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


class PaymentMethodModel(BaseModel):
    name = models.CharField(max_length=80)
    instructions = models.TextField(blank=True)
    account_info = models.TextField(blank=True)
    requires_slip = models.BooleanField(default=True)
    is_cod = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class CouponModel(BaseModel):
    code = models.CharField(max_length=40, unique=True)
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.BigIntegerField(default=0)
    min_order_amount = models.BigIntegerField(default=0)
    max_uses = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    used_count = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["code"]

    def __str__(self):
        return self.code

    def is_valid_now(self):
        if not self.is_active:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def calc_discount(self, subtotal):
        if not self.is_valid_now():
            return 0
        if subtotal < self.min_order_amount:
            return 0

        discount = 0
        if self.discount_percent > 0:
            discount = int(subtotal * self.discount_percent / 100)
        if self.discount_amount > 0:
            if self.discount_amount > discount:
                discount = self.discount_amount

        if discount > subtotal:
            discount = subtotal
        return discount


class ShippingRegionModel(BaseModel):
    name = models.CharField(max_length=120, unique=True)
    standard_fee = models.BigIntegerField(default=3000)
    express_fee = models.BigIntegerField(default=6000)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["name"]

    def __str__(self):
        return self.name
