from django.contrib.auth.models import User
from django.db import models

from models.base_models import BaseModel
from models.product_models import ProductModel, ProductVariantModel


class ProfileModel(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=32, blank=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.get_username()


class AddressModel(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    region = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        ordering = ["-is_default", "-updated_at"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return self.label or f"{self.first_name} — {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            AddressModel.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)


class WishlistModel(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    class Meta(BaseModel.Meta):
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user.get_username()} wishlist"


class WishlistItemModel(BaseModel):
    wishlist = models.ForeignKey(
        WishlistModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    variant = models.ForeignKey(
        ProductVariantModel,
        on_delete=models.SET_NULL,
        related_name="wishlist_items",
        blank=True,
        null=True,
    )

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]
        unique_together = [("wishlist", "product", "variant")]

    def __str__(self):
        return self.product.name
