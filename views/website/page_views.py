from django.contrib import messages
from django.shortcuts import redirect, render

from enums.content_enums import ContactSubject
from models.content_models import ContactMessageModel, NewsletterSubscriberModel


def about(request):
    return render(request, "website/about.html")


def contact(request):
    if request.method == "GET":
        return render(request, "website/contact.html")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        subject_text = request.POST.get("subject") or "Other"
        message = (request.POST.get("message") or "").strip()

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
    return render(request, "website/returns.html")


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
        email = (request.POST.get("email") or "").strip().lower()
        if email:
            existing = NewsletterSubscriberModel.objects.filter(email=email).first()
            if not existing:
                NewsletterSubscriberModel.objects.create(email=email)
            messages.success(request, "Thanks for subscribing.")

        referer = request.META.get("HTTP_REFERER", "/")
        return redirect(referer)

    return redirect("index")
