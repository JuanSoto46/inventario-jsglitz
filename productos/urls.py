# productos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Productos
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/crear/", views.crear_producto, name="crear_producto"),
    path("productos/<int:pk>/editar/", views.editar_producto, name="editar_producto"),
    path("productos/<int:pk>/eliminar/", views.eliminar_producto, name="eliminar_producto"),

    # Categorías
    path("categorias/", views.lista_categorias, name="lista_categorias"),
    path("categorias/crear/", views.crear_categoria, name="crear_categoria"),
    path("categorias/<int:pk>/editar/", views.editar_categoria, name="editar_categoria"),
    path("categorias/<int:pk>/eliminar/", views.eliminar_categoria, name="eliminar_categoria"),

    # Movimientos
    path("movimientos/", views.lista_movimientos, name="lista_movimientos"),
    path("movimientos/crear/", views.crear_movimiento, name="crear_movimiento"),

    # Reportes
    path("reportes/", views.menu_reportes, name="reportes_menu"),
    path("reportes/entradas/", views.reporte_entradas, name="reporte_entradas"),
    path("reportes/entradas/exportar/", views.exportar_entradas_excel, name="exportar_entradas_excel"),

    # Autoría / Auditoría
    path("autoria/", views.lista_autoria, name="lista_autoria"),
    path("autoria/<int:pk>/deshacer/", views.deshacer_autoria, name="deshacer_autoria"),
    path("autoria/<int:pk>/eliminar/", views.eliminar_autoria, name="eliminar_autoria"),
    path("ayuda/", views.ayuda, name="ayuda"),
]
