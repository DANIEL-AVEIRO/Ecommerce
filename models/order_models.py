from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from enums.order_enums import (
    OrderStatus,
    PaymentStatus,
    ReturnStatus,
    ShippingMethod,
)
from models.base_models import BaseModel
from models.content_models import PaymentMethodModel
from models.product_models import ProductModel, ProductVariantModel


class OrderModel(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="orders",
        blank=True,
        null=True,
    )
    order_number = models.CharField(max_length=32, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    username = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    region = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    shipping_method = models.CharField(
        max_length=20,
        choices=ShippingMethod.choices,
        default=ShippingMethod.STANDARD,
    )
    payment_method = models.ForeignKey(
        PaymentMethodModel,
        on_delete=models.SET_NULL,
        related_name="orders",
        blank=True,
        null=True,
    )
    payment_method_name = models.CharField(max_length=80, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_slip = models.ImageField(
        upload_to="payment_slips/",
        blank=True,
        null=True,
    )
    tracking_number = models.CharField(max_length=80, blank=True)
    coupon_code = models.CharField(max_length=40, blank=True)
    discount_amount = models.BigIntegerField(default=0)
    subtotal = models.BigIntegerField(default=0)
    shipping_fee = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def delete(self, *args, **kwargs):
        if self.payment_slip:
            self.payment_slip.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def can_cancel(self):
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]

    @property
    def payment_label(self):
        if self.payment_method_name:
            return self.payment_method_name
        if self.payment_method:
            return self.payment_method.name
        return "—"

    @property
    def needs_payment_slip(self):
        if self.payment_method:
            return self.payment_method.requires_slip
        return False


class OrderItemModel(BaseModel):
    order = models.ForeignKey(
        OrderModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.SET_NULL,
        related_name="order_items",
        blank=True,
        null=True,
    )
    variant = models.ForeignKey(
        ProductVariantModel,
        on_delete=models.SET_NULL,
        related_name="order_items",
        blank=True,
        null=True,
    )
    product_name = models.CharField(max_length=200)
    variant_label = models.CharField(max_length=120, blank=True)
    sku = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.BigIntegerField()
    line_total = models.BigIntegerField()

    class Meta(BaseModel.Meta):
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class OrderStatusEventModel(BaseModel):
    order = models.ForeignKey(
        OrderModel,
        on_delete=models.CASCADE,
        related_name="status_events",
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    note = models.CharField(max_length=255, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number} → {self.status}"


class ReturnRequestModel(BaseModel):
    order = models.ForeignKey(
        OrderModel,
        on_delete=models.CASCADE,
        related_name="return_requests",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="return_requests",
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.PENDING,
    )
    admin_note = models.CharField(max_length=255, blank=True)
    stock_restored = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return f"Return {self.order.order_number}"


@receiver(pre_delete, sender=OrderModel)
def delete_order_payment_slip_file(sender, instance, **kwargs):
    if instance.payment_slip:
        instance.payment_slip.delete(save=False)
