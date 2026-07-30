import mimetypes
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.management.commands.seed_catalog_data import CATEGORIES, PRODUCTS
from models.product_models import (
    CategoryModel,
    ProductImageModel,
    ProductModel,
    ProductVariantModel,
)


class Command(BaseCommand):
    help = "Seed realistic catalog data (30 products) with downloaded images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing catalog data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing catalog…")
            ProductImageModel.objects.all().delete()
            ProductVariantModel.objects.all().delete()
            ProductModel.objects.all().delete()
            CategoryModel.objects.all().delete()

        categories = {}
        for item in CATEGORIES:
            category, created = CategoryModel.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "description": item["description"],
                    "sort_order": item["sort_order"],
                    "is_active": True,
                },
            )
            if not category.image:
                self._attach_image(
                    category,
                    "image",
                    item["image_url"],
                    f"category-{item['slug']}.jpg",
                    title=item["name"],
                )
            categories[item["slug"]] = category
            self.stdout.write(
                f"  category: {category.name} ({'created' if created else 'updated'})"
            )

        created_products = 0
        image_ok = 0
        image_fail = 0

        with transaction.atomic():
            for index, item in enumerate(PRODUCTS, start=1):
                category = categories[item["category"]]
                product, created = ProductModel.objects.update_or_create(
                    slug=item["slug"],
                    defaults={
                        "category": category,
                        "name": item["name"],
                        "sku": item["sku"],
                        "price": item["price"],
                        "compare_at_price": item["compare_at_price"],
                        "material": item["material"],
                        "description": item["description"],
                        "is_featured": item["featured"],
                        "is_active": True,
                    },
                )
                if created:
                    created_products += 1

                for color, hex_code, size in item["variants"]:
                    ProductVariantModel.objects.update_or_create(
                        product=product,
                        color=color,
                        size=size,
                        defaults={
                            "color_hex": hex_code,
                            "sku": f"{product.sku}-{color[:3].upper()}-{size}",
                            "stock": 15 + (index % 20),
                            "is_active": True,
                        },
                    )

                if not product.images.exists():
                    saved = self._create_product_image(
                        product,
                        item["image_url"],
                        f"{item['slug']}.jpg",
                    )
                    if saved:
                        image_ok += 1
                    else:
                        image_fail += 1

                self.stdout.write(f"  [{index:02d}/30] {product.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete — categories: {CategoryModel.objects.count()}, "
                f"products: {ProductModel.objects.count()} "
                f"(new: {created_products}), "
                f"images saved: {image_ok}, failed: {image_fail}"
            )
        )

    def _download(self, url):
        request = Request(
            url,
            headers={"User-Agent": "DANIEL-Store-Seed/1.0"},
        )
        with urlopen(request, timeout=60) as response:
            data = response.read()
            content_type = response.headers.get_content_type()
            if not data or len(data) < 1000:
                raise OSError("Downloaded file too small or empty")
            return data, content_type

    def _generate_image(self, title, size=(800, 1000), color=(45, 74, 62)):
        from io import BytesIO

        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGB", size, color)
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, size[0], int(size[1] * 0.62)], fill=tuple(min(255, c + 25) for c in color))
        draw.rectangle([40, 40, size[0] - 40, size[1] - 40], outline=(255, 255, 255), width=2)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 36)
        except OSError:
            font = ImageFont.load_default()
        text = title[:28]
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((size[0] - tw) / 2, (size[1] - th) / 2),
            text,
            fill=(255, 255, 255),
            font=font,
        )
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue(), "image/jpeg"

    def _load_image_bytes(self, url, title, size=(800, 1000)):
        try:
            return self._download(url)
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            self.stderr.write(f"  download failed, generating local image ({title}): {exc}")
            return self._generate_image(title, size=size)

    def _attach_image(self, instance, field_name, url, filename, title=""):
        try:
            content, content_type = self._load_image_bytes(
                url, title or filename, size=(1200, 800)
            )
            ext = mimetypes.guess_extension(content_type or "") or Path(filename).suffix or ".jpg"
            if not filename.endswith(ext):
                filename = f"{Path(filename).stem}{ext}"
            getattr(instance, field_name).save(
                filename,
                ContentFile(content),
                save=True,
            )
            return True
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            self.stderr.write(f"  image failed ({filename}): {exc}")
            return False

    def _create_product_image(self, product, url, filename):
        try:
            content, content_type = self._load_image_bytes(url, product.name)
            ext = mimetypes.guess_extension(content_type or "") or ".jpg"
            if not filename.endswith(ext):
                filename = f"{Path(filename).stem}{ext}"
            image = ProductImageModel(
                product=product,
                alt_text=product.name,
                is_primary=True,
                sort_order=0,
            )
            image.image.save(filename, ContentFile(content), save=True)
            return True
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            self.stderr.write(f"  product image failed ({product.slug}): {exc}")
            return False
