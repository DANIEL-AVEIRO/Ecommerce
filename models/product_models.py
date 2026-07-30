from django.db import models
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


class ProductModel(BaseModel):
    category = models.ForeignKey(
        CategoryModel,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    price = models.BigIntegerField()
    compare_at_price = models.BigIntegerField(
        blank=True,
        null=True,
        help_text="Original price shown when on sale",
    )
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

    @property
    def is_on_sale(self):
        return self.compare_at_price is not None and self.compare_at_price > self.price

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
        return (
            self.price_override
            if self.price_override is not None
            else self.product.price
        )

    @property
    def in_stock(self):
        return self.stock > 0
