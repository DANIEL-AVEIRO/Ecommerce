from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.text import slugify
from models.base_models import BaseModel


class CategoryModel(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)


class ProductModel(BaseModel):
    category = models.ForeignKey(
        CategoryModel,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    regular_price = models.BigIntegerField()
    sale_price = models.BigIntegerField(blank=True, null=True)
    sku = models.CharField(max_length=64, unique=True)
    material = models.CharField(max_length=120, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for image in list(self.images.all()):
            image.delete()
        super().delete(*args, **kwargs)

    @property
    def is_on_sale(self):
        if self.sale_price is None:
            return False
        if self.sale_price < self.regular_price:
            return True
        return False

    @property
    def selling_price(self):
        if self.is_on_sale:
            return self.sale_price
        return self.regular_price

    @property
    def total_stock(self):
        total = 0
        for variant in self.variants.filter(is_active=True):
            total = total + variant.stock
        return total

    @property
    def in_stock(self):
        if self.variants.filter(is_active=True).count() > 0:
            return self.total_stock > 0
        return True

    @property
    def primary_image_url(self):
        images = list(self.images.all())
        if not images:
            return ""
        for image in images:
            if image.is_primary and image.image:
                return image.image.url
        if images[0].image:
            return images[0].image.url
        return ""


class ProductImageModel(BaseModel):
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["sort_order", "created_at"]

    def __str__(self):
        return f"{self.product.name} image"

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)


class ProductVariantModel(BaseModel):
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    color = models.CharField(max_length=64)
    color_hex = models.CharField(max_length=7, blank=True)
    size = models.CharField(max_length=16)
    sku = models.CharField(max_length=64, unique=True)
    stock = models.PositiveIntegerField(default=0)
    price_override = models.BigIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        ordering = ["color", "size"]
        unique_together = [("product", "color", "size")]

    def __str__(self):
        return f"{self.product.name} — {self.color} / {self.size}"

    @property
    def price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.selling_price

    @property
    def in_stock(self):
        return self.stock > 0


class ProductReviewModel(BaseModel):
    product = models.ForeignKey(
        ProductModel,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveIntegerField(default=5)
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.rating} stars"


@receiver(pre_delete, sender=CategoryModel)
def delete_category_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)


@receiver(pre_delete, sender=ProductImageModel)
def delete_product_image_file(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)
