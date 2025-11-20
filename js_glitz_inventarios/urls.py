# js_glitz_inventarios/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Autenticación + panel de inicio (cuentas)
    # Aquí viven 'login', 'logout', 'password_reset', e 'inicio'
    path("", include("cuentas.urls")),

    # Inventario (productos, movimientos, categorías, reportes, autoría)
    # Lo incluimos en raíz para que los nombres funcionen sin namespace
    # y las URLs queden /productos/, /movimientos/, /categorias/, etc.
    path("", include("productos.urls")),
]
