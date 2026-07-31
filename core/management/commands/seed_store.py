from django.core.management.base import BaseCommand

from core.models import (
    CategoryModel,
    CouponModel,
    PaymentMethodModel,
    ProductModel,
    ProductVariantModel,
    ShippingRegionModel,
)


class Command(BaseCommand):
    help = "Seed demo categories, products, regions, coupons, and payment methods"

    def handle(self, *args, **options):
        self.seed_payment_methods()
        self.seed_regions()
        self.seed_coupons()
        self.seed_catalog()
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))

    def seed_payment_methods(self):
        defaults = [
            {
                "name": "Cash on delivery",
                "instructions": "Pay with cash when your order arrives.",
                "account_info": "",
                "requires_slip": False,
                "is_cod": True,
                "sort_order": 1,
            },
            {
                "name": "KBZ Pay / Wave Money",
                "instructions": "Transfer the total, then upload a payment screenshot on your order page.",
                "account_info": "09XXXXXXXX",
                "requires_slip": True,
                "is_cod": False,
                "sort_order": 2,
            },
            {
                "name": "Bank transfer",
                "instructions": "Transfer to our bank account, then upload your slip.",
                "account_info": "Bank account details",
                "requires_slip": True,
                "is_cod": False,
                "sort_order": 3,
            },
        ]
        for item in defaults:
            existing = PaymentMethodModel.objects.filter(name=item["name"]).first()
            if existing:
                continue
            PaymentMethodModel.objects.create(
                name=item["name"],
                instructions=item["instructions"],
                account_info=item["account_info"],
                requires_slip=item["requires_slip"],
                is_cod=item["is_cod"],
                is_active=True,
                sort_order=item["sort_order"],
            )
            self.stdout.write(f"  payment method: {item['name']}")

    def seed_regions(self):
        regions = [
            ("Yangon", 3000, 6000),
            ("Mandalay", 4000, 7000),
            ("Naypyidaw", 3500, 6500),
            ("Other", 5000, 9000),
        ]
        for name, standard_fee, express_fee in regions:
            existing = ShippingRegionModel.objects.filter(name=name).first()
            if existing:
                continue
            ShippingRegionModel.objects.create(
                name=name,
                standard_fee=standard_fee,
                express_fee=express_fee,
                is_active=True,
            )
            self.stdout.write(f"  region: {name}")

    def seed_coupons(self):
        existing = CouponModel.objects.filter(code="WELCOME10").first()
        if not existing:
            CouponModel.objects.create(
                code="WELCOME10",
                discount_percent=10,
                discount_amount=0,
                min_order_amount=50000,
                max_uses=100,
                is_active=True,
            )
            self.stdout.write("  coupon: WELCOME10")

    def seed_catalog(self):
        if ProductModel.objects.count() > 0:
            self.stdout.write("  catalog already has products — skipped")
            return

        tops = CategoryModel.objects.filter(slug="tops").first()
        if not tops:
            tops = CategoryModel.objects.create(
                name="Tops",
                slug="tops",
                description="Everyday tops and knits.",
                sort_order=1,
                is_active=True,
            )

        bottoms = CategoryModel.objects.filter(slug="bottoms").first()
        if not bottoms:
            bottoms = CategoryModel.objects.create(
                name="Bottoms",
                slug="bottoms",
                description="Pants and easy layers.",
                sort_order=2,
                is_active=True,
            )

        products = [
            {
                "category": tops,
                "name": "Half-Zip Knit Pullover",
                "slug": "half-zip-knit-pullover",
                "sku": "DN-TOP-001",
                "regular_price": 89000,
                "sale_price": 79000,
                "material": "Cotton blend",
                "description": "A soft half-zip knit for cool evenings.",
                "featured": True,
                "variants": [("Black", "#111111", "M"), ("Ivory", "#F5F0E8", "L")],
            },
            {
                "category": tops,
                "name": "Relaxed Linen Shirt",
                "slug": "relaxed-linen-shirt",
                "sku": "DN-TOP-002",
                "regular_price": 65000,
                "sale_price": None,
                "material": "Linen",
                "description": "Breathable linen shirt for warm Yangon days.",
                "featured": True,
                "variants": [("White", "#FFFFFF", "M"), ("Sage", "#9CAF88", "L")],
            },
            {
                "category": bottoms,
                "name": "Wide Crop Trouser",
                "slug": "wide-crop-trouser",
                "sku": "DN-BTM-001",
                "regular_price": 72000,
                "sale_price": None,
                "material": "Cotton twill",
                "description": "Easy wide-leg crop with a clean front.",
                "featured": False,
                "variants": [("Stone", "#C2B8A3", "M"), ("Navy", "#1F2A44", "L")],
            },
        ]

        for item in products:
            product = ProductModel.objects.create(
                category=item["category"],
                name=item["name"],
                slug=item["slug"],
                sku=item["sku"],
                regular_price=item["regular_price"],
                sale_price=item["sale_price"],
                material=item["material"],
                description=item["description"],
                is_featured=item["featured"],
                is_active=True,
            )
            for color, hex_code, size in item["variants"]:
                ProductVariantModel.objects.create(
                    product=product,
                    color=color,
                    color_hex=hex_code,
                    size=size,
                    sku=f"{product.sku}-{color[:3].upper()}-{size}",
                    stock=20,
                    is_active=True,
                )
            self.stdout.write(f"  product: {product.name}")
