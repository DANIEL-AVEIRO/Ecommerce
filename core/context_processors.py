from core.models import CartModel, WishlistModel


def storefront_context(request):
    cart_count = 0
    wishlist_count = 0

    if request.user.is_authenticated:
        cart = CartModel.objects.filter(user=request.user, is_active=True).first()
        if cart:
            cart_count = cart.item_count

        wishlist = WishlistModel.objects.filter(user=request.user).first()
        if wishlist:
            wishlist_count = wishlist.items.count()

    return {
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
    }
