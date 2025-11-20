from django import forms
from django.utils import timezone
from .models import Producto, Categoria, Movimiento


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['categoria', 'nombre', 'descripcion', 'cantidad', 'costo', 'precio_venta']

    def __init__(self, *args, **kwargs):
        super(ProductoForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control bg-dark text-light border-secondary'
            })


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control bg-dark text-light border-secondary'
            })


class MovimientoForm(forms.ModelForm):
    fecha = forms.DateTimeField(
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=True,
        initial=lambda: timezone.localtime(timezone.now()).strftime('%Y-%m-%dT%H:%M')
    )

    class Meta:
        model = Movimiento
        fields = ['producto', 'tipo', 'cantidad', 'observacion', 'fecha']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super(MovimientoForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control bg-dark text-light border-secondary').strip()

        if getattr(self.instance, 'pk', None) and self.instance.fecha:
            self.fields['fecha'].initial = timezone.localtime(self.instance.fecha).strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned = super().clean()
        producto = cleaned.get('producto')
        tipo = cleaned.get('tipo')
        cantidad = cleaned.get('cantidad')

        if cantidad is not None and cantidad <= 0:
            self.add_error('cantidad', 'La cantidad debe ser mayor que cero.')

        # Bloquear salidas mayores al stock
        if producto and tipo == 'salida' and cantidad is not None:
            stock_actual = producto.cantidad
            if cantidad > stock_actual:
                self.add_error('cantidad', f'No hay suficiente inventario. Stock actual: {stock_actual}.')

        return cleaned
