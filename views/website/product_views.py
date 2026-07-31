from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from core.models import (
    CategoryModel,
    OrderItemModel,
    ProductModel,
    ProductReviewModel,
)
from enums.order_enums import OrderStatus


def index(request):
    featured_products = ProductModel.objects.filter(is_active=True, is_featured=True)[
        :6
    ]

    if featured_products.count() < 3:
        featured_products = ProductModel.objects.filter(is_active=True)[:6]

    new_products = ProductModel.objects.filter(is_active=True).order_by("-created_at")[
        :4
    ]
    categories = CategoryModel.objects.filter(is_active=True).order_by("sort_order")[:6]

    context = {
        "featured_products": featured_products,
        "new_products": new_products,
        "categories": categories,
    }
    return render(request, "website/index.html", context)


def shop(request):
    categories = CategoryModel.objects.filter(is_active=True).order_by(
        "sort_order", "name"
    )

    products = ProductModel.objects.filter(is_active=True)

    selected_category = request.GET.get("category", "")
    if selected_category == "new":
        products = products.order_by("-created_at")
    elif selected_category == "sale":
        sale_ids = []
        for product in products:
            if product.is_on_sale:
                sale_ids.append(product.id)
        products = ProductModel.objects.filter(id__in=sale_ids, is_active=True)
    elif selected_category:
        products = products.filter(category__slug=selected_category)

    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    if min_price.isdigit():
        products = products.filter(regular_price__gte=int(min_price))
    if max_price.isdigit():
        products = products.filter(regular_price__lte=int(max_price))

    selected_sort = request.GET.get("sort", "featured")
    if selected_category != "new":
        if selected_sort == "newest":
            products = products.order_by("-created_at")
        elif selected_sort == "price_asc":
            products = products.order_by("regular_price")
        elif selected_sort == "price_desc":
            products = products.order_by("-regular_price")
        else:
            products = products.order_by("-is_featured", "-created_at")

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "categories": categories,
        "products": page_obj,
        "page_obj": page_obj,
        "selected_category": selected_category,
        "selected_sort": selected_sort,
        "min_price": min_price,
        "max_price": max_price,
    }
    return render(request, "website/shop.html", context)


def category(request, slug):
    category_obj = CategoryModel.objects.filter(slug=slug, is_active=True).first()
    if not category_obj:
        return render(request, "website/404.html", status=404)

    products = ProductModel.objects.filter(is_active=True, category=category_obj)

    selected_sort = request.GET.get("sort", "featured")
    if selected_sort == "newest":
        products = products.order_by("-created_at")
    elif selected_sort == "price_asc":
        products = products.order_by("regular_price")
    elif selected_sort == "price_desc":
        products = products.order_by("-regular_price")
    else:
        products = products.order_by("-is_featured", "-created_at")

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "category": category_obj,
        "products": page_obj,
        "page_obj": page_obj,
    }
    return render(request, "website/category.html", context)


def product_detail(request, slug):
    product = ProductModel.objects.filter(slug=slug, is_active=True).first()
    if not product:
        return render(request, "website/404.html", status=404)

    related_products = ProductModel.objects.filter(
        is_active=True, category=product.category
    ).exclude(id=product.id)[:4]

    colors = []
    sizes = []
    for variant in product.variants.filter(is_active=True):
        if variant.color not in colors:
            colors.append(variant.color)
        if variant.size not in sizes:
            sizes.append(variant.size)

    reviews = product.reviews.filter(is_approved=True)
    review_count = reviews.count()
    rating_total = 0
    for review in reviews:
        rating_total = rating_total + review.rating
    average_rating = 0
    average_stars = 0
    if review_count > 0:
        average_rating = round(rating_total / review_count, 1)
        average_stars = int(round(rating_total / review_count))

    can_review = False
    is_verified_buyer = False
    if request.user.is_authenticated:
        bought = OrderItemModel.objects.filter(
            product=product,
            order__user=request.user,
            order__status=OrderStatus.DELIVERED,
        ).first()
        if bought:
            is_verified_buyer = True
            can_review = True

    context = {
        "product": product,
        "related_products": related_products,
        "colors": colors,
        "sizes": sizes,
        "reviews": reviews,
        "review_count": review_count,
        "average_rating": average_rating,
        "average_stars": average_stars,
        "in_stock": product.in_stock,
        "total_stock": product.total_stock,
        "can_review": can_review,
        "is_verified_buyer": is_verified_buyer,
    }
    return render(request, "website/product_detail.html", context)


@login_required(login_url="login")
def product_review(request, slug):
    if request.method == "GET":
        return redirect("product_detail", slug=slug)

    if request.method == "POST":
        product = ProductModel.objects.filter(slug=slug, is_active=True).first()
        if not product:
            return render(request, "website/404.html", status=404)

        bought = OrderItemModel.objects.filter(
            product=product,
            order__user=request.user,
            order__status=OrderStatus.DELIVERED,
        ).first()
        if not bought:
            messages.error(
                request,
                "Only customers with a delivered order can review this product.",
            )
            return redirect("product_detail", slug=slug)

        rating = request.POST.get("rating", "5")
        comment = request.POST.get("comment", "")

        if rating.isdigit():
            rating = int(rating)
        else:
            rating = 5
        if rating < 1:
            rating = 1
        if rating > 5:
            rating = 5

        if not comment:
            messages.error(request, "Please write a short review.")
            return redirect("product_detail", slug=slug)

        existing = ProductReviewModel.objects.filter(
            product=product, user=request.user
        ).first()
        if existing:
            existing.rating = rating
            existing.comment = comment
            existing.is_verified_purchase = True
            existing.is_approved = False
            existing.save()
            messages.success(
                request, "Your review was updated and is waiting for approval."
            )
        else:
            ProductReviewModel.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment,
                is_approved=False,
                is_verified_purchase=True,
            )
            messages.success(
                request, "Thanks for your review. It will show after approval."
            )

        return redirect("product_detail", slug=slug)

    return redirect("shop")


def search(request):
    query = request.GET.get("q", "").strip()
    products = []
    result_count = 0
    categories = CategoryModel.objects.filter(is_active=True).order_by(
        "sort_order", "name"
    )[:8]

    if query:
        by_name = ProductModel.objects.filter(is_active=True, name__icontains=query)
        by_desc = ProductModel.objects.filter(
            is_active=True, description__icontains=query
        )
        by_sku = ProductModel.objects.filter(is_active=True, sku__icontains=query)
        by_category = ProductModel.objects.filter(
            is_active=True, category__name__icontains=query
        )
        by_material = ProductModel.objects.filter(
            is_active=True, material__icontains=query
        )
        products = (
            (by_name | by_desc | by_sku | by_category | by_material)
            .distinct()
            .order_by("-is_featured", "-created_at")
        )
        result_count = products.count()
        products = products[:48]

    context = {
        "query": query,
        "products": products,
        "result_count": result_count,
        "categories": categories,
    }
    return render(request, "website/search.html", context)
