from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render

from core.models import (
    AddressModel,
    CartItemModel,
    CartModel,
    OrderModel,
    OrderStatusEventModel,
    ProductModel,
    ProductVariantModel,
    ProfileModel,
    ReturnRequestModel,
    WishlistItemModel,
    WishlistModel,
)
from enums.order_enums import OrderStatus, PaymentStatus, ReturnStatus


@login_required(login_url="login")
def account_dashboard(request):
    profile = ProfileModel.objects.filter(user=request.user).first()
    if not profile:
        profile = ProfileModel.objects.create(user=request.user)

    wishlist = WishlistModel.objects.filter(user=request.user).first()
    if not wishlist:
        wishlist = WishlistModel.objects.create(user=request.user)

    orders = OrderModel.objects.filter(user=request.user)[:5]

    context = {
        "orders": orders,
        "order_count": OrderModel.objects.filter(user=request.user).count(),
        "wishlist_count": wishlist.items.count(),
        "address_count": AddressModel.objects.filter(user=request.user).count(),
    }
    return render(request, "website/account/dashboard.html", context)


@login_required(login_url="login")
def account_orders(request):
    orders = OrderModel.objects.filter(user=request.user)
    context = {
        "orders": orders,
    }
    return render(request, "website/account/orders.html", context)


@login_required(login_url="login")
def account_order_detail(request, order_id):
    order = OrderModel.objects.filter(order_number=order_id, user=request.user).first()
    if not order:
        return render(request, "website/404.html", status=404)

    context = {
        "order": order,
    }
    return render(request, "website/account/order_detail.html", context)


@login_required(login_url="login")
def account_order_cancel(request, order_id):
    if request.method == "GET":
        return redirect("account_order_detail", order_id=order_id)

    if request.method == "POST":
        order = OrderModel.objects.filter(
            order_number=order_id, user=request.user
        ).first()
        if not order:
            return render(request, "website/404.html", status=404)

        if not order.can_cancel:
            messages.error(request, "This order can no longer be cancelled.")
            return redirect("account_order_detail", order_id=order_id)

        with transaction.atomic():
            for item in order.items.all():
                if item.variant:
                    variant = (
                        ProductVariantModel.objects.filter(id=item.variant.id)
                        .select_for_update()
                        .first()
                    )
                    if variant:
                        variant.stock = variant.stock + item.quantity
                        variant.save()

            order.status = OrderStatus.CANCELLED
            order.save()

            OrderStatusEventModel.objects.create(
                order=order,
                status=OrderStatus.CANCELLED,
                note="Cancelled by customer",
            )
        messages.success(request, "Order cancelled.")
        return redirect("account_order_detail", order_id=order_id)

    return redirect("account_orders")


@login_required(login_url="login")
def account_order_upload_slip(request, order_id):
    if request.method == "GET":
        return redirect("account_order_detail", order_id=order_id)

    if request.method == "POST":
        order = OrderModel.objects.filter(
            order_number=order_id, user=request.user
        ).first()
        if not order:
            return render(request, "website/404.html", status=404)

        if order.payment_method and order.payment_method.is_cod:
            messages.error(request, "COD orders do not need a payment screenshot.")
            return redirect("account_order_detail", order_id=order_id)

        if order.payment_method and not order.payment_method.requires_slip:
            messages.error(request, "This payment method does not need a screenshot.")
            return redirect("account_order_detail", order_id=order_id)

        slip = request.FILES.get("payment_slip")
        if not slip:
            messages.error(request, "Please choose a payment screenshot.")
            return redirect("account_order_detail", order_id=order_id)

        if order.payment_slip:
            order.payment_slip.delete(save=False)

        order.payment_slip = slip
        order.payment_status = PaymentStatus.PENDING
        order.save()
        messages.success(request, "Payment screenshot uploaded. We will confirm soon.")
        return redirect("account_order_detail", order_id=order_id)

    return redirect("account_orders")


@login_required(login_url="login")
def account_return_request(request, order_id):
    order = OrderModel.objects.filter(order_number=order_id, user=request.user).first()
    if not order:
        return render(request, "website/404.html", status=404)

    if request.method == "GET":
        context = {
            "order": order,
        }
        return render(request, "website/account/return_request.html", context)

    if request.method == "POST":
        reason = request.POST.get("reason", "")
        if not reason:
            messages.error(request, "Please explain why you want to return.")
            context = {
                "order": order,
            }
            return render(request, "website/account/return_request.html", context)

        if order.status != OrderStatus.DELIVERED:
            messages.error(request, "Returns are only for delivered orders.")
            return redirect("account_order_detail", order_id=order_id)

        existing = ReturnRequestModel.objects.filter(
            order=order, user=request.user, status=ReturnStatus.PENDING
        ).first()
        if existing:
            messages.info(request, "You already have a pending return for this order.")
            return redirect("account_order_detail", order_id=order_id)

        ReturnRequestModel.objects.create(
            order=order,
            user=request.user,
            reason=reason,
            status=ReturnStatus.PENDING,
        )
        messages.success(request, "Return request submitted.")
        return redirect("account_order_detail", order_id=order_id)

    return redirect("account_orders")


@login_required(login_url="login")
def account_profile(request):
    profile = ProfileModel.objects.filter(user=request.user).first()
    if not profile:
        profile = ProfileModel.objects.create(user=request.user)

    if request.method == "GET":
        context = {
            "profile": profile,
        }
        return render(request, "website/account/profile.html", context)

    if request.method == "POST":
        user = request.user
        username = request.POST.get("username", "")
        email = request.POST.get("email", "").lower()

        if not username:
            messages.error(request, "Username is required.")
            return redirect("account_profile")

        username_taken = User.objects.filter(username=username).first()
        if username_taken and username_taken.id != user.id:
            messages.error(request, "That username is already taken.")
            return redirect("account_profile")

        if email:
            email_taken = User.objects.filter(email=email).first()
            if email_taken and email_taken.id != user.id:
                messages.error(request, "That email is already in use.")
                return redirect("account_profile")
            user.email = email

        user.username = username
        user.save()

        profile.phone = request.POST.get("phone", "")
        profile.save()

        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if current_password or new_password or confirm_password:
            if not user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("account_profile")
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect("account_profile")
            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters.")
                return redirect("account_profile")
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password updated. Please sign in again.")
            return redirect("login")

        messages.success(request, "Profile updated.")
        return redirect("account_profile")

    return redirect("account_profile")


@login_required(login_url="login")
def account_addresses(request):
    addresses = AddressModel.objects.filter(user=request.user)

    if request.method == "GET":
        context = {
            "addresses": addresses,
        }
        return render(request, "website/account/addresses.html", context)

    if request.method == "POST":
        AddressModel.objects.create(
            user=request.user,
            label=request.POST.get("label", ""),
            username=request.POST.get("username", ""),
            address=request.POST.get("address", ""),
            city=request.POST.get("city", ""),
            region=request.POST.get("region", ""),
            phone=request.POST.get("phone", ""),
            is_default=bool(request.POST.get("is_default")),
        )
        messages.success(request, "Address saved.")
        return redirect("account_addresses")

    return redirect("account_addresses")


@login_required(login_url="login")
def account_address_delete(request, address_id):
    if request.method == "GET":
        return redirect("account_addresses")

    if request.method == "POST":
        address = AddressModel.objects.filter(id=address_id, user=request.user).first()
        if address:
            address.delete()
            messages.success(request, "Address removed.")
        return redirect("account_addresses")

    return redirect("account_addresses")


@login_required(login_url="login")
def wishlist(request):
    wishlist_obj = WishlistModel.objects.filter(user=request.user).first()
    if not wishlist_obj:
        wishlist_obj = WishlistModel.objects.create(user=request.user)

    items = wishlist_obj.items.all()
    context = {
        "items": items,
    }
    return render(request, "website/wishlist.html", context)


@login_required(login_url="login")
def wishlist_add(request):
    if request.method == "GET":
        return redirect("wishlist")

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        next_url = request.POST.get("next", "wishlist")

        product = ProductModel.objects.filter(id=product_id, is_active=True).first()
        if not product:
            messages.error(request, "Product not found.")
            return redirect("shop")

        wishlist_obj = WishlistModel.objects.filter(user=request.user).first()
        if not wishlist_obj:
            wishlist_obj = WishlistModel.objects.create(user=request.user)

        existing = WishlistItemModel.objects.filter(
            wishlist=wishlist_obj, product=product
        ).first()
        if not existing:
            WishlistItemModel.objects.create(wishlist=wishlist_obj, product=product)

        messages.success(request, "Saved to wishlist.")
        return redirect(next_url)

    return redirect("wishlist")


@login_required(login_url="login")
def wishlist_remove(request):
    if request.method == "GET":
        return redirect("wishlist")

    if request.method == "POST":
        item_id = request.POST.get("item_id")
        wishlist_obj = WishlistModel.objects.filter(user=request.user).first()
        if wishlist_obj:
            item = WishlistItemModel.objects.filter(
                id=item_id, wishlist=wishlist_obj
            ).first()
            if item:
                item.delete()
                messages.success(request, "Removed from wishlist.")
        return redirect("wishlist")

    return redirect("wishlist")


@login_required(login_url="login")
def wishlist_add_to_cart(request):
    if request.method == "GET":
        return redirect("wishlist")

    if request.method == "POST":
        item_id = request.POST.get("item_id")
        wishlist_obj = WishlistModel.objects.filter(user=request.user).first()
        if not wishlist_obj:
            return redirect("wishlist")

        wish_item = WishlistItemModel.objects.filter(
            id=item_id, wishlist=wishlist_obj
        ).first()
        if not wish_item:
            messages.error(request, "Item not found.")
            return redirect("wishlist")

        cart_obj = CartModel.objects.filter(user=request.user, is_active=True).first()
        if not cart_obj:
            cart_obj = CartModel.objects.create(user=request.user, is_active=True)

        product = wish_item.product
        variant = wish_item.variant
        if variant:
            unit_price = variant.price
        else:
            unit_price = product.selling_price

        cart_item = CartItemModel.objects.filter(
            cart=cart_obj, product=product, variant=variant
        ).first()
        if cart_item:
            cart_item.quantity = cart_item.quantity + 1
            cart_item.unit_price = unit_price
            cart_item.save()
        else:
            CartItemModel.objects.create(
                cart=cart_obj,
                product=product,
                variant=variant,
                quantity=1,
                unit_price=unit_price,
            )

        messages.success(request, "Added to cart.")
        return redirect("cart")

    return redirect("wishlist")
