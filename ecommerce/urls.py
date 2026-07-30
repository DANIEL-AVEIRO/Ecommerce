from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.conf.urls.static import static

from views.website import (
    account_views,
    auth_views,
    cart_views,
    checkout_views,
    page_views,
    product_views,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", product_views.index, name="index"),
    path("shop/", product_views.shop, name="shop"),
    path("product/<slug:slug>/", product_views.product_detail, name="product_detail"),
    path("category/<slug:slug>/", product_views.category, name="category"),
    path("search/", product_views.search, name="search"),
    path("cart/", cart_views.cart, name="cart"),
    path("cart/add/", cart_views.cart_add, name="cart_add"),
    path("cart/update/", cart_views.cart_update, name="cart_update"),
    path("cart/remove/", cart_views.cart_remove, name="cart_remove"),
    path("checkout/", checkout_views.checkout, name="checkout"),
    path(
        "order-success/<str:order_id>/",
        checkout_views.order_success,
        name="order_success",
    ),
    path("wishlist/", account_views.wishlist, name="wishlist"),
    path("wishlist/add/", account_views.wishlist_add, name="wishlist_add"),
    path("wishlist/remove/", account_views.wishlist_remove, name="wishlist_remove"),
    path(
        "wishlist/add-to-cart/",
        account_views.wishlist_add_to_cart,
        name="wishlist_add_to_cart",
    ),
    path("about/", page_views.about, name="about"),
    path("contact/", page_views.contact, name="contact"),
    path("faq/", page_views.faq, name="faq"),
    path("shipping/", page_views.shipping, name="shipping"),
    path("returns/", page_views.returns, name="returns"),
    path("privacy/", page_views.privacy, name="privacy"),
    path("terms/", page_views.terms, name="terms"),
    path("newsletter/", page_views.newsletter_subscribe, name="newsletter_subscribe"),
    path("account/", account_views.account_dashboard, name="account"),
    path("account/orders/", account_views.account_orders, name="account_orders"),
    path(
        "account/orders/<str:order_id>/",
        account_views.account_order_detail,
        name="account_order_detail",
    ),
    path("account/profile/", account_views.account_profile, name="account_profile"),
    path(
        "account/addresses/",
        account_views.account_addresses,
        name="account_addresses",
    ),
    path(
        "account/addresses/<uuid:address_id>/delete/",
        account_views.account_address_delete,
        name="account_address_delete",
    ),
    path("auth/login/", auth_views.login, name="login"),
    path("auth/register/", auth_views.register, name="register"),
    path("auth/forgot-password/", auth_views.forgot_password, name="forgot_password"),
    path("auth/logout/", auth_views.logout, name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r"^.*$", page_views.page_not_found, name="page_not_found"),
]
