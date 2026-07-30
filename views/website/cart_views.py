from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from models.cart_models import CartItemModel, CartModel
from models.product_models import ProductModel, ProductVariantModel


@login_required(login_url="login")
def cart(request):
    cart_obj = CartModel.objects.filter(user=request.user, is_active=True).first()
    if not cart_obj:
        cart_obj = CartModel.objects.create(user=request.user, is_active=True)

    items = cart_obj.items.all()

    if items.count() == 0:
        return render(request, "website/cart_empty.html")

    free_shipping_over = 150000
    subtotal = cart_obj.subtotal
    free_shipping_remaining = free_shipping_over - subtotal
    if free_shipping_remaining < 0:
        free_shipping_remaining = 0

    return render(
        request,
        "website/cart.html",
        {
            "cart": cart_obj,
            "items": items,
            "subtotal": subtotal,
            "free_shipping_over": free_shipping_over,
            "free_shipping_remaining": free_shipping_remaining,
        },
    )


@login_required(login_url="login")
def cart_add(request):
    if request.method == "GET":
        return redirect("shop")

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        quantity = request.POST.get("quantity", "1")
        color = request.POST.get("color", "")
        size = request.POST.get("size", "")
        variant_id = request.POST.get("variant_id")
        next_url = request.POST.get("next") or "cart"

        product = ProductModel.objects.filter(id=product_id, is_active=True).first()
        if not product:
            messages.error(request, "Product not found.")
            return redirect("shop")

        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 1
        if quantity < 1:
            quantity = 1

        cart_obj = CartModel.objects.filter(user=request.user, is_active=True).first()
        if not cart_obj:
            cart_obj = CartModel.objects.create(user=request.user, is_active=True)

        variant = None
        if variant_id:
            variant = ProductVariantModel.objects.filter(
                id=variant_id, product=product, is_active=True
            ).first()
        elif color or size:
            variant_qs = product.variants.filter(is_active=True)
            if color:
                variant_qs = variant_qs.filter(color=color)
            if size:
                variant_qs = variant_qs.filter(size=size)
            variant = variant_qs.first()

        if variant:
            unit_price = variant.price
        else:
            unit_price = product.price

        item = CartItemModel.objects.filter(
            cart=cart_obj, product=product, variant=variant
        ).first()

        if item:
            item.quantity = item.quantity + quantity
            item.unit_price = unit_price
            item.save()
        else:
            CartItemModel.objects.create(
                cart=cart_obj,
                product=product,
                variant=variant,
                quantity=quantity,
                unit_price=unit_price,
            )

        messages.success(request, "Added to cart.")
        return redirect(next_url)

    return redirect("shop")


@login_required(login_url="login")
def cart_update(request):
    if request.method == "GET":
        return redirect("cart")

    if request.method == "POST":
        item_id = request.POST.get("item_id")
        quantity = request.POST.get("quantity", "1")

        cart_obj = CartModel.objects.filter(user=request.user, is_active=True).first()
        if not cart_obj:
            return redirect("cart")

        item = CartItemModel.objects.filter(id=item_id, cart=cart_obj).first()
        if not item:
            messages.error(request, "Item not found.")
            return redirect("cart")

        try:
            quantity = int(quantity)
        except ValueError:
            quantity = 1

        if quantity < 1:
            item.delete()
        else:
            item.quantity = quantity
            item.save()

        messages.success(request, "Cart updated.")
        return redirect("cart")

    return redirect("cart")


@login_required(login_url="login")
def cart_remove(request):
    if request.method == "GET":
        return redirect("cart")

    if request.method == "POST":
        item_id = request.POST.get("item_id")
        cart_obj = CartModel.objects.filter(user=request.user, is_active=True).first()
        if cart_obj:
            item = CartItemModel.objects.filter(id=item_id, cart=cart_obj).first()
            if item:
                item.delete()
                messages.success(request, "Item removed.")
        return redirect("cart")

    return redirect("cart")
