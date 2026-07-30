import random
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from enums.order_enums import OrderStatus
from models.account_models import AddressModel, ProfileModel
from models.cart_models import CartModel
from models.order_models import OrderItemModel, OrderModel, OrderStatusEventModel

SHIPPING_FEES = {
    "standard": 3000,
    "express": 6000,
}
FREE_SHIPPING_OVER = 150000


@login_required(login_url="login")
def checkout(request):
    profile = ProfileModel.objects.filter(user=request.user).first()
    if not profile:
        profile = ProfileModel.objects.create(user=request.user)

    cart_obj = CartModel.objects.filter(user=request.user, is_active=True).first()
    if not cart_obj:
        messages.info(request, "Your cart is empty.")
        return redirect("cart")

    items = cart_obj.items.all()
    if items.count() == 0:
        messages.info(request, "Your cart is empty.")
        return redirect("cart")

    subtotal = cart_obj.subtotal

    default_address = AddressModel.objects.filter(
        user=request.user, is_default=True
    ).first()
    if not default_address:
        default_address = AddressModel.objects.filter(user=request.user).first()

    if request.method == "GET":
        shipping_fee = SHIPPING_FEES["standard"]
        if subtotal >= FREE_SHIPPING_OVER:
            shipping_fee = 0

        return render(
            request,
            "website/checkout.html",
            {
                "items": items,
                "subtotal": subtotal,
                "shipping_fee": shipping_fee,
                "total": subtotal + shipping_fee,
                "shipping_fees": SHIPPING_FEES,
                "default_address": default_address,
                "profile_phone": profile.phone,
            },
        )

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        address = (request.POST.get("address") or "").strip()
        city = (request.POST.get("city") or "").strip()
        region = (request.POST.get("region") or "").strip()
        notes = (request.POST.get("notes") or "").strip()
        shipping_method = request.POST.get("shipping") or "standard"
        payment_method = request.POST.get("payment") or "cod"

        if not email or not phone or not first_name or not address or not city or not region:
            messages.error(request, "Please fill in all required fields.")
            shipping_fee = SHIPPING_FEES["standard"]
            if subtotal >= FREE_SHIPPING_OVER:
                shipping_fee = 0
            return render(
                request,
                "website/checkout.html",
                {
                    "items": items,
                    "subtotal": subtotal,
                    "shipping_fee": shipping_fee,
                    "total": subtotal + shipping_fee,
                    "shipping_fees": SHIPPING_FEES,
                    "default_address": default_address,
                    "profile_phone": profile.phone,
                },
            )

        shipping_fee = SHIPPING_FEES.get(shipping_method, 3000)
        if subtotal >= FREE_SHIPPING_OVER and shipping_method == "standard":
            shipping_fee = 0

        order_number = "DN-" + "".join(random.choices(string.digits, k=5))
        while OrderModel.objects.filter(order_number=order_number).count() > 0:
            order_number = "DN-" + "".join(random.choices(string.digits, k=5))

        order = OrderModel.objects.create(
            user=request.user,
            order_number=order_number,
            status=OrderStatus.CONFIRMED,
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            address=address,
            city=city,
            region=region,
            notes=notes,
            shipping_method=shipping_method,
            payment_method=payment_method,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total=subtotal + shipping_fee,
        )

        for item in items:
            variant_label = ""
            if item.variant:
                variant_label = f"{item.variant.color} / {item.variant.size}"

            sku = item.product.sku
            if item.variant:
                sku = item.variant.sku

            OrderItemModel.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                product_name=item.product.name,
                variant_label=variant_label,
                sku=sku,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )

        OrderStatusEventModel.objects.create(
            order=order,
            status=OrderStatus.CONFIRMED,
            note="Order placed",
        )

        cart_obj.items.all().delete()

        messages.success(request, "Order placed successfully.")
        return redirect("order_success", order_id=order.order_number)

    return redirect("checkout")


@login_required(login_url="login")
def order_success(request, order_id):
    order = OrderModel.objects.filter(
        order_number=order_id, user=request.user
    ).first()
    if not order:
        return render(request, "website/404.html", status=404)

    return render(request, "website/order_success.html", {"order": order})
