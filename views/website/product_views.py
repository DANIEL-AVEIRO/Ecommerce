from django.core.paginator import Paginator
from django.shortcuts import render

from models.product_models import CategoryModel, ProductModel


def index(request):
    featured_products = ProductModel.objects.filter(
        is_active=True, is_featured=True
    )[:6]

    if featured_products.count() < 3:
        featured_products = ProductModel.objects.filter(is_active=True)[:6]

    new_products = ProductModel.objects.filter(is_active=True).order_by("-created_at")[:4]
    categories = CategoryModel.objects.filter(is_active=True).order_by("sort_order")[:6]

    return render(
        request,
        "website/index.html",
        {
            "featured_products": featured_products,
            "new_products": new_products,
            "categories": categories,
        },
    )


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
            if product.compare_at_price and product.compare_at_price > product.price:
                sale_ids.append(product.id)
        products = ProductModel.objects.filter(id__in=sale_ids, is_active=True)
    elif selected_category:
        products = products.filter(category__slug=selected_category)

    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    if min_price:
        try:
            products = products.filter(price__gte=int(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=int(max_price))
        except ValueError:
            pass

    selected_sort = request.GET.get("sort", "featured")
    if selected_category != "new":
        if selected_sort == "newest":
            products = products.order_by("-created_at")
        elif selected_sort == "price_asc":
            products = products.order_by("price")
        elif selected_sort == "price_desc":
            products = products.order_by("-price")
        else:
            products = products.order_by("-is_featured", "-created_at")

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "website/shop.html",
        {
            "categories": categories,
            "products": page_obj,
            "page_obj": page_obj,
            "selected_category": selected_category,
            "selected_sort": selected_sort,
            "min_price": min_price,
            "max_price": max_price,
        },
    )


def category(request, slug):
    category_obj = CategoryModel.objects.filter(slug=slug, is_active=True).first()
    if not category_obj:
        return render(request, "website/404.html", status=404)

    products = ProductModel.objects.filter(is_active=True, category=category_obj)

    selected_sort = request.GET.get("sort", "featured")
    if selected_sort == "newest":
        products = products.order_by("-created_at")
    elif selected_sort == "price_asc":
        products = products.order_by("price")
    elif selected_sort == "price_desc":
        products = products.order_by("-price")
    else:
        products = products.order_by("-is_featured", "-created_at")

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "website/category.html",
        {
            "category": category_obj,
            "products": page_obj,
            "page_obj": page_obj,
        },
    )


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

    return render(
        request,
        "website/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "colors": colors,
            "sizes": sizes,
        },
    )


def search(request):
    query = (request.GET.get("q") or "").strip()
    products = []
    result_count = 0
    categories = CategoryModel.objects.filter(is_active=True).order_by(
        "sort_order", "name"
    )[:8]

    if query:
        products = ProductModel.objects.filter(
            is_active=True, name__icontains=query
        ).order_by("-created_at")[:24]
        result_count = ProductModel.objects.filter(
            is_active=True, name__icontains=query
        ).count()

    return render(
        request,
        "website/search.html",
        {
            "query": query,
            "products": products,
            "result_count": result_count,
            "categories": categories,
        },
    )
