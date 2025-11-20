# productos/admin.py
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from .models import Categoria, Producto, Movimiento, ReporteProxy
from .models_audit import AuditLog  # ← import del modelo de Autoría (el bueno)

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "categoria", "cantidad", "costo", "precio_venta")
    list_filter = ("categoria",)
    search_fields = ("nombre", "descripcion")
    autocomplete_fields = ("categoria",)

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ("id", "producto", "tipo", "cantidad", "saldo", "fecha")
    list_filter = ("tipo", "fecha", "producto__categoria")
    search_fields = ("producto__nombre", "observacion")
    autocomplete_fields = ("producto",)

    # Si quieres que aparezca con solo "add", descomenta:
    # def get_model_perms(self, request):
    #     perms = super().get_model_perms(request)
    #     if request.user.has_perm("productos.add_movimiento"):
    #         perms["view"] = perms.get("view") or True
    #     return perms

@admin.register(ReporteProxy)
class ReporteAdmin(admin.ModelAdmin):
    # No listamos nada; es un ancla de menú
    def get_queryset(self, request):
        return Producto.objects.none()

    # Controla visibilidad del bloque en el index
    def has_module_permission(self, request):
        return request.user.has_perm("productos.ver_reportes")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("productos.ver_reportes")

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_permission(request):
            raise PermissionDenied
        # Redirige correctamente al menú de reportes (nombre CANÓNICO: 'reportes_menu')
        return redirect(reverse("reportes_menu"))

# ====== AUTORÍA ======
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user_name", "action", "entity_type", "entity_id")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("user_name", "entity_type", "entity_id")
    ordering = ("-created_at",)

    readonly_fields = (
        "created_at", "user_name", "action", "entity_type", "entity_id",
        "before_json", "after_json", "extra",
    )

    # Solo lectura para todos (evita que alguien “fabrique” auditorías)
    def has_add_permission(self, request): 
        return False

    def has_change_permission(self, request, obj=None): 
        return False

    def has_delete_permission(self, request, obj=None):
        # Si quieres permitir borrar, deja superuser; si no, devuelve False
        return request.user.is_superuser

    # Respeta el permiso productos.ver_autoria
    def has_module_permission(self, request):
        return request.user.has_perm("productos.ver_autoria")

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("productos.ver_autoria")
