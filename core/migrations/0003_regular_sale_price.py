from django.db import migrations, models


def move_prices_forward(apps, schema_editor):
    Product = apps.get_model("core", "ProductModel")
    for product in Product.objects.all():
        old_price = product.price
        old_compare = product.compare_at_price
        if old_compare is not None and old_compare > old_price:
            product.regular_price = old_compare
            product.sale_price = old_price
        else:
            product.regular_price = old_price
            product.sale_price = None
        product.save()


def move_prices_backward(apps, schema_editor):
    Product = apps.get_model("core", "ProductModel")
    for product in Product.objects.all():
        if product.sale_price is not None and product.sale_price < product.regular_price:
            product.price = product.sale_price
            product.compare_at_price = product.regular_price
        else:
            product.price = product.regular_price
            product.compare_at_price = None
        product.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_store_features"),
    ]

    operations = [
        migrations.AddField(
            model_name="productmodel",
            name="regular_price",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="productmodel",
            name="sale_price",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(move_prices_forward, move_prices_backward),
        migrations.RemoveField(
            model_name="productmodel",
            name="price",
        ),
        migrations.RemoveField(
            model_name="productmodel",
            name="compare_at_price",
        ),
    ]
