from django.contrib.auth.models import User
from django.db import models

from models.base_models import BaseModel
from models.product_models import ProductModel, ProductVariantModel


class CartModel(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart ({self.user})"

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItemModel(BaseModel):
    cart = models.ForeignKey(
        CartModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        ProductVariantModel,
        on_delete=models.SET_NULL,
        related_name="cart_items",
        blank=True,
        null=True,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.BigIntegerField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]
        unique_together = [("cart", "product", "variant")]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def save(self, *args, **kwargs):
        if self.unit_price is None:
            if self.variant:
                self.unit_price = self.variant.price
            else:
                self.unit_price = self.product.selling_price
        super().save(*args, **kwargs)

    @property
    def line_total(self):
        return self.unit_price * self.quantity
