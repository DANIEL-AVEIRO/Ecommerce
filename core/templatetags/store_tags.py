from django import template

register = template.Library()


@register.filter(name="money")
def money(value):
    if value is None:
        return "0 Ks"
    return f"{int(value):,} Ks"
