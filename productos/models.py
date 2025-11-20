from django.db import models, transaction
from django.utils import timezone


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    cantidad = models.PositiveIntegerField()  # stock actual mostrado
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre}"


TIPO_CHOICES = (
    ('entrada', 'Entrada'),
    ('salida', 'Salida'),
)


class Movimiento(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    cantidad = models.PositiveIntegerField()
    observacion = models.TextField(blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    # Saldo acumulado después de aplicar este movimiento
    saldo = models.IntegerField(default=0, editable=False)
    

    class Meta:
        ordering = ['fecha', 'id']  # orden estable para el recálculo
        permissions = [
            ("ver_reportes", "Puede ver el módulo de reportes"),
        ]

    def __str__(self):
        return f"{self.producto} - {self.tipo} {self.cantidad} - saldo {self.saldo}"

    @classmethod
    def recomputar_saldos_producto(cls, producto_id: int):
        """
        Recalcula el saldo de TODOS los movimientos del producto en orden cronológico
        y sincroniza Producto.cantidad con el último saldo.
        """
        with transaction.atomic():
            movimientos = list(
                cls.objects.select_for_update()
                .filter(producto_id=producto_id)
                .order_by('fecha', 'id')
            )
            saldo = 0
            for m in movimientos:
                saldo += (m.cantidad if m.tipo == 'entrada' else -int(m.cantidad))
                if m.saldo != saldo:
                    cls.objects.filter(pk=m.pk).update(saldo=saldo)

            Producto.objects.filter(pk=producto_id).update(
                cantidad=saldo if movimientos else 0
            )

    def save(self, *args, **kwargs):
        # Guardamos y luego recalculamos todo el historial del producto.
        super().save(*args, **kwargs)
        Movimiento.recomputar_saldos_producto(self.producto_id)
        
# OPCIONAL: proxy para que “Reportes” salga como módulo en el admin
class ReporteProxy(Producto):
    class Meta:
        proxy = True
        app_label = "productos"
        verbose_name = "Reportes"
        verbose_name_plural = "Reportes"
        default_permissions = () 

# Asegurar que Django detecte AuditLog para migraciones
from .models_audit import AuditLog  # noqa: F401
