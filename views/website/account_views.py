from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from models.account_models import (
    AddressModel,
    ProfileModel,
    WishlistItemModel,
    WishlistModel,
)
from models.cart_models import CartItemModel, CartModel
from models.order_models import OrderModel
from models.product_models import ProductModel


@login_required(login_url="login")
def account_dashboard(request):
    profile = ProfileModel.objects.filter(user=request.user).first()
    if not profile:
        profile = ProfileModel.objects.create(user=request.user)

    wishlist = WishlistModel.objects.filter(user=request.user).first()
    if not wishlist:
        wishlist = WishlistModel.objects.create(user=request.user)

    orders = OrderModel.objects.filter(user=request.user)[:5]

    return render(
        request,
        "website/account/dashboard.html",
        {
            "orders": orders,
            "order_count": OrderModel.objects.filter(user=request.user).count(),
            "wishlist_count": wishlist.items.count(),
            "address_count": AddressModel.objects.filter(user=request.user).count(),
        },
    )


@login_required(login_url="login")
def account_orders(request):
    orders = OrderModel.objects.filter(user=request.user)
    return render(request, "website/account/orders.html", {"orders": orders})


@login_required(login_url="login")
def account_order_detail(request, order_id):
    order = OrderModel.objects.filter(order_number=order_id, user=request.user).first()
    if not order:
        return render(request, "website/404.html", status=404)

    return render(request, "website/account/order_detail.html", {"order": order})


@login_required(login_url="login")
def account_profile(request):
    profile = ProfileModel.objects.filter(user=request.user).first()
    if not profile:
        profile = ProfileModel.objects.create(user=request.user)

    if request.method == "GET":
        return render(request, "website/account/profile.html", {"profile": profile})

    if request.method == "POST":
        user = request.user
        user.first_name = (request.POST.get("first_name") or "").strip()
        user.last_name = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        if email:
            user.email = email
            user.username = email
        user.save()

        profile.phone = (request.POST.get("phone") or "").strip()
        profile.save()

        current_password = request.POST.get("current_password") or ""
        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

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
        return render(
            request, "website/account/addresses.html", {"addresses": addresses}
        )

    if request.method == "POST":
        AddressModel.objects.create(
            user=request.user,
            label=(request.POST.get("label") or "").strip(),
            first_name=(request.POST.get("first_name") or "").strip(),
            last_name=(request.POST.get("last_name") or "").strip(),
            address=(request.POST.get("address") or "").strip(),
            city=(request.POST.get("city") or "").strip(),
            region=(request.POST.get("region") or "").strip(),
            phone=(request.POST.get("phone") or "").strip(),
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
    return render(request, "website/wishlist.html", {"items": items})


@login_required(login_url="login")
def wishlist_add(request):
    if request.method == "GET":
        return redirect("wishlist")

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        next_url = request.POST.get("next") or "wishlist"

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
            unit_price = product.price

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
