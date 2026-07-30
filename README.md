# DANIEL Store

Django ecommerce storefront for **DANIEL** — everyday essentials, Yangon-focused shipping, Kyat pricing.

## Stack

- Django 5.2
- SQLite (default)
- Tailwind CDN + Syne / Manrope fonts
- Pillow (product images / seed)

## Setup

```bash
# 1. Create and activate a virtualenv (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment file
cp .env.example .env
# Edit .env — set a unique SECRET_KEY for anything beyond local play

# 4. Database
python manage.py migrate

# 5. (Optional) Seed ~30 sample products + images
python manage.py seed_store --clear

# 6. (Optional) Create an admin user
python manage.py createsuperuser

# 7. Run
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Admin: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin).

## Environment variables

Copy `.env.example` to `.env`. Values are loaded in `ecommerce/settings.py`.

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | long random string |
| `DEBUG` | Debug mode | `True` / `False` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `TIME_ZONE` | Django timezone | `Asia/Yangon` |

Never commit `.env`. It is listed in `.gitignore`.

## Project layout

```
ecommerce/          # Django project (settings, urls)
core/               # App (admin, context processors, seed command, templatetags)
models/             # Product, cart, order, account, content models
enums/              # TextChoices
views/website/      # Function-based views
templates/website/  # Storefront templates
static/             # Static assets
media/              # Uploaded / seeded images (ignored by git)
```

## Features

- Shop, product detail, search, categories
- Auth (login / register) — cart & wishlist require login
- Cart, checkout (COD / KBZ / bank transfer), order history
- Wishlist, account profile & addresses
- Contact form, newsletter signup, FAQ / shipping / returns pages
- Mobile bottom navigation

## Notes

- Money fields use `BigIntegerField` (MMK / Kyat).
- Templates use `{% url %}` names and the `money` template filter.
- Seed images need network access the first time; Pillow can fill gaps if a download fails.
