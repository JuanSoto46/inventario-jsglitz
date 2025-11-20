from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    # Relación con el usuario real (si existe)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )

    # Copia de seguridad del nombre de usuario
    user_name = models.CharField(max_length=150, blank=True)

    # e.g. create | update | delete | login...
    action = models.CharField(max_length=50)

    # e.g. Producto | Movimiento | Categoria
    entity_type = models.CharField(max_length=50)

    # id del registro afectado
    entity_id = models.CharField(max_length=100, blank=True)

    # Estado antes y después de la operación
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)

    # Metadata extra opcional (path, motivo, etc.)
    extra = models.JSONField(default=dict, blank=True)

    # Datos técnicos de la petición
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        app_label = "productos"
        ordering = ["-created_at"]
        permissions = [
            ("ver_autoria", "Puede ver el módulo de autoría"),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.usuario_label} {self.action} {self.entity_type}#{self.entity_id}"

    # ------- Helpers de presentación -------

    @property
    def usuario_label(self) -> str:
        """
        Nombre “bonito” del usuario para mostrar en la tabla.
        """
        if getattr(self, "user", None):
            try:
                full_name = self.user.get_full_name()
            except Exception:
                full_name = ""
            return full_name or self.user.get_username()
        return self.user_name or "(sin usuario)"

    @property
    def action_label(self) -> str:
        """
        Acción en castellano para la UI.
        """
        mapping = {
            "create": "Creación",
            "update": "Actualización",
            "delete": "Eliminación",
        }
        return mapping.get((self.action or "").lower(), self.action or "")

    @property
    def entity_label(self) -> str:
        """
        Muestra tipo + id de forma compacta.
        """
        if self.entity_id:
            return f"{self.entity_type} #{self.entity_id}"
        return self.entity_type

    @property
    def resumen_cambios(self) -> list[dict]:
        """
        Devuelve una lista de cambios campo por campo:

        [
          {"campo": "nombre", "antes": "A", "despues": "B"},
          ...
        ]
        """
        before = self.before_json or {}
        after = self.after_json or {}

        if not isinstance(before, dict):
            before = {}
        if not isinstance(after, dict):
            after = {}

        llaves = sorted(set(before.keys()) | set(after.keys()))
        ignorar = {"id", "__model__", "__str__"}

        cambios: list[dict] = []
        for field in llaves:
            if field in ignorar:
                continue
            antes = before.get(field)
            despues = after.get(field)
            if antes != despues:
                cambios.append(
                    {
                        "campo": field,
                        "antes": antes,
                        "despues": despues,
                    }
                )
        return cambios
