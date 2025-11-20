from django.apps import AppConfig

class ProductosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "productos"

    def ready(self):
        # Fuerza a cargar el módulo de modelos de auditoría
        from . import models_audit  # noqa: F401
