from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from core.models import ProfileModel, WishlistModel


def login(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "GET":
        return render(request, "website/auth/login.html")

    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        password = request.POST.get("password", "")
        remember = request.POST.get("remember")

        user = authenticate(request, username=email, password=password)

        if user is None:
            matched = User.objects.filter(email=email).first()
            if matched and not matched.is_active:
                messages.error(
                    request,
                    "Please confirm your email first. Check your inbox for the link.",
                )
                return render(request, "website/auth/login.html")
            if matched:
                user = authenticate(
                    request, username=matched.username, password=password
                )

        if user is None:
            messages.error(request, "Invalid email or password.")
            return render(request, "website/auth/login.html")

        auth_login(request, user)

        if not remember:
            request.session.set_expiry(0)

        profile = ProfileModel.objects.filter(user=user).first()
        if not profile:
            ProfileModel.objects.create(user=user)

        wishlist = WishlistModel.objects.filter(user=user).first()
        if not wishlist:
            WishlistModel.objects.create(user=user)

        messages.success(request, "Welcome back.")
        next_url = request.GET.get("next", "")
        if not next_url:
            next_url = request.POST.get("next", "index")
        return redirect(next_url)

    return render(request, "website/auth/login.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "GET":
        return render(request, "website/auth/register.html")

    if request.method == "POST":
        username = request.POST.get("username", "")
        email = request.POST.get("email", "").lower()
        phone = request.POST.get("phone", "")
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if not username or not email or not password:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "website/auth/register.html")

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "website/auth/register.html")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "website/auth/register.html")

        if User.objects.filter(username=username).count() > 0:
            messages.error(request, "That username is already taken.")
            return render(request, "website/auth/register.html")

        if User.objects.filter(email=email).count() > 0:
            messages.error(request, "An account with this email already exists.")
            return render(request, "website/auth/register.html")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        user.is_active = False
        user.save()

        profile = ProfileModel.objects.filter(user=user).first()
        if not profile:
            profile = ProfileModel.objects.create(user=user)
        if phone:
            profile.phone = phone
            profile.save()

        wishlist = WishlistModel.objects.filter(user=user).first()
        if not wishlist:
            WishlistModel.objects.create(user=user)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        confirm_link = request.build_absolute_uri(
            f"/auth/confirm-email/{uid}/{token}/"
        )

        body = (
            f"Hi {user.username},\n\n"
            f"Thanks for joining DANIEL. Confirm your email with this link:\n"
            f"{confirm_link}\n\n"
            f"If you did not create an account, you can ignore this email.\n\n"
            f"— DANIEL Store"
        )
        html_body = render_to_string(
            "emails/account_confirm.html",
            {
                "username": user.username,
                "confirm_link": confirm_link,
                "shop_url": request.build_absolute_uri("/shop/"),
            },
        )
        try:
            send_mail(
                "Confirm your DANIEL account",
                body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=html_body,
            )
            messages.success(
                request,
                "Account created. Please check your email and click the confirm link.",
            )
        except Exception:
            messages.success(request, "Account created.")
            messages.warning(
                request,
                "We could not send the confirmation email. Please try again later or contact support.",
            )
        return redirect("login")

    return render(request, "website/auth/register.html")


def confirm_email(request, uidb64, token):
    user = None
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    uid_ok = True
    for ch in uidb64:
        if ch not in allowed:
            uid_ok = False
    if uid_ok and uidb64:
        uid = force_str(urlsafe_base64_decode(uidb64))
        if uid.isdigit():
            user = User.objects.filter(pk=int(uid)).first()

    if not user or not default_token_generator.check_token(user, token):
        messages.error(request, "This confirm link is invalid or has expired.")
        return redirect("login")

    user.is_active = True
    user.save()
    messages.success(request, "Email confirmed. You can sign in now.")
    return redirect("login")


def forgot_password(request):
    if request.method == "GET":
        return render(request, "website/auth/forgot_password.html")

    if request.method == "POST":
        email = request.POST.get("email", "").lower()
        if not email:
            messages.error(request, "Please enter your email.")
            return render(request, "website/auth/forgot_password.html")

        user = User.objects.filter(email=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                f"/auth/reset-password/{uid}/{token}/"
            )
            body = (
                f"Hi {user.username},\n\n"
                f"Click this link to reset your DANIEL password:\n"
                f"{reset_link}\n\n"
                f"If you did not ask for this, you can ignore this email.\n\n"
                f"— DANIEL Store"
            )
            html_body = render_to_string(
                "emails/password_reset.html",
                {
                    "username": user.username,
                    "reset_link": reset_link,
                    "shop_url": request.build_absolute_uri("/shop/"),
                },
            )
            try:
                send_mail(
                    "Reset your DANIEL password",
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                    html_message=html_body,
                )
            except Exception:
                messages.warning(
                    request,
                    "We could not send the reset email right now. Please try again later.",
                )
                return render(request, "website/auth/forgot_password.html")

        messages.success(
            request,
            "If an account exists for that email, reset instructions have been sent.",
        )
        return redirect("login")

    return render(request, "website/auth/forgot_password.html")


def reset_password(request, uidb64, token):
    user = None
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    uid_ok = True
    for ch in uidb64:
        if ch not in allowed:
            uid_ok = False
    if uid_ok and uidb64:
        uid = force_str(urlsafe_base64_decode(uidb64))
        if uid.isdigit():
            user = User.objects.filter(pk=int(uid)).first()

    if not user or not default_token_generator.check_token(user, token):
        messages.error(request, "This reset link is invalid or has expired.")
        return redirect("forgot_password")

    if request.method == "GET":
        context = {
            "uidb64": uidb64,
            "token": token,
        }
        return render(request, "website/auth/reset_password.html", context)

    if request.method == "POST":
        password = request.POST.get("password", "")
        password_confirm = request.POST.get("password_confirm", "")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            context = {
                "uidb64": uidb64,
                "token": token,
            }
            return render(request, "website/auth/reset_password.html", context)

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            context = {
                "uidb64": uidb64,
                "token": token,
            }
            return render(request, "website/auth/reset_password.html", context)

        user.set_password(password)
        user.save()
        messages.success(request, "Password updated. Please sign in.")
        return redirect("login")

    return redirect("login")


def logout(request):
    auth_logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")
