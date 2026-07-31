from django.db import migrations, models


def move_names_forward(apps, schema_editor):
    Address = apps.get_model("core", "AddressModel")
    Order = apps.get_model("core", "OrderModel")

    for address in Address.objects.all():
        name = address.first_name
        if address.last_name:
            name = name + " " + address.last_name
        address.username = name
        address.save()

    for order in Order.objects.all():
        name = order.first_name
        if order.last_name:
            name = name + " " + order.last_name
        order.username = name
        order.save()


def move_names_backward(apps, schema_editor):
    Address = apps.get_model("core", "AddressModel")
    Order = apps.get_model("core", "OrderModel")

    for address in Address.objects.all():
        parts = address.username.split(" ", 1)
        address.first_name = parts[0]
        if len(parts) > 1:
            address.last_name = parts[1]
        else:
            address.last_name = ""
        address.save()

    for order in Order.objects.all():
        parts = order.username.split(" ", 1)
        order.first_name = parts[0]
        if len(parts) > 1:
            order.last_name = parts[1]
        else:
            order.last_name = ""
        order.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_regular_sale_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="addressmodel",
            name="username",
            field=models.CharField(default="", max_length=150),
        ),
        migrations.AddField(
            model_name="ordermodel",
            name="username",
            field=models.CharField(default="", max_length=150),
        ),
        migrations.RunPython(move_names_forward, move_names_backward),
        migrations.RemoveField(
            model_name="addressmodel",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="addressmodel",
            name="last_name",
        ),
        migrations.RemoveField(
            model_name="ordermodel",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="ordermodel",
            name="last_name",
        ),
    ]
