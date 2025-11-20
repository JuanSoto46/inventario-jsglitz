from django import template
register = template.Library()

@register.filter
def in_group(user, group_name):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=group_name).exists()

@register.filter
def can(user, perm):
    if not user.is_authenticated:
        return False
    app, code = perm.split(".")
    return user.is_superuser or user.has_perm(f"{app}.{code}")
