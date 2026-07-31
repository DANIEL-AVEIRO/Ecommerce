from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path
from django.conf.urls.static import static

from views.dashboard import dashboard_views
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
    # Storefront
    path("", product_views.index, name="index"),
    path("shop/", product_views.shop, name="shop"),
    path("product/<slug:slug>/", product_views.product_detail, name="product_detail"),
    path(
        "product/<slug:slug>/review/",
        product_views.product_review,
        name="product_review",
    ),
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
    path(
        "account/orders/<str:order_id>/cancel/",
        account_views.account_order_cancel,
        name="account_order_cancel",
    ),
    path(
        "account/orders/<str:order_id>/upload-slip/",
        account_views.account_order_upload_slip,
        name="account_order_upload_slip",
    ),
    path(
        "account/orders/<str:order_id>/return/",
        account_views.account_return_request,
        name="account_return_request",
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
    path(
        "auth/confirm-email/<uidb64>/<token>/",
        auth_views.confirm_email,
        name="confirm_email",
    ),
    path("auth/forgot-password/", auth_views.forgot_password, name="forgot_password"),
    path(
        "auth/reset-password/<uidb64>/<token>/",
        auth_views.reset_password,
        name="reset_password",
    ),
    path("auth/logout/", auth_views.logout, name="logout"),
    # Staff dashboard (separate login)
    path("dashboard/login/", dashboard_views.dashboard_login, name="dashboard_login"),
    path("dashboard/logout/", dashboard_views.dashboard_logout, name="dashboard_logout"),
    path("dashboard/", dashboard_views.dashboard_home, name="dashboard"),
    path("dashboard/users/", dashboard_views.dashboard_users, name="dashboard_users"),
    path(
        "dashboard/users/create/",
        dashboard_views.dashboard_user_create,
        name="dashboard_user_create",
    ),
    path(
        "dashboard/users/<int:user_id>/edit/",
        dashboard_views.dashboard_user_edit,
        name="dashboard_user_edit",
    ),
    path("dashboard/orders/", dashboard_views.dashboard_orders, name="dashboard_orders"),
    path(
        "dashboard/orders/<str:order_id>/",
        dashboard_views.dashboard_order_detail,
        name="dashboard_order_detail",
    ),
    path("dashboard/stock/", dashboard_views.dashboard_stock, name="dashboard_stock"),
    path(
        "dashboard/categories/",
        dashboard_views.dashboard_categories,
        name="dashboard_categories",
    ),
    path(
        "dashboard/products/",
        dashboard_views.dashboard_products,
        name="dashboard_products",
    ),
    path(
        "dashboard/products/create/",
        dashboard_views.dashboard_product_create,
        name="dashboard_product_create",
    ),
    path(
        "dashboard/products/<uuid:product_id>/edit/",
        dashboard_views.dashboard_product_edit,
        name="dashboard_product_edit",
    ),
    path(
        "dashboard/coupons/",
        dashboard_views.dashboard_coupons,
        name="dashboard_coupons",
    ),
    path(
        "dashboard/regions/",
        dashboard_views.dashboard_regions,
        name="dashboard_regions",
    ),
    path(
        "dashboard/returns/",
        dashboard_views.dashboard_returns,
        name="dashboard_returns",
    ),
    path(
        "dashboard/payment-methods/",
        dashboard_views.dashboard_payment_methods,
        name="dashboard_payment_methods",
    ),
    path(
        "dashboard/reviews/",
        dashboard_views.dashboard_reviews,
        name="dashboard_reviews",
    ),
    path(
        "dashboard/contacts/",
        dashboard_views.dashboard_contacts,
        name="dashboard_contacts",
    ),
    path(
        "dashboard/newsletter/",
        dashboard_views.dashboard_newsletter,
        name="dashboard_newsletter",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r"^.*$", page_views.page_not_found, name="page_not_found"),
]
