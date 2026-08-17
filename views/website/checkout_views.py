import random
import string

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from urllib.parse import urlencode

from enums.order_enums import OrderStatus, PaymentStatus
from core.models import (
    AddressModel,
    CartModel,
    CouponModel,
    OrderItemModel,
    OrderModel,
    OrderStatusEventModel,
    PaymentMethodModel,
    ProductVariantModel,
    ProfileModel,
    ShippingRegionModel,
)

FREE_SHIPPING_OVER = settings.FREE_SHIPPING_OVER


def get_shipping_fees(region_name):
    region = ShippingRegionModel.objects.filter(
        name=region_name, is_active=True
    ).first()
    if region:
        return {
            "standard": region.standard_fee,
            "express": region.express_fee,
        }
    return {
        "standard": 3000,
        "express": 6000,
    }


def find_valid_coupon(coupon_code, subtotal):
    code = coupon_code.strip()
    if not code:
        return None, 0, ""

    coupon = CouponModel.objects.filter(code__iexact=code).first()
    if not coupon:
        return None, 0, "Invalid coupon code."

    if not coupon.is_active:
        return None, 0, "This coupon is no longer active."

    if coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
        return None, 0, "This coupon has reached its usage limit."

    if coupon.expires_at:
        expires_at = coupon.expires_at
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at)
        if timezone.now() > expires_at:
            return None, 0, "This coupon has expired."

    if subtotal < coupon.min_order_amount:
        return (
            None,
            0,
            f"This coupon needs a minimum order of {coupon.min_order_amount} Ks.",
        )

    discount = coupon.calc_discount(subtotal)
    if discount <= 0:
        return None, 0, "This coupon has no discount for your cart."

    return coupon, discount, ""


def send_order_email(request, order):
    subject = f"Order confirmed — {order.order_number}"
    items = order.items.all()

    lines = [
        f"Hi {order.username},",
        "",
        f"Thanks for your order {order.order_number}.",
        f"Status: {order.get_status_display()}",
        f"Payment: {order.payment_label} ({order.get_payment_status_display()})",
        f"Subtotal: {order.subtotal} Ks",
        f"Discount: {order.discount_amount} Ks",
        f"Shipping: {order.shipping_fee} Ks",
        f"Total: {order.total} Ks",
        "",
        "Items:",
    ]
    for item in items:
        label = item.product_name
        if item.variant_label:
            label = f"{label} ({item.variant_label})"
        lines.append(f"- {label} x {item.quantity} = {item.line_total} Ks")

    lines.append("")
    lines.append("Ships to:")
    lines.append(order.username)
    lines.append(order.address)
    lines.append(f"{order.city}, {order.region}")
    lines.append(order.phone)
    lines.append("")
    lines.append("— DANIEL Store")

    body = "\n".join(lines)
    shop_url = request.build_absolute_uri("/shop/")
    order_url = request.build_absolute_uri(
        f"/account/orders/{order.order_number}/"
    )
    html_body = render_to_string(
        "emails/order_confirmation.html",
        {
            "order": order,
            "items": items,
            "shop_url": shop_url,
            "order_url": order_url,
        },
    )

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
            fail_silently=False,
            html_message=html_body,
        )
        return True
    except Exception:
        return False


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

    for item in items:
        if item.variant:
            if item.variant.stock < item.quantity:
                messages.error(
                    request,
                    f"Not enough stock for {item.product.name}. Only {item.variant.stock} left.",
                )
                return redirect("cart")

    subtotal = cart_obj.subtotal

    default_address = AddressModel.objects.filter(
        user=request.user, is_default=True
    ).first()
    if not default_address:
        default_address = AddressModel.objects.filter(user=request.user).first()

    regions = ShippingRegionModel.objects.filter(is_active=True)
    if regions.count() == 0:
        region_names = ["Yangon", "Mandalay", "Naypyidaw", "Other"]
    else:
        region_names = []
        for region in regions:
            region_names.append(region.name)

    payment_methods = PaymentMethodModel.objects.filter(is_active=True)

    selected_region = "Yangon"
    if default_address and default_address.region:
        selected_region = default_address.region

    coupon_code = ""
    discount_amount = 0
    coupon_error = ""
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code", "").strip().upper()
    elif request.GET.get("coupon"):
        coupon_code = request.GET.get("coupon", "").strip().upper()

    if coupon_code:
        coupon, discount_amount, coupon_error = find_valid_coupon(
            coupon_code, subtotal
        )
        if not coupon:
            if request.method == "GET" and request.GET.get("coupon"):
                messages.error(request, coupon_error or "Invalid coupon code.")
            coupon_code = ""
            discount_amount = 0

    shipping_fees = get_shipping_fees(selected_region)
    shipping_fee = shipping_fees["standard"]
    after_discount = subtotal - discount_amount
    if after_discount >= FREE_SHIPPING_OVER:
        shipping_fee = 0
    total = after_discount + shipping_fee

    if request.method == "GET":
        context = {
            "items": items,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "coupon_code": coupon_code,
            "shipping_fee": shipping_fee,
            "total": total,
            "shipping_fees": shipping_fees,
            "region_names": region_names,
            "selected_region": selected_region,
            "default_address": default_address,
            "profile_phone": profile.phone,
            "free_shipping_over": FREE_SHIPPING_OVER,
            "payment_methods": payment_methods,
        }
        return render(request, "website/checkout.html", context)

    if request.method == "POST":
        action = request.POST.get("action", "place_order")

        if action == "apply_coupon":
            typed_code = request.POST.get("coupon_code", "").strip().upper()
            if not typed_code:
                messages.error(request, "Please enter a coupon code.")
                return redirect("checkout")

            coupon, discount_amount, coupon_error = find_valid_coupon(
                typed_code, subtotal
            )
            if coupon and discount_amount > 0:
                messages.success(request, "Coupon applied.")
                query = urlencode({"coupon": coupon.code})
                return redirect("/checkout/?" + query)

            messages.error(request, coupon_error or "Invalid coupon code.")
            return redirect("checkout")

        email = request.POST.get("email", "")
        phone = request.POST.get("phone", "")
        username = request.POST.get("username", "")
        address = request.POST.get("address", "")
        city = request.POST.get("city", "")
        region = request.POST.get("region", "")
        notes = request.POST.get("notes", "")
        shipping_method = request.POST.get("shipping", "standard")
        payment_method_id = request.POST.get("payment", "")
        coupon_code = request.POST.get("coupon_code", "").strip().upper()

        payment_method = PaymentMethodModel.objects.filter(
            id=payment_method_id, is_active=True
        ).first()
        if not payment_method:
            payment_method = PaymentMethodModel.objects.filter(
                is_active=True, is_cod=True
            ).first()
        if not payment_method:
            payment_method = PaymentMethodModel.objects.filter(is_active=True).first()

        shipping_fees = get_shipping_fees(region)
        discount_amount = 0
        coupon = None
        typed_coupon = coupon_code
        if coupon_code:
            coupon, discount_amount, coupon_error = find_valid_coupon(
                coupon_code, subtotal
            )
            if not coupon:
                messages.error(
                    request,
                    coupon_error or "Invalid coupon code.",
                )
                checkout_context = {
                    "items": items,
                    "subtotal": subtotal,
                    "discount_amount": 0,
                    "coupon_code": typed_coupon,
                    "shipping_fee": shipping_fees.get(
                        shipping_method, shipping_fees["standard"]
                    ),
                    "total": subtotal
                    + shipping_fees.get(shipping_method, shipping_fees["standard"]),
                    "shipping_fees": shipping_fees,
                    "region_names": region_names,
                    "selected_region": region or selected_region,
                    "default_address": default_address,
                    "profile_phone": profile.phone,
                    "free_shipping_over": FREE_SHIPPING_OVER,
                    "payment_methods": payment_methods,
                }
                after_discount = subtotal
                shipping_fee = shipping_fees.get(
                    shipping_method, shipping_fees["standard"]
                )
                if after_discount >= FREE_SHIPPING_OVER and shipping_method == "standard":
                    shipping_fee = 0
                checkout_context["shipping_fee"] = shipping_fee
                checkout_context["total"] = after_discount + shipping_fee
                return render(request, "website/checkout.html", checkout_context)
            coupon_code = coupon.code

        shipping_fee = shipping_fees.get(shipping_method, shipping_fees["standard"])
        after_discount = subtotal - discount_amount
        if after_discount >= FREE_SHIPPING_OVER and shipping_method == "standard":
            shipping_fee = 0
        total = after_discount + shipping_fee

        checkout_context = {
            "items": items,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "coupon_code": coupon_code,
            "shipping_fee": shipping_fee,
            "total": total,
            "shipping_fees": shipping_fees,
            "region_names": region_names,
            "selected_region": region or selected_region,
            "default_address": default_address,
            "profile_phone": profile.phone,
            "free_shipping_over": FREE_SHIPPING_OVER,
            "payment_methods": payment_methods,
        }

        if not email or not phone or not username or not address or not city or not region:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "website/checkout.html", checkout_context)

        if not payment_method:
            messages.error(request, "No payment method is available. Please contact the store.")
            return render(request, "website/checkout.html", checkout_context)

        order_number = "DN-" + "".join(random.choices(string.digits, k=5))
        while OrderModel.objects.filter(order_number=order_number).count() > 0:
            order_number = "DN-" + "".join(random.choices(string.digits, k=5))

        if payment_method.is_cod:
            order_status = OrderStatus.CONFIRMED
            payment_status = PaymentStatus.PENDING
        else:
            order_status = OrderStatus.PENDING
            payment_status = PaymentStatus.PENDING

        try:
            with transaction.atomic():
                for item in items:
                    if item.variant:
                        variant = (
                            ProductVariantModel.objects.filter(id=item.variant.id)
                            .select_for_update()
                            .first()
                        )
                        if not variant or variant.stock < item.quantity:
                            raise ValueError(
                                f"Not enough stock for {item.product.name}."
                            )

                order = OrderModel.objects.create(
                    user=request.user,
                    order_number=order_number,
                    status=order_status,
                    email=email,
                    phone=phone,
                    username=username,
                    address=address,
                    city=city,
                    region=region,
                    notes=notes,
                    shipping_method=shipping_method,
                    payment_method=payment_method,
                    payment_method_name=payment_method.name,
                    payment_status=payment_status,
                    coupon_code=coupon_code,
                    discount_amount=discount_amount,
                    subtotal=subtotal,
                    shipping_fee=shipping_fee,
                    total=total,
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

                    if item.variant:
                        variant = (
                            ProductVariantModel.objects.filter(id=item.variant.id)
                            .select_for_update()
                            .first()
                        )
                        variant.stock = variant.stock - item.quantity
                        variant.save()

                if coupon_code:
                    coupon_locked = (
                        CouponModel.objects.filter(code__iexact=coupon_code)
                        .select_for_update()
                        .first()
                    )
                    if coupon_locked and coupon_locked.is_valid_now():
                        if subtotal >= coupon_locked.min_order_amount:
                            coupon_locked.used_count = coupon_locked.used_count + 1
                            coupon_locked.save()

                OrderStatusEventModel.objects.create(
                    order=order,
                    status=order_status,
                    note="Order placed",
                )

                cart_obj.items.all().delete()
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("cart")

        email_ok = send_order_email(request, order)
        if email_ok:
            messages.success(request, "Order placed successfully.")
        else:
            messages.success(request, "Order placed successfully.")
            messages.warning(
                request,
                "Order saved, but the confirmation email could not be sent.",
            )
        return redirect("order_success", order_id=order.order_number)

    return redirect("checkout")


@login_required(login_url="login")
def order_success(request, order_id):
    order = OrderModel.objects.filter(
        order_number=order_id, user=request.user
    ).first()
    if not order:
        return render(request, "website/404.html", status=404)

    context = {
        "order": order,
    }
    return render(request, "website/order_success.html", context)
