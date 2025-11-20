from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

def grant(group, codes):
    ok, miss = 0, 0
    for code in codes:
        try:
            app_label, codename = code.split(".")
        except ValueError:
            miss += 1
            continue
        try:
            perm = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename
            )
            group.permissions.add(perm)
            ok += 1
        except Permission.DoesNotExist:
            miss += 1
    return ok, miss

class Command(BaseCommand):
    help = "Crea grupos (Administrador, Bodeguero, Vendedor) y asigna permisos para la app 'productos'."

    def handle(self, *args, **opts):
        admin, _ = Group.objects.get_or_create(name="Administrador")
        bodeguero, _ = Group.objects.get_or_create(name="Bodeguero")
        vendedor, _ = Group.objects.get_or_create(name="Vendedor")

        # Limpieza para que sea idempotente
        for g in (admin, bodeguero, vendedor):
            g.permissions.clear()

        # Admin: TODO lo que exista (todas las apps)
        for p in Permission.objects.all():
            admin.permissions.add(p)

        # Bodeguero: productos/categorías/movimientos (sin deletes)
        bodeguero_perms = [
            # Producto
            "productos.view_producto",
            "productos.add_producto",
            "productos.change_producto",

            # Categoría (solo ver)
            "productos.view_categoria",

            # Movimiento (tu modelo único para entradas/salidas)
            "productos.view_movimiento",
            "productos.add_movimiento",

            # Reportes: se controlan con view_movimiento, no hay permiso aparte
        ]

        # Vendedor: ver productos y registrar movimientos; ve reportes
        vendedor_perms = [
            "productos.view_producto",
            "productos.view_movimiento",
            "productos.add_movimiento",
        ]

        ok_b, miss_b = grant(bodeguero, bodeguero_perms)
        ok_v, miss_v = grant(vendedor, vendedor_perms)

        self.stdout.write(self.style.SUCCESS(
            f"Roles creados/actualizados.\n"
            f" - Bodeguero: {ok_b} permisos asignados, {miss_b} ignorados.\n"
            f" - Vendedor: {ok_v} permisos asignados, {miss_v} ignorados."
        ))
