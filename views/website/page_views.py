from django.contrib import messages
from django.shortcuts import redirect, render

from enums.content_enums import ContactSubject
from enums.order_enums import OrderStatus, ReturnStatus
from core.models import (
    ContactMessageModel,
    NewsletterSubscriberModel,
    OrderModel,
    ReturnRequestModel,
)

def about(request):
    return render(request, "website/about.html")


def contact(request):
    if request.method == "GET":
        return render(request, "website/contact.html")

    if request.method == "POST":
        name = request.POST.get("name", "")
        email = request.POST.get("email", "")
        subject_text = request.POST.get("subject", "Other")
        message = request.POST.get("message", "")

        subject_map = {
            "Order support": ContactSubject.ORDER,
            "Product question": ContactSubject.PRODUCT,
            "Returns": ContactSubject.RETURNS,
            "Other": ContactSubject.OTHER,
        }
        subject = subject_map.get(subject_text, ContactSubject.OTHER)

        if name and email and message:
            ContactMessageModel.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message,
            )
            messages.success(request, "Message sent. We’ll get back to you soon.")
            return redirect("contact")

        messages.error(request, "Please fill in all fields.")
        return render(request, "website/contact.html")

    return render(request, "website/contact.html")


def faq(request):
    return render(request, "website/faq.html")


def shipping(request):
    return render(request, "website/shipping.html")


def returns(request):
    delivered_orders = []
    if request.user.is_authenticated:
        delivered_orders = OrderModel.objects.filter(
            user=request.user, status=OrderStatus.DELIVERED
        )

    if request.method == "GET":
        context = {
            "delivered_orders": delivered_orders,
        }
        return render(request, "website/returns.html", context)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to request a return.")
            return redirect("login")

        order_number = request.POST.get("order_number", "")
        reason = request.POST.get("reason", "")

        order = OrderModel.objects.filter(
            order_number=order_number,
            user=request.user,
            status=OrderStatus.DELIVERED,
        ).first()
        if not order:
            messages.error(request, "Order not found or not eligible for return.")
            context = {
                "delivered_orders": delivered_orders,
            }
            return render(request, "website/returns.html", context)

        if not reason:
            messages.error(request, "Please enter a reason.")
            context = {
                "delivered_orders": delivered_orders,
            }
            return render(request, "website/returns.html", context)

        existing = ReturnRequestModel.objects.filter(
            order=order, status=ReturnStatus.PENDING
        ).first()
        if existing:
            messages.info(request, "You already have a pending return for that order.")
            return redirect("returns")

        ReturnRequestModel.objects.create(
            order=order,
            user=request.user,
            reason=reason,
            status=ReturnStatus.PENDING,
        )
        messages.success(request, "Return request submitted. We’ll email you soon.")
        return redirect("returns")

    return redirect("returns")


def privacy(request):
    return render(request, "website/privacy.html")


def terms(request):
    return render(request, "website/terms.html")


def page_not_found(request):
    return render(request, "website/404.html", status=404)


def newsletter_subscribe(request):
    if request.method == "GET":
        return redirect("index")

    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        if email:
            existing = NewsletterSubscriberModel.objects.filter(email=email).first()
            if not existing:
                NewsletterSubscriberModel.objects.create(email=email)
            messages.success(request, "Thanks for subscribing.")

        referer = request.META.get("HTTP_REFERER", "/")
        return redirect(referer)

    return redirect("index")
