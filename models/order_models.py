from django.contrib.auth.models import User
from django.db import models

from enums.order_enums import OrderStatus, PaymentMethod, ShippingMethod
from models.base_models import BaseModel
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
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    region = models.CharField(max_length=120)
    notes = models.TextField(blank=True)
    shipping_method = models.CharField(
        max_length=20,
        choices=ShippingMethod.choices,
        default=ShippingMethod.STANDARD,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
    )
    subtotal = models.BigIntegerField(default=0)
    shipping_fee = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number


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
