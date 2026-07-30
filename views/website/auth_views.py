from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from models.account_models import ProfileModel, WishlistModel


def login(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "GET":
        return render(request, "website/auth/login.html")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        remember = request.POST.get("remember")

        user = authenticate(request, username=email, password=password)

        if user is None:
            matched = User.objects.filter(email=email).first()
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
        next_url = request.GET.get("next") or request.POST.get("next") or "index"
        return redirect(next_url)

    return render(request, "website/auth/login.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "GET":
        return render(request, "website/auth/register.html")

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        phone = (request.POST.get("phone") or "").strip()
        password = request.POST.get("password") or ""
        password_confirm = request.POST.get("password_confirm") or ""

        if not first_name or not last_name or not email or not password:
            messages.error(request, "Please fill in all required fields.")
            return render(request, "website/auth/register.html")

        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, "website/auth/register.html")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "website/auth/register.html")

        if User.objects.filter(username=email).count() > 0:
            messages.error(request, "An account with this email already exists.")
            return render(request, "website/auth/register.html")

        if User.objects.filter(email=email).count() > 0:
            messages.error(request, "An account with this email already exists.")
            return render(request, "website/auth/register.html")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        profile = ProfileModel.objects.filter(user=user).first()
        if not profile:
            profile = ProfileModel.objects.create(user=user)
        if phone:
            profile.phone = phone
            profile.save()

        wishlist = WishlistModel.objects.filter(user=user).first()
        if not wishlist:
            WishlistModel.objects.create(user=user)

        auth_login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("index")

    return render(request, "website/auth/register.html")


def forgot_password(request):
    if request.method == "GET":
        return render(request, "website/auth/forgot_password.html")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        if email:
            messages.success(
                request,
                "If an account exists for that email, reset instructions have been sent.",
            )
            return redirect("login")
        messages.error(request, "Please enter your email.")
        return render(request, "website/auth/forgot_password.html")

    return render(request, "website/auth/forgot_password.html")


def logout(request):
    auth_logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")
