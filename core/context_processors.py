def expose_perms(request):
    u = request.user
    if not getattr(u, "is_authenticated", False):
        return {"has_perms": lambda *p: False}
    def _has_perms(*perm_list):
        return u.is_superuser or u.has_perms(perm_list)
    return {"has_perms": _has_perms}
