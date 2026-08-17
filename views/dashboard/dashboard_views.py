from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from urllib.parse import urlencode

from enums.order_enums import OrderStatus, PaymentStatus, ReturnStatus
from core.models import (
    CategoryModel,
    ContactMessageModel,
    CouponModel,
    NewsletterSubscriberModel,
    PaymentMethodModel,
    ProductImageModel,
    ProductModel,
    ProductReviewModel,
    ProductVariantModel,
    OrderModel,
    OrderStatusEventModel,
    ProfileModel,
    ReturnRequestModel,
    ShippingRegionModel,
    WishlistModel,
)


def staff_only(request):
    if not request.user.is_authenticated:
        return False
    if not request.user.is_staff:
        return False
    return True


def filter_query(request):
    data = {}
    for key in request.GET:
        if key == "page":
            continue
        value = request.GET.get(key, "")
        if value:
            data[key] = value
    encoded = urlencode(data)
    if encoded:
        return "&" + encoded
    return ""


def dashboard_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard")

    if request.method == "GET":
        return render(request, "dashboard/login.html")

    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is None:
            matched = User.objects.filter(email=email).first()
            if matched:
                user = authenticate(
                    request, username=matched.username, password=password
                )

        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "dashboard/login.html")

        if not user.is_staff:
            messages.error(request, "This account cannot access the dashboard.")
            return render(request, "dashboard/login.html")

        auth_login(request, user)
        messages.success(request, "Welcome back.")
        next_url = request.GET.get("next", "dashboard")
        return redirect(next_url)

    return render(request, "dashboard/login.html")


def dashboard_logout(request):
    auth_logout(request)
    messages.success(request, "Signed out of dashboard.")
    return redirect("dashboard_login")


@login_required(login_url="dashboard_login")
def dashboard_home(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    low_stock = []
    for variant in ProductVariantModel.objects.filter(is_active=True):
        if variant.stock <= settings.LOW_STOCK_THRESHOLD:
            low_stock.append(variant)

    context = {
        "page_title": "Overview",
        "active_nav": "overview",
        "order_count": OrderModel.objects.count(),
        "pending_orders": OrderModel.objects.filter(status=OrderStatus.PENDING).count(),
        "pending_payments": OrderModel.objects.filter(
            payment_status=PaymentStatus.PENDING,
            payment_method__requires_slip=True,
        ).count(),
        "pending_returns": ReturnRequestModel.objects.filter(
            status=ReturnStatus.PENDING
        ).count(),
        "product_count": ProductModel.objects.filter(is_active=True).count(),
        "low_stock": low_stock[:20],
        "recent_orders": OrderModel.objects.all()[:8],
    }
    return render(request, "dashboard/index.html", context)


@login_required(login_url="dashboard_login")
def dashboard_users(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        action = request.POST.get("action", "")
        user_id = request.POST.get("user_id")
        account = User.objects.filter(id=user_id).first()

        if action == "delete" and account:
            if account.id == request.user.id:
                messages.error(request, "You cannot delete your own account.")
            else:
                account.delete()
                messages.success(request, "User deleted.")
            return redirect("dashboard_users")

        if action == "toggle_active" and account:
            if account.id == request.user.id:
                messages.error(request, "You cannot deactivate your own account.")
            else:
                account.is_active = not account.is_active
                account.save()
                messages.success(request, "User status updated.")
            return redirect("dashboard_users")

    users = User.objects.all().order_by("-date_joined")

    search = request.GET.get("search", "")
    role_filter = request.GET.get("role", "")
    status_filter = request.GET.get("status", "")

    if search:
        by_username = User.objects.filter(username__icontains=search)
        by_email = User.objects.filter(email__icontains=search)
        phone_user_ids = []
        for profile in ProfileModel.objects.filter(phone__icontains=search):
            phone_user_ids.append(profile.user_id)
        by_phone = User.objects.filter(id__in=phone_user_ids)
        users = (by_username | by_email | by_phone).distinct().order_by("-date_joined")

    if role_filter == "staff":
        users = users.filter(is_staff=True)
    if role_filter == "customer":
        users = users.filter(is_staff=False)

    if status_filter == "active":
        users = users.filter(is_active=True)
    if status_filter == "inactive":
        users = users.filter(is_active=False)

    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    for account in page_obj:
        profile = ProfileModel.objects.filter(user=account).first()
        if profile:
            account.phone = profile.phone
        else:
            account.phone = ""
        account.order_count = OrderModel.objects.filter(user=account).count()

    has_filters = False
    if role_filter or status_filter:
        has_filters = True

    context = {
        "page_title": "Users",
        "active_nav": "users",
        "users": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search username, email, or phone",
        "role_filter": role_filter,
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_users"),
        "filter_fields": [
            {
                "name": "role",
                "label": "Role",
                "all_label": "All roles",
                "selected": role_filter,
                "choices": [("staff", "Staff"), ("customer", "Customer")],
            },
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": [("active", "Active"), ("inactive", "Inactive")],
            },
        ],
    }
    return render(request, "dashboard/users.html", context)


@login_required(login_url="dashboard_login")
def dashboard_user_create(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "GET":
        context = {
            "page_title": "Add user",
            "active_nav": "users",
            "account": None,
            "phone": "",
        }
        return render(request, "dashboard/user_form.html", context)

    username = request.POST.get("username", "")
    email = request.POST.get("email", "").lower()
    phone = request.POST.get("phone", "")
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    is_staff = request.POST.get("is_staff") == "on"
    is_active = request.POST.get("is_active") == "on"

    context = {
        "page_title": "Add user",
        "active_nav": "users",
        "account": None,
        "phone": phone,
        "form_username": username,
        "form_email": email,
        "form_is_staff": is_staff,
        "form_is_active": is_active,
    }

    if not username or not email or not password:
        messages.error(request, "Username, email, and password are required.")
        return render(request, "dashboard/user_form.html", context)

    if password != password_confirm:
        messages.error(request, "Passwords do not match.")
        return render(request, "dashboard/user_form.html", context)

    if len(password) < 8:
        messages.error(request, "Password must be at least 8 characters.")
        return render(request, "dashboard/user_form.html", context)

    if User.objects.filter(username=username).first():
        messages.error(request, "That username is already taken.")
        return render(request, "dashboard/user_form.html", context)

    if User.objects.filter(email=email).first():
        messages.error(request, "That email is already in use.")
        return render(request, "dashboard/user_form.html", context)

    account = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )
    account.is_staff = is_staff
    account.is_active = is_active
    account.save()

    profile = ProfileModel.objects.filter(user=account).first()
    if not profile:
        profile = ProfileModel.objects.create(user=account)
    profile.phone = phone
    profile.save()

    wishlist = WishlistModel.objects.filter(user=account).first()
    if not wishlist:
        WishlistModel.objects.create(user=account)

    messages.success(request, "User created.")
    return redirect("dashboard_user_edit", user_id=account.id)


@login_required(login_url="dashboard_login")
def dashboard_user_edit(request, user_id):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    account = User.objects.filter(id=user_id).first()
    if not account:
        messages.error(request, "User not found.")
        return redirect("dashboard_users")

    profile = ProfileModel.objects.filter(user=account).first()
    if not profile:
        profile = ProfileModel.objects.create(user=account)

    if request.method == "GET":
        context = {
            "page_title": "Edit user",
            "active_nav": "users",
            "account": account,
            "phone": profile.phone,
        }
        return render(request, "dashboard/user_form.html", context)

    action = request.POST.get("action", "save")

    if action == "delete":
        if account.id == request.user.id:
            messages.error(request, "You cannot delete your own account.")
            return redirect("dashboard_user_edit", user_id=account.id)
        account.delete()
        messages.success(request, "User deleted.")
        return redirect("dashboard_users")

    username = request.POST.get("username", "")
    email = request.POST.get("email", "").lower()
    phone = request.POST.get("phone", "")
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")
    is_staff = request.POST.get("is_staff") == "on"
    is_active = request.POST.get("is_active") == "on"

    account.username = username
    account.email = email
    account.is_staff = is_staff
    account.is_active = is_active

    context = {
        "page_title": "Edit user",
        "active_nav": "users",
        "account": account,
        "phone": phone,
    }

    if not username or not email:
        messages.error(request, "Username and email are required.")
        return render(request, "dashboard/user_form.html", context)

    if account.id == request.user.id and not is_staff:
        messages.error(request, "You cannot remove staff access from your own account.")
        return render(request, "dashboard/user_form.html", context)

    if account.id == request.user.id and not is_active:
        messages.error(request, "You cannot deactivate your own account.")
        return render(request, "dashboard/user_form.html", context)

    existing_username = User.objects.filter(username=username).first()
    if existing_username and existing_username.id != account.id:
        messages.error(request, "That username is already taken.")
        return render(request, "dashboard/user_form.html", context)

    existing_email = User.objects.filter(email=email).first()
    if existing_email and existing_email.id != account.id:
        messages.error(request, "That email is already in use.")
        return render(request, "dashboard/user_form.html", context)

    if password:
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "dashboard/user_form.html", context)
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "dashboard/user_form.html", context)
        account.set_password(password)

    account.save()

    profile.phone = phone
    profile.save()

    messages.success(request, "User updated.")
    return redirect("dashboard_user_edit", user_id=account.id)


@login_required(login_url="dashboard_login")
def dashboard_orders(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    status_filter = request.GET.get("status", "")
    payment_filter = request.GET.get("payment", "")
    search = request.GET.get("search", "")

    orders = OrderModel.objects.all()

    if search:
        by_number = OrderModel.objects.filter(order_number__icontains=search)
        by_name = OrderModel.objects.filter(username__icontains=search)
        by_email = OrderModel.objects.filter(email__icontains=search)
        by_phone = OrderModel.objects.filter(phone__icontains=search)
        orders = (by_number | by_name | by_email | by_phone).distinct()

    if status_filter:
        orders = orders.filter(status=status_filter)
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)

    orders = orders.order_by("-created_at")

    paginator = Paginator(orders, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter or payment_filter:
        has_filters = True

    context = {
        "page_title": "Orders",
        "active_nav": "orders",
        "orders": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search order #, name, email, or phone",
        "status_filter": status_filter,
        "payment_filter": payment_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_orders"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": OrderStatus.choices,
            },
            {
                "name": "payment",
                "label": "Payment",
                "all_label": "All payments",
                "selected": payment_filter,
                "choices": PaymentStatus.choices,
            },
        ],
    }
    return render(request, "dashboard/orders.html", context)


@login_required(login_url="dashboard_login")
def dashboard_order_detail(request, order_id):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    order = OrderModel.objects.filter(order_number=order_id).first()
    if not order:
        return render(request, "website/404.html", status=404)

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_status":
            new_status = request.POST.get("status", order.status)
            note = request.POST.get("note", "")
            tracking_number = request.POST.get("tracking_number", "").strip()
            if tracking_number:
                order.tracking_number = tracking_number
            if not note:
                note = "Updated by staff"
            if new_status == OrderStatus.SHIPPED and order.tracking_number:
                note = note + f" · Tracking: {order.tracking_number}"
            if new_status == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
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
                    order.status = new_status
                    order.save()
                    OrderStatusEventModel.objects.create(
                        order=order,
                        status=new_status,
                        note=note,
                    )
            else:
                order.status = new_status
                order.save()
                OrderStatusEventModel.objects.create(
                    order=order,
                    status=new_status,
                    note=note,
                )
            messages.success(request, "Order status updated.")

        if action == "update_shipping":
            tracking_number = request.POST.get("tracking_number", "").strip()
            note = request.POST.get("note", "")
            mark_packed = request.POST.get("mark_packed", "")
            mark_shipped = request.POST.get("mark_shipped", "")

            if tracking_number:
                order.tracking_number = tracking_number

            if mark_packed and order.status in [
                OrderStatus.PENDING,
                OrderStatus.CONFIRMED,
            ]:
                order.status = OrderStatus.PROCESSING
                order.save()
                OrderStatusEventModel.objects.create(
                    order=order,
                    status=OrderStatus.PROCESSING,
                    note=note or "Packed / processing",
                )
                messages.success(request, "Order marked as processing/packed.")
            elif mark_shipped:
                order.status = OrderStatus.SHIPPED
                order.save()
                ship_note = note or "Shipped"
                if order.tracking_number:
                    ship_note = ship_note + f" · Tracking: {order.tracking_number}"
                OrderStatusEventModel.objects.create(
                    order=order,
                    status=OrderStatus.SHIPPED,
                    note=ship_note,
                )
                messages.success(request, "Order marked as shipped.")
            else:
                order.save()
                messages.success(request, "Shipping details saved.")

        if action == "update_payment":
            new_payment = request.POST.get("payment_status", order.payment_status)
            order.payment_status = new_payment
            if (
                new_payment == PaymentStatus.PAID
                and order.status == OrderStatus.PENDING
            ):
                order.status = OrderStatus.CONFIRMED
                OrderStatusEventModel.objects.create(
                    order=order,
                    status=OrderStatus.CONFIRMED,
                    note="Payment confirmed",
                )
            order.save()
            messages.success(request, "Payment status updated.")

        return redirect("dashboard_order_detail", order_id=order.order_number)

    context = {
        "page_title": order.order_number,
        "active_nav": "orders",
        "order": order,
        "statuses": OrderStatus.choices,
        "payment_statuses": PaymentStatus.choices,
    }
    return render(request, "dashboard/order_detail.html", context)


@login_required(login_url="dashboard_login")
def dashboard_stock(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        variant_id = request.POST.get("variant_id")
        stock = request.POST.get("stock", "0")
        if stock.isdigit():
            stock = int(stock)
        else:
            stock = 0

        variant = ProductVariantModel.objects.filter(id=variant_id).first()
        if variant:
            variant.stock = stock
            variant.save()
            messages.success(request, "Stock updated.")
        return redirect("dashboard_stock")

    search = request.GET.get("search", "")
    stock_filter = request.GET.get("stock", "")

    variants = ProductVariantModel.objects.filter(is_active=True).order_by(
        "product__name", "color", "size"
    )

    if search:
        by_product = ProductVariantModel.objects.filter(
            is_active=True, product__name__icontains=search
        )
        by_sku = ProductVariantModel.objects.filter(
            is_active=True, sku__icontains=search
        )
        by_color = ProductVariantModel.objects.filter(
            is_active=True, color__icontains=search
        )
        by_size = ProductVariantModel.objects.filter(
            is_active=True, size__icontains=search
        )
        variants = (by_product | by_sku | by_color | by_size).distinct().order_by(
            "product__name", "color", "size"
        )

    if stock_filter == "low":
        low_ids = []
        for variant in variants:
            if variant.stock <= settings.LOW_STOCK_THRESHOLD:
                low_ids.append(variant.id)
        variants = ProductVariantModel.objects.filter(id__in=low_ids).order_by(
            "product__name", "color", "size"
        )
    if stock_filter == "out":
        variants = variants.filter(stock=0)

    paginator = Paginator(variants, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if stock_filter:
        has_filters = True

    context = {
        "page_title": "Stock",
        "active_nav": "stock",
        "variants": page_obj,
        "page_obj": page_obj,
        "low_stock_threshold": settings.LOW_STOCK_THRESHOLD,
        "search": search,
        "search_placeholder": "Search product, SKU, color, or size",
        "stock_filter": stock_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_stock"),
        "filter_fields": [
            {
                "name": "stock",
                "label": "Stock",
                "all_label": "All stock",
                "selected": stock_filter,
                "choices": [
                    ("low", "Low stock"),
                    ("out", "Out of stock"),
                ],
            },
        ],
    }
    return render(request, "dashboard/stock.html", context)


@login_required(login_url="dashboard_login")
def dashboard_coupons(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        action = request.POST.get("action", "create")
        coupon_id = request.POST.get("coupon_id")
        code = request.POST.get("code", "").upper().strip()
        discount_percent = request.POST.get("discount_percent", "0")
        discount_amount = request.POST.get("discount_amount", "0")
        min_order_amount = request.POST.get("min_order_amount", "0")
        max_uses = request.POST.get("max_uses", "0")
        expires_at_raw = request.POST.get("expires_at", "").strip()

        if discount_percent.isdigit():
            discount_percent = int(discount_percent)
        else:
            discount_percent = 0
        if discount_amount.isdigit():
            discount_amount = int(discount_amount)
        else:
            discount_amount = 0
        if min_order_amount.isdigit():
            min_order_amount = int(min_order_amount)
        else:
            min_order_amount = 0
        if max_uses.isdigit():
            max_uses = int(max_uses)
        else:
            max_uses = 0

        expires_at = None
        if expires_at_raw:
            expires_at = parse_datetime(expires_at_raw)
            if not expires_at:
                expires_at = parse_datetime(expires_at_raw + "T23:59:59")
            if expires_at and timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at)

        if action == "toggle":
            coupon = CouponModel.objects.filter(id=coupon_id).first()
            if coupon:
                coupon.is_active = not coupon.is_active
                coupon.save()
                messages.success(request, "Coupon status updated.")
            return redirect("dashboard_coupons")

        if action == "delete":
            coupon = CouponModel.objects.filter(id=coupon_id).first()
            if coupon:
                coupon.delete()
                messages.success(request, "Coupon deleted.")
            return redirect("dashboard_coupons")

        if action == "update":
            coupon = CouponModel.objects.filter(id=coupon_id).first()
            if not coupon:
                messages.error(request, "Coupon not found.")
            elif not code:
                messages.error(request, "Coupon code is required.")
            else:
                other = CouponModel.objects.filter(code=code).first()
                if other and other.id != coupon.id:
                    messages.error(request, "That coupon code already exists.")
                else:
                    coupon.code = code
                    coupon.discount_percent = discount_percent
                    coupon.discount_amount = discount_amount
                    coupon.min_order_amount = min_order_amount
                    coupon.max_uses = max_uses
                    coupon.expires_at = expires_at
                    coupon.save()
                    messages.success(request, "Coupon updated.")
            return redirect("dashboard_coupons")

        if not code:
            messages.error(request, "Coupon code is required.")
        else:
            existing = CouponModel.objects.filter(code=code).first()
            if existing:
                messages.error(request, "That coupon code already exists.")
            else:
                CouponModel.objects.create(
                    code=code,
                    discount_percent=discount_percent,
                    discount_amount=discount_amount,
                    min_order_amount=min_order_amount,
                    max_uses=max_uses,
                    expires_at=expires_at,
                    is_active=True,
                )
                messages.success(request, "Coupon created.")
        return redirect("dashboard_coupons")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    coupons = CouponModel.objects.all().order_by("-created_at")

    if search:
        coupons = coupons.filter(code__icontains=search)

    if status_filter == "active":
        coupons = coupons.filter(is_active=True)
    if status_filter == "inactive":
        coupons = coupons.filter(is_active=False)

    paginator = Paginator(coupons, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Coupons",
        "active_nav": "coupons",
        "coupons": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search coupon code",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_coupons"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": [("active", "Active"), ("inactive", "Off")],
            },
        ],
    }
    return render(request, "dashboard/coupons.html", context)


@login_required(login_url="dashboard_login")
def dashboard_regions(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        action = request.POST.get("action", "create")
        region_id = request.POST.get("region_id")
        name = request.POST.get("name", "").strip()
        standard_fee = request.POST.get("standard_fee", "3000")
        express_fee = request.POST.get("express_fee", "6000")

        if standard_fee.isdigit():
            standard_fee = int(standard_fee)
        else:
            standard_fee = 3000
        if express_fee.isdigit():
            express_fee = int(express_fee)
        else:
            express_fee = 6000

        if action == "toggle":
            region = ShippingRegionModel.objects.filter(id=region_id).first()
            if region:
                region.is_active = not region.is_active
                region.save()
                messages.success(request, "Region status updated.")
            return redirect("dashboard_regions")

        if action == "update":
            region = ShippingRegionModel.objects.filter(id=region_id).first()
            if region and name:
                other = ShippingRegionModel.objects.filter(name=name).first()
                if other and other.id != region.id:
                    messages.error(request, "That region name already exists.")
                else:
                    region.name = name
                    region.standard_fee = standard_fee
                    region.express_fee = express_fee
                    region.save()
                    messages.success(request, "Region updated.")
            return redirect("dashboard_regions")

        if name:
            existing = ShippingRegionModel.objects.filter(name=name).first()
            if existing:
                existing.standard_fee = standard_fee
                existing.express_fee = express_fee
                existing.is_active = True
                existing.save()
                messages.success(request, "Region updated.")
            else:
                ShippingRegionModel.objects.create(
                    name=name,
                    standard_fee=standard_fee,
                    express_fee=express_fee,
                    is_active=True,
                )
                messages.success(request, "Region created.")
        return redirect("dashboard_regions")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    regions = ShippingRegionModel.objects.all().order_by("name")

    if search:
        regions = regions.filter(name__icontains=search)

    if status_filter == "active":
        regions = regions.filter(is_active=True)
    if status_filter == "inactive":
        regions = regions.filter(is_active=False)

    paginator = Paginator(regions, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Shipping regions",
        "active_nav": "regions",
        "regions": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search region name",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_regions"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": [("active", "Active"), ("inactive", "Inactive")],
            },
        ],
    }
    return render(request, "dashboard/regions.html", context)


@login_required(login_url="dashboard_login")
def dashboard_returns(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        return_id = request.POST.get("return_id")
        new_status = request.POST.get("status", ReturnStatus.PENDING)
        admin_note = request.POST.get("admin_note", "")
        return_obj = ReturnRequestModel.objects.filter(id=return_id).first()
        if return_obj:
            old_status = return_obj.status
            return_obj.status = new_status
            return_obj.admin_note = admin_note
            return_obj.save()

            should_restock = False
            if new_status in [ReturnStatus.APPROVED, ReturnStatus.COMPLETED]:
                if not return_obj.stock_restored:
                    should_restock = True

            if should_restock:
                with transaction.atomic():
                    order = return_obj.order
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
                    return_obj.stock_restored = True
                    return_obj.save()

                    if order.payment_status == PaymentStatus.PAID:
                        order.payment_status = PaymentStatus.REFUNDED
                        order.save()

                    OrderStatusEventModel.objects.create(
                        order=order,
                        status=order.status,
                        note="Return approved — stock restored"
                        + (
                            " · payment refunded"
                            if order.payment_status == PaymentStatus.REFUNDED
                            else ""
                        ),
                    )
                messages.success(request, "Return updated. Stock restored.")
            else:
                if (
                    old_status != new_status
                    and new_status == ReturnStatus.REJECTED
                ):
                    messages.success(request, "Return rejected.")
                else:
                    messages.success(request, "Return updated.")
        return redirect("dashboard_returns")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    returns = ReturnRequestModel.objects.all().order_by("-created_at")

    if search:
        by_order = ReturnRequestModel.objects.filter(
            order__order_number__icontains=search
        )
        by_email = ReturnRequestModel.objects.filter(user__email__icontains=search)
        by_reason = ReturnRequestModel.objects.filter(reason__icontains=search)
        returns = (by_order | by_email | by_reason).distinct().order_by("-created_at")

    if status_filter:
        returns = returns.filter(status=status_filter)

    paginator = Paginator(returns, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Returns",
        "active_nav": "returns",
        "returns": page_obj,
        "page_obj": page_obj,
        "statuses": ReturnStatus.choices,
        "search": search,
        "search_placeholder": "Search order #, email, or reason",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_returns"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": ReturnStatus.choices,
            },
        ],
    }
    return render(request, "dashboard/returns.html", context)


def make_unique_slug(name, product_id=None):
    base_slug = slugify(name) or "product"
    slug = base_slug
    n = 1
    while True:
        existing = ProductModel.objects.filter(slug=slug).first()
        if not existing:
            return slug
        if product_id and existing.id == product_id:
            return slug
        slug = base_slug + "-" + str(n)
        n = n + 1


@login_required(login_url="dashboard_login")
def dashboard_categories(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        action = request.POST.get("action", "")
        category_id = request.POST.get("category_id")

        if action == "toggle_active":
            category = CategoryModel.objects.filter(id=category_id).first()
            if category:
                category.is_active = not category.is_active
                category.save()
                messages.success(request, "Category status updated.")
            return redirect("dashboard_categories")

        if action == "delete":
            category = CategoryModel.objects.filter(id=category_id).first()
            if category:
                if category.products.count() > 0:
                    messages.error(
                        request,
                        "Cannot delete a category that still has products.",
                    )
                else:
                    category.delete()
                    messages.success(request, "Category deleted.")
            return redirect("dashboard_categories")

        name = request.POST.get("name", "")
        description = request.POST.get("description", "")
        sort_order = request.POST.get("sort_order", "0")
        image = request.FILES.get("image")

        if sort_order.isdigit():
            sort_order = int(sort_order)
        else:
            sort_order = 0

        if not name:
            messages.error(request, "Category name is required.")
            return redirect("dashboard_categories")

        base_slug = slugify(name) or "category"
        slug = base_slug
        n = 1
        while CategoryModel.objects.filter(slug=slug).first():
            slug = base_slug + "-" + str(n)
            n = n + 1

        category = CategoryModel.objects.create(
            name=name,
            slug=slug,
            description=description,
            sort_order=sort_order,
            is_active=True,
        )
        if image:
            category.image = image
            category.save()

        messages.success(request, "Category created.")
        return redirect("dashboard_categories")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    categories = CategoryModel.objects.all().order_by("sort_order", "name")

    if search:
        by_name = CategoryModel.objects.filter(name__icontains=search)
        by_slug = CategoryModel.objects.filter(slug__icontains=search)
        categories = (by_name | by_slug).distinct().order_by("sort_order", "name")

    if status_filter == "active":
        categories = categories.filter(is_active=True)
    if status_filter == "inactive":
        categories = categories.filter(is_active=False)

    paginator = Paginator(categories, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Categories",
        "active_nav": "categories",
        "categories": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search category name or slug",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_categories"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": [("active", "Active"), ("inactive", "Hidden")],
            },
        ],
    }
    return render(request, "dashboard/categories.html", context)


@login_required(login_url="dashboard_login")
def dashboard_products(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        action = request.POST.get("action", "")
        product_id = request.POST.get("product_id")
        product = ProductModel.objects.filter(id=product_id).first()

        if action == "delete" and product:
            product.delete()
            messages.success(request, "Product deleted.")
            return redirect("dashboard_products")

        if action == "toggle_active" and product:
            product.is_active = not product.is_active
            product.save()
            messages.success(request, "Product status updated.")
            return redirect("dashboard_products")

    search = request.GET.get("search", "")
    category_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    products = ProductModel.objects.all().order_by("-created_at")

    if search:
        by_name = ProductModel.objects.filter(name__icontains=search)
        by_sku = ProductModel.objects.filter(sku__icontains=search)
        products = (by_name | by_sku).distinct().order_by("-created_at")

    if category_filter:
        products = products.filter(category_id=category_filter)

    if status_filter == "active":
        products = products.filter(is_active=True)
    if status_filter == "hidden":
        products = products.filter(is_active=False)

    paginator = Paginator(products, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    category_choices = []
    for category in CategoryModel.objects.all().order_by("sort_order", "name"):
        category_choices.append((str(category.id), category.name))

    has_filters = False
    if category_filter or status_filter:
        has_filters = True

    context = {
        "page_title": "Products",
        "active_nav": "products",
        "products": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search product name or SKU",
        "category_filter": category_filter,
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_products"),
        "filter_fields": [
            {
                "name": "category",
                "label": "Category",
                "all_label": "All categories",
                "selected": category_filter,
                "choices": category_choices,
            },
            {
                "name": "status",
                "label": "Status",
                "all_label": "All statuses",
                "selected": status_filter,
                "choices": [("active", "Active"), ("hidden", "Hidden")],
            },
        ],
    }
    return render(request, "dashboard/products.html", context)


@login_required(login_url="dashboard_login")
def dashboard_product_create(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    categories = CategoryModel.objects.filter(is_active=True).order_by(
        "sort_order", "name"
    )

    if request.method == "GET":
        context = {
            "page_title": "Add product",
            "active_nav": "products",
            "categories": categories,
            "product": None,
        }
        return render(request, "dashboard/product_form.html", context)

    if request.method == "POST":
        name = request.POST.get("name", "")
        category_id = request.POST.get("category_id")
        new_category_name = request.POST.get("new_category_name", "")
        description = request.POST.get("description", "")
        sku = request.POST.get("sku", "")
        material = request.POST.get("material", "")
        price = request.POST.get("regular_price", "0")
        sale_price = request.POST.get("sale_price", "")
        is_featured = request.POST.get("is_featured") == "on"
        is_active = request.POST.get("is_active") == "on"
        color = request.POST.get("color", "Default")
        size = request.POST.get("size", "One Size")
        stock = request.POST.get("stock", "0")
        gallery_files = request.FILES.getlist("gallery_images")

        if price.isdigit():
            price = int(price)
        else:
            price = 0
        if stock.isdigit():
            stock = int(stock)
        else:
            stock = 0

        sale = None
        if sale_price and sale_price.isdigit():
            sale = int(sale_price)

        category = None
        if new_category_name:
            cat_slug = slugify(new_category_name) or "category"
            existing_cat = CategoryModel.objects.filter(slug=cat_slug).first()
            if existing_cat:
                category = existing_cat
            else:
                category = CategoryModel.objects.create(
                    name=new_category_name,
                    slug=cat_slug,
                    is_active=True,
                )
        elif category_id:
            category = CategoryModel.objects.filter(id=category_id).first()

        if not name:
            messages.error(request, "Product name is required.")
            context = {
                "page_title": "Add product",
                "active_nav": "products",
                "categories": categories,
                "product": None,
            }
            return render(request, "dashboard/product_form.html", context)

        if not category:
            messages.error(request, "Please choose or create a category.")
            context = {
                "page_title": "Add product",
                "active_nav": "products",
                "categories": categories,
                "product": None,
            }
            return render(request, "dashboard/product_form.html", context)

        if not sku:
            messages.error(request, "SKU is required.")
            context = {
                "page_title": "Add product",
                "active_nav": "products",
                "categories": categories,
                "product": None,
            }
            return render(request, "dashboard/product_form.html", context)

        if ProductModel.objects.filter(sku=sku).first():
            messages.error(request, "That product SKU already exists.")
            context = {
                "page_title": "Add product",
                "active_nav": "products",
                "categories": categories,
                "product": None,
            }
            return render(request, "dashboard/product_form.html", context)

        if price <= 0:
            messages.error(request, "Price must be greater than 0.")
            context = {
                "page_title": "Add product",
                "active_nav": "products",
                "categories": categories,
                "product": None,
            }
            return render(request, "dashboard/product_form.html", context)

        product = ProductModel.objects.create(
            category=category,
            name=name,
            slug=make_unique_slug(name),
            description=description,
            regular_price=price,
            sale_price=sale,
            sku=sku,
            material=material,
            is_featured=is_featured,
            is_active=is_active,
        )

        variant_sku = sku + "-V1"
        if ProductVariantModel.objects.filter(sku=variant_sku).first():
            variant_sku = sku + "-V" + str(product.id)

        ProductVariantModel.objects.create(
            product=product,
            color=color,
            size=size,
            sku=variant_sku,
            stock=stock,
            is_active=True,
        )

        if gallery_files:
            sort_order = 0
            for image_file in gallery_files:
                ProductImageModel.objects.create(
                    product=product,
                    image=image_file,
                    alt_text=name,
                    is_primary=(sort_order == 0),
                    sort_order=sort_order,
                )
                sort_order = sort_order + 1

        messages.success(request, "Product created.")
        return redirect("dashboard_product_edit", product_id=product.id)

    return redirect("dashboard_products")


@login_required(login_url="dashboard_login")
def dashboard_product_edit(request, product_id):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    product = ProductModel.objects.filter(id=product_id).first()
    if not product:
        return render(request, "website/404.html", status=404)

    categories = CategoryModel.objects.filter(is_active=True).order_by(
        "sort_order", "name"
    )
    variants = ProductVariantModel.objects.filter(product=product).order_by(
        "color", "size"
    )
    product_images = ProductImageModel.objects.filter(product=product).order_by(
        "-is_primary", "sort_order", "created_at"
    )
    primary_image = ProductImageModel.objects.filter(
        product=product, is_primary=True
    ).first()
    if not primary_image:
        primary_image = ProductImageModel.objects.filter(product=product).first()

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "delete":
            product.delete()
            messages.success(request, "Product deleted.")
            return redirect("dashboard_products")

        if action == "add_images":
            gallery_files = request.FILES.getlist("gallery_images")
            if not gallery_files:
                messages.error(request, "Please choose at least one image.")
                return redirect("dashboard_product_edit", product_id=product.id)

            last_image = (
                ProductImageModel.objects.filter(product=product)
                .order_by("-sort_order")
                .first()
            )
            sort_order = 0
            if last_image:
                sort_order = last_image.sort_order + 1

            for image_file in gallery_files:
                ProductImageModel.objects.create(
                    product=product,
                    image=image_file,
                    alt_text=product.name,
                    is_primary=False,
                    sort_order=sort_order,
                )
                sort_order = sort_order + 1

            has_primary = ProductImageModel.objects.filter(
                product=product, is_primary=True
            ).first()
            if not has_primary:
                first_image = (
                    ProductImageModel.objects.filter(product=product)
                    .order_by("sort_order", "created_at")
                    .first()
                )
                if first_image:
                    first_image.is_primary = True
                    first_image.save()

            messages.success(request, "Gallery images added.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if action == "set_primary_image":
            image_id = request.POST.get("image_id")
            image = ProductImageModel.objects.filter(
                id=image_id, product=product
            ).first()
            if image:
                for other in ProductImageModel.objects.filter(product=product):
                    other.is_primary = False
                    other.save()
                image.is_primary = True
                image.save()
                messages.success(request, "Primary image updated.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if action == "delete_image":
            image_id = request.POST.get("image_id")
            image = ProductImageModel.objects.filter(
                id=image_id, product=product
            ).first()
            if image:
                was_primary = image.is_primary
                image.delete()
                if was_primary:
                    next_image = (
                        ProductImageModel.objects.filter(product=product)
                        .order_by("sort_order", "created_at")
                        .first()
                    )
                    if next_image:
                        next_image.is_primary = True
                        next_image.save()
                messages.success(request, "Image removed from gallery.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if action == "add_variant":
            color = request.POST.get("color", "")
            size = request.POST.get("size", "")
            stock = request.POST.get("stock", "0")
            variant_sku = request.POST.get("variant_sku", "")

            if stock.isdigit():
                stock = int(stock)
            else:
                stock = 0

            if not color or not size:
                messages.error(request, "Color and size are required.")
                return redirect("dashboard_product_edit", product_id=product.id)

            if not variant_sku:
                variant_sku = product.sku + "-" + color[:3].upper() + "-" + size.upper()

            if ProductVariantModel.objects.filter(sku=variant_sku).first():
                messages.error(request, "That variant SKU already exists.")
                return redirect("dashboard_product_edit", product_id=product.id)

            same = ProductVariantModel.objects.filter(
                product=product, color=color, size=size
            ).first()
            if same:
                messages.error(request, "This color and size already exists.")
                return redirect("dashboard_product_edit", product_id=product.id)

            ProductVariantModel.objects.create(
                product=product,
                color=color,
                size=size,
                sku=variant_sku,
                stock=stock,
                is_active=True,
            )
            messages.success(request, "Variant added.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if action == "update_variant":
            variant_id = request.POST.get("variant_id")
            color = request.POST.get("color", "")
            size = request.POST.get("size", "")
            stock = request.POST.get("stock", "0")
            variant_sku = request.POST.get("variant_sku", "")
            is_active = request.POST.get("is_active") == "on"

            if stock.isdigit():
                stock = int(stock)
            else:
                stock = 0

            variant = ProductVariantModel.objects.filter(
                id=variant_id, product=product
            ).first()
            if not variant:
                messages.error(request, "Variant not found.")
                return redirect("dashboard_product_edit", product_id=product.id)

            if not color or not size or not variant_sku:
                messages.error(request, "Color, size, and SKU are required.")
                return redirect("dashboard_product_edit", product_id=product.id)

            sku_taken = ProductVariantModel.objects.filter(sku=variant_sku).first()
            if sku_taken and sku_taken.id != variant.id:
                messages.error(request, "That variant SKU already exists.")
                return redirect("dashboard_product_edit", product_id=product.id)

            same = ProductVariantModel.objects.filter(
                product=product, color=color, size=size
            ).first()
            if same and same.id != variant.id:
                messages.error(request, "This color and size already exists.")
                return redirect("dashboard_product_edit", product_id=product.id)

            variant.color = color
            variant.size = size
            variant.sku = variant_sku
            variant.stock = stock
            variant.is_active = is_active
            variant.save()
            messages.success(request, "Variant updated.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if action == "delete_variant":
            variant_id = request.POST.get("variant_id")
            variant = ProductVariantModel.objects.filter(
                id=variant_id, product=product
            ).first()
            if variant:
                variant.delete()
                messages.success(request, "Variant deleted.")
            return redirect("dashboard_product_edit", product_id=product.id)

        name = request.POST.get("name", "")
        category_id = request.POST.get("category_id")
        new_category_name = request.POST.get("new_category_name", "")
        description = request.POST.get("description", "")
        sku = request.POST.get("sku", "")
        material = request.POST.get("material", "")
        price = request.POST.get("regular_price", "0")
        sale_price = request.POST.get("sale_price", "")
        is_featured = request.POST.get("is_featured") == "on"
        is_active = request.POST.get("is_active") == "on"

        if price.isdigit():
            price = int(price)
        else:
            price = 0

        sale = None
        if sale_price and sale_price.isdigit():
            sale = int(sale_price)

        category = product.category
        if new_category_name:
            cat_slug = slugify(new_category_name) or "category"
            existing_cat = CategoryModel.objects.filter(slug=cat_slug).first()
            if existing_cat:
                category = existing_cat
            else:
                category = CategoryModel.objects.create(
                    name=new_category_name,
                    slug=cat_slug,
                    is_active=True,
                )
        elif category_id:
            found = CategoryModel.objects.filter(id=category_id).first()
            if found:
                category = found

        if not name:
            messages.error(request, "Product name is required.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if not sku:
            messages.error(request, "SKU is required.")
            return redirect("dashboard_product_edit", product_id=product.id)

        sku_taken = ProductModel.objects.filter(sku=sku).first()
        if sku_taken and sku_taken.id != product.id:
            messages.error(request, "That product SKU already exists.")
            return redirect("dashboard_product_edit", product_id=product.id)

        if price <= 0:
            messages.error(request, "Price must be greater than 0.")
            return redirect("dashboard_product_edit", product_id=product.id)

        product.category = category
        product.name = name
        product.slug = make_unique_slug(name, product_id=product.id)
        product.description = description
        product.regular_price = price
        product.sale_price = sale
        product.sku = sku
        product.material = material
        product.is_featured = is_featured
        product.is_active = is_active
        product.save()

        messages.success(request, "Product updated.")
        return redirect("dashboard_product_edit", product_id=product.id)

    context = {
        "page_title": "Edit product",
        "active_nav": "products",
        "categories": categories,
        "product": product,
        "variants": variants,
        "product_images": product_images,
        "primary_image": primary_image,
    }
    return render(request, "dashboard/product_form.html", context)


@login_required(login_url="dashboard_login")
def dashboard_payment_methods(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        action = request.POST.get("action", "create")
        method_id = request.POST.get("method_id")
        name = request.POST.get("name", "").strip()
        instructions = request.POST.get("instructions", "")
        account_info = request.POST.get("account_info", "")
        sort_order = request.POST.get("sort_order", "0")
        requires_slip = bool(request.POST.get("requires_slip"))
        is_cod = bool(request.POST.get("is_cod"))

        if sort_order.isdigit():
            sort_order = int(sort_order)
        else:
            sort_order = 0

        if is_cod:
            requires_slip = False

        if action == "toggle":
            method = PaymentMethodModel.objects.filter(id=method_id).first()
            if method:
                method.is_active = not method.is_active
                method.save()
                messages.success(request, "Payment method status updated.")
            return redirect("dashboard_payment_methods")

        if action == "delete":
            method = PaymentMethodModel.objects.filter(id=method_id).first()
            if method:
                method.delete()
                messages.success(request, "Payment method deleted.")
            return redirect("dashboard_payment_methods")

        if action == "update":
            method = PaymentMethodModel.objects.filter(id=method_id).first()
            if method and name:
                method.name = name
                method.instructions = instructions
                method.account_info = account_info
                method.sort_order = sort_order
                method.requires_slip = requires_slip
                method.is_cod = is_cod
                method.save()
                messages.success(request, "Payment method updated.")
            return redirect("dashboard_payment_methods")

        if not name:
            messages.error(request, "Name is required.")
        else:
            PaymentMethodModel.objects.create(
                name=name,
                instructions=instructions,
                account_info=account_info,
                sort_order=sort_order,
                requires_slip=requires_slip,
                is_cod=is_cod,
                is_active=True,
            )
            messages.success(request, "Payment method created.")
        return redirect("dashboard_payment_methods")

    search = request.GET.get("search", "")
    methods = PaymentMethodModel.objects.all().order_by("sort_order", "name")
    if search:
        methods = methods.filter(name__icontains=search)

    paginator = Paginator(methods, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_title": "Payment methods",
        "active_nav": "payments",
        "methods": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search payment method",
        "has_filters": False,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_payment_methods"),
        "filter_fields": [],
    }
    return render(request, "dashboard/payment_methods.html", context)


@login_required(login_url="dashboard_login")
def dashboard_reviews(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        review_id = request.POST.get("review_id")
        action = request.POST.get("action", "")
        review = ProductReviewModel.objects.filter(id=review_id).first()
        if review:
            if action == "approve":
                review.is_approved = True
                review.save()
                messages.success(request, "Review approved.")
            if action == "hide":
                review.is_approved = False
                review.save()
                messages.success(request, "Review hidden.")
            if action == "delete":
                review.delete()
                messages.success(request, "Review deleted.")
        return redirect("dashboard_reviews")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    reviews = ProductReviewModel.objects.all().order_by("-created_at")

    if search:
        by_product = ProductReviewModel.objects.filter(
            product__name__icontains=search
        )
        by_user = ProductReviewModel.objects.filter(user__username__icontains=search)
        by_comment = ProductReviewModel.objects.filter(comment__icontains=search)
        reviews = (by_product | by_user | by_comment).distinct().order_by(
            "-created_at"
        )

    if status_filter == "pending":
        reviews = reviews.filter(is_approved=False)
    if status_filter == "approved":
        reviews = reviews.filter(is_approved=True)

    paginator = Paginator(reviews, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Reviews",
        "active_nav": "reviews",
        "reviews": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search product, user, or comment",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_reviews"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All reviews",
                "selected": status_filter,
                "choices": [
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                ],
            },
        ],
    }
    return render(request, "dashboard/reviews.html", context)


@login_required(login_url="dashboard_login")
def dashboard_contacts(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        contact_id = request.POST.get("contact_id")
        action = request.POST.get("action", "")
        contact = ContactMessageModel.objects.filter(id=contact_id).first()
        if contact:
            if action == "resolve":
                contact.is_resolved = True
                contact.save()
                messages.success(request, "Marked as resolved.")
            if action == "reopen":
                contact.is_resolved = False
                contact.save()
                messages.success(request, "Marked as open.")
            if action == "delete":
                contact.delete()
                messages.success(request, "Message deleted.")
        return redirect("dashboard_contacts")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    contacts = ContactMessageModel.objects.all().order_by("-created_at")

    if search:
        by_name = ContactMessageModel.objects.filter(name__icontains=search)
        by_email = ContactMessageModel.objects.filter(email__icontains=search)
        by_message = ContactMessageModel.objects.filter(message__icontains=search)
        contacts = (by_name | by_email | by_message).distinct().order_by("-created_at")

    if status_filter == "open":
        contacts = contacts.filter(is_resolved=False)
    if status_filter == "resolved":
        contacts = contacts.filter(is_resolved=True)

    paginator = Paginator(contacts, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Contact messages",
        "active_nav": "contacts",
        "contacts": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search name, email, or message",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_contacts"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All messages",
                "selected": status_filter,
                "choices": [
                    ("open", "Open"),
                    ("resolved", "Resolved"),
                ],
            },
        ],
    }
    return render(request, "dashboard/contacts.html", context)


@login_required(login_url="dashboard_login")
def dashboard_newsletter(request):
    if not staff_only(request):
        messages.error(request, "Staff access only.")
        return redirect("dashboard_login")

    if request.method == "POST":
        subscriber_id = request.POST.get("subscriber_id")
        action = request.POST.get("action", "")
        subscriber = NewsletterSubscriberModel.objects.filter(id=subscriber_id).first()
        if subscriber:
            if action == "toggle":
                subscriber.is_active = not subscriber.is_active
                subscriber.save()
                messages.success(request, "Subscriber updated.")
            if action == "delete":
                subscriber.delete()
                messages.success(request, "Subscriber deleted.")
        return redirect("dashboard_newsletter")

    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    subscribers = NewsletterSubscriberModel.objects.all().order_by("-created_at")

    if search:
        subscribers = subscribers.filter(email__icontains=search)

    if status_filter == "active":
        subscribers = subscribers.filter(is_active=True)
    if status_filter == "inactive":
        subscribers = subscribers.filter(is_active=False)

    paginator = Paginator(subscribers, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    has_filters = False
    if status_filter:
        has_filters = True

    context = {
        "page_title": "Newsletter",
        "active_nav": "newsletter",
        "subscribers": page_obj,
        "page_obj": page_obj,
        "search": search,
        "search_placeholder": "Search email",
        "status_filter": status_filter,
        "has_filters": has_filters,
        "filter_query": filter_query(request),
        "clear_url": reverse("dashboard_newsletter"),
        "filter_fields": [
            {
                "name": "status",
                "label": "Status",
                "all_label": "All subscribers",
                "selected": status_filter,
                "choices": [
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                ],
            },
        ],
    }
    return render(request, "dashboard/newsletter.html", context)
