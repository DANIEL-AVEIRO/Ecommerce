# DANIEL Store

Beginner-friendly Django ecommerce project for **DANIEL** — Yangon-focused shipping, Kyat (MMK) pricing, function-based views.

This repository is meant for students. Clone it, set up a virtualenv, migrate, and run the server.

## Stack

- Python 3 + Django 5.2
- SQLite (default database file: `db.sqlite3`)
- Pillow (product / payment screenshot images)
- Tailwind CDN + Syne / Manrope fonts
- HTML email templates (order confirm, password reset, account confirm)

## Quick start

```bash
# 1. Clone the repo, then enter the project folder
cd ecommerce

# 2. Create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install packages
pip install -r requirements.txt

# 4. Environment file
cp .env.example .env
# Optional: edit .env (SECRET_KEY, email). Email can stay empty for local learning.

# 5. Database tables
python manage.py migrate

# 6. Demo data (categories, products, regions, coupons, payment methods)
python manage.py seed_store

# 7. Staff user for the dashboard
python manage.py createsuperuser
# After create, open Django admin or use shell to set is_staff=True if needed.
# createsuperuser already creates a staff/superuser account.

# 8. Run
python manage.py runserver
```

Open:

- Store: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Staff dashboard: [http://127.0.0.1:8000/dashboard/login/](http://127.0.0.1:8000/dashboard/login/)
- Django admin: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

If the repo already includes a `db.sqlite3` with sample data, you can still run `migrate` (safe), then skip `seed_store` if products already exist.

## Environment variables

Copy `.env.example` → `.env`. Values are loaded in `ecommerce/settings.py`.

| Variable              | Description                   | Example                        |
| --------------------- | ----------------------------- | ------------------------------ |
| `SECRET_KEY`          | Django secret key             | long random string             |
| `DEBUG`               | Debug mode                    | `True`                         |
| `ALLOWED_HOSTS`       | Comma-separated hosts         | `localhost,127.0.0.1`          |
| `TIME_ZONE`           | Timezone                      | `Asia/Yangon`                  |
| `EMAIL_HOST_USER`     | Gmail address (optional)      | you@gmail.com                  |
| `EMAIL_HOST_PASSWORD` | Gmail app password (optional) | app password                   |
| `DEFAULT_FROM_EMAIL`  | From header                   | DANIEL Store \<you@gmail.com\> |

Notes:

- **Never commit `.env`.** It is listed in `.gitignore`.
- If email is empty, Django prints emails in the **terminal** (console backend). That is enough for learning register / reset / order emails.
- To send real Gmail mail, set `EMAIL_HOST_USER` and a Gmail **App Password**.

## Project layout

```
manage.py
requirements.txt
.env.example
db.sqlite3              # SQLite database (included for demo; safe to recreate)
ecommerce/              # Project settings + urls
core/                   # App config, admin, context processor, management commands
models/                 # Product, cart, order, account, content models
enums/                  # TextChoices (order status, payment status, …)
views/website/          # Storefront function-based views
views/dashboard/        # Staff dashboard views
templates/website/      # Storefront HTML
templates/dashboard/    # Dashboard HTML
templates/emails/       # HTML emails
static/website/         # CSS, JS, fonts, images
static/dashboard/       # Dashboard CSS / JS / fonts
media/                  # Uploaded product images & payment screenshots
```

## Features

### Storefront

- Home, shop, category, product detail, search (name / description / SKU / category / material)
- Auth: register + email confirm, login, logout, forgot / reset password
- Cart & wishlist (login required)
- Checkout: shipping regions, coupons, CRUD payment methods, order email
- Payment screenshot upload (for methods that require it)
- Account: orders, tracking number timeline, cancel, returns, profile, addresses
- Contact form, newsletter, FAQ / shipping / returns / privacy / terms

### Staff dashboard (`/dashboard/`)

- Overview, users, orders (status + packing/shipping + tracking number + payment)
- Products, categories, stock
- Coupons (create / edit / deactivate, expiry, max uses)
- Shipping regions (standard / express fees)
- Payment methods CRUD
- Returns (approve → restock + refund paid orders)
- Review moderation (verified purchase only)
- Contact messages & newsletter subscribers

## Learning notes (beginner style)

This project intentionally stays simple:

- Function-based views (`def my_view(request):`)
- `request.POST.get(...)` / `request.GET.get(...)` (no `forms.py`)
- `.filter(...).first()` and create when missing
- `@login_required(login_url="login")` for private pages
- Money stored as `BigIntegerField` (Kyat). Templates use `{% load humanize %}` and `{{ price|intcomma }} Ks`

## Common commands

```bash
python manage.py migrate
python manage.py seed_store
python manage.py createsuperuser
python manage.py runserver
python manage.py runserver 0.0.0.0:8000   # LAN access
```

## What is not in Git

These stay local (see `.gitignore`):

- `.env` (secrets)
- `.venv/` / `venv/` (virtualenv)
- `.cursor/` (editor)
- `__pycache__/`, `*.pyc`, `staticfiles/`, IDE folders, logs

Everything else in this project (code, templates, static, media, `db.sqlite3`, migrations) is meant to be shared with students.
