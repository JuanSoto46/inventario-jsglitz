from decimal import Decimal
from django.contrib import messages
from django.db import models
from django.db.models import Q, F, Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.utils.html import escape
from django.contrib.auth.decorators import permission_required, login_required

from .models import Producto, Movimiento, Categoria
from .forms import ProductoForm, MovimientoForm, CategoriaForm

# Auditoría
from .audit_utils import save_audit
from .models_audit import AuditLog
from django.apps import apps
from django.views.decorators.http import require_POST
from django.db import transaction

# -------- Productos --------
@login_required
def lista_productos(request):
    query = request.GET.get('q', '').strip()
    productos = Producto.objects.all()

    costo_total = productos.aggregate(
        total=Sum(F('costo') * F('cantidad'), output_field=models.DecimalField(max_digits=18, decimal_places=2))
    )['total'] or Decimal('0')

    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) | Q(categoria__nombre__icontains=query)
        )

    return render(request, 'productos/lista_productos.html', {
        'productos': productos,
        'costo_total': costo_total
    })


@login_required
def crear_producto(request):
    form = ProductoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        save_audit(request, entity_type="Producto", entity_id=obj.pk, action="create", after=obj)
        messages.success(request, 'Producto creado correctamente.')
        return redirect('lista_productos')
    return render(request, 'productos/crear_producto.html', {'form': form})


@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    before = Producto.objects.get(pk=pk)  # snapshot previo

    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        save_audit(request, entity_type="Producto", entity_id=obj.pk, action="update", before=before, after=obj)
        messages.success(request, 'Producto actualizado.')
        return redirect('lista_productos')
    return render(request, 'productos/editar_producto.html', {'form': form})


@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        before = Producto.objects.get(pk=pk)
        producto.delete()
        save_audit(request, entity_type="Producto", entity_id=pk, action="delete", before=before)
        messages.success(request, 'Producto eliminado.')
        return redirect('lista_productos')
    return render(request, 'productos/eliminar_producto.html', {'producto': producto})


# -------- Categorías --------
@login_required
def lista_categorias(request):
    categorias = Categoria.objects.all()
    query = request.GET.get('q', '').strip()
    if query:
        categorias = categorias.filter(nombre__icontains=query)
    return render(request, 'categorias/lista_categorias.html', {'categorias': categorias})


@login_required
def crear_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            save_audit(request, entity_type="Categoria", entity_id=obj.pk, action="create", after=obj)
            messages.success(request, 'Categoría creada.')
            return redirect('lista_categorias')
        messages.error(request, 'Revisa los errores del formulario.')
    else:
        form = CategoriaForm()
    return render(request, 'categorias/crear_categoria.html', {'form': form, 'accion': 'Crear'})


@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        before = Categoria.objects.get(pk=pk)
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            obj = form.save()
            save_audit(request, entity_type="Categoria", entity_id=obj.pk, action="update", before=before, after=obj)
            messages.success(request, 'Categoría actualizada.')
            return redirect('lista_categorias')
        messages.error(request, 'Revisa los errores del formulario.')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'categorias/editar_categoria.html', {'form': form, 'accion': 'Editar'})


@login_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        before = Categoria.objects.get(pk=pk)
        categoria.delete()
        save_audit(request, entity_type="Categoria", entity_id=pk, action="delete", before=before)
        messages.success(request, 'Categoría eliminada.')
        return redirect('lista_categorias')
    return render(request, 'categorias/eliminar_categoria.html', {'categoria': categoria})


# -------- Movimientos --------
@permission_required("productos.view_movimiento", raise_exception=True)
def lista_movimientos(request):
    movimientos = Movimiento.objects.select_related('producto').order_by('fecha', 'id')
    q = request.GET.get('q', '').strip()
    if q:
        if q.isdigit():
            movimientos = movimientos.filter(producto__id=int(q))
        else:
            movimientos = movimientos.filter(producto__nombre__icontains=q)

    return render(request, 'productos/lista_movimientos.html', {
        'movimientos': movimientos,
        'q': q,
    })


@permission_required("productos.add_movimiento", raise_exception=True)
def crear_movimiento(request):
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            obj = form.save()  # valida stock y recalcula saldos
            save_audit(request, entity_type="Movimiento", entity_id=obj.pk, action="create", after=obj)
            messages.success(request, 'Movimiento registrado.')
            return redirect('lista_movimientos')
        messages.error(request, 'Revisa los errores del formulario.')
    else:
        form = MovimientoForm()

    return render(request, 'productos/crear_movimiento.html', {'form': form})


# -------- Reporte de Entradas --------
def _filtro_entradas_queryset(params):
    """
    Aplica filtros sobre Movimiento para entradas.
    Filtros soportados: q (texto), producto (id), categoria (id), desde (YYYY-MM-DD), hasta (YYYY-MM-DD)
    """
    q = params.get('q', '').strip()
    producto_id = params.get('producto')
    categoria_id = params.get('categoria')
    fecha_desde = params.get('desde')
    fecha_hasta = params.get('hasta')

    qs = Movimiento.objects.select_related('producto', 'producto__categoria') \
                           .filter(tipo='entrada') \
                           .order_by('-fecha')

    if q:
        qs = qs.filter(Q(producto__nombre__icontains=q) | Q(producto__id__icontains=q))

    if producto_id:
        try:
            qs = qs.filter(producto_id=int(producto_id))
        except ValueError:
            pass

    if categoria_id:
        try:
            qs = qs.filter(producto__categoria_id=int(categoria_id))
        except ValueError:
            pass

    if fecha_desde:
        qs = qs.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__date__lte=fecha_hasta)

    return qs


@permission_required("productos.ver_reportes", raise_exception=True)
def reporte_entradas(request):
    qs = _filtro_entradas_queryset(request.GET)
    productos = Producto.objects.all().order_by('nombre')
    categorias = Categoria.objects.all().order_by('nombre')

    ctx = {
        'movimientos': qs,
        'q': request.GET.get('q', ''),
        'producto': request.GET.get('producto', ''),
        'categoria': request.GET.get('categoria', ''),
        'desde': request.GET.get('desde', ''),
        'hasta': request.GET.get('hasta', ''),
        'productos': productos,
        'categorias': categorias,
        'total_cant': qs.aggregate(total=Sum('cantidad'))['total'] or 0,
    }
    return render(request, 'reportes/reporte_entradas.html', ctx)


@permission_required("productos.ver_reportes", raise_exception=True)
def exportar_entradas_excel(request):
    qs = _filtro_entradas_queryset(request.GET)

    rows = []
    rows.append("<table border='1'>")
    rows.append("<thead><tr>")
    headers = ["ID", "Producto", "Categoría", "Cantidad", "Fecha", "Observación"]
    for h in headers:
        rows.append(f"<th>{escape(h)}</th>")
    rows.append("</tr></thead><tbody>")

    for m in qs:
        rows.append("<tr>")
        rows.append(f"<td>{m.id}</td>")
        rows.append(f"<td>{escape(m.producto.nombre if m.producto else '')}</td>")
        rows.append(f"<td>{escape(m.producto.categoria.nombre if m.producto and m.producto.categoria else '')}</td>")
        rows.append(f"<td style='mso-number-format:0;'>{m.cantidad}</td>")
        rows.append(f"<td>{m.fecha.strftime('%Y-%m-%d %H:%M')}</td>")
        rows.append(f"<td>{escape(m.observacion or '')}</td>")
        rows.append("</tr>")

    rows.append("</tbody></table>")
    html_table = "".join(rows)

    response = HttpResponse(html_table, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename="reporte_entradas.xls"'
    return response


@permission_required("productos.ver_reportes", raise_exception=True)
def menu_reportes(request):
    return render(request, 'reportes/menu.html', {})


# -------- Autoría --------
@permission_required("productos.ver_autoria", raise_exception=True)
def lista_autoria(request):
    """
    Lista los registros de auditoría con filtros:
    - búsqueda libre (usuario / acción / entidad / id)
    - por tipo de entidad
    - por acción
    - por rango de fechas
    """
    q = (request.GET.get("q") or "").strip()
    entidad = (request.GET.get("entidad") or "").strip()
    accion = (request.GET.get("accion") or "").strip()
    desde = (request.GET.get("desde") or "").strip()
    hasta = (request.GET.get("hasta") or "").strip()

    qs = AuditLog.objects.all()

    if q:
        qs = qs.filter(
            models.Q(user_name__icontains=q)
            | models.Q(user__username__icontains=q)
            | models.Q(user__first_name__icontains=q)
            | models.Q(user__last_name__icontains=q)
            | models.Q(entity_type__icontains=q)
            | models.Q(entity_id__icontains=q)
            | models.Q(action__icontains=q)
        )

    if entidad:
        qs = qs.filter(entity_type__iexact=entidad)

    if accion:
        qs = qs.filter(action__iexact=accion)

    if desde:
        qs = qs.filter(created_at__date__gte=desde)
    if hasta:
        qs = qs.filter(created_at__date__lte=hasta)

    qs = qs.select_related("user").order_by("-created_at")
    items = qs[:300]

    entidades = (
        AuditLog.objects.exclude(entity_type="")
        .values_list("entity_type", flat=True)
        .order_by("entity_type")
        .distinct()
    )
    acciones = (
        AuditLog.objects.exclude(action="")
        .values_list("action", flat=True)
        .order_by("action")
        .distinct()
    )

    ctx = {
        "items": items,
        "q": q,
        "entidad": entidad,
        "accion": accion,
        "desde": desde,
        "hasta": hasta,
        "entidades": entidades,
        "acciones": acciones,
    }
    return render(request, "autoria/lista_autoria.html", ctx)


@permission_required("productos.ver_autoria", raise_exception=True)
@require_POST
@transaction.atomic
def deshacer_autoria(request, pk):
    """
    Intenta revertir el cambio asociado a este registro de autoría.
    - update: vuelve al estado 'before_json'
    - create: elimina el registro creado
    - delete: recrea el registro a partir del JSON
    """
    log = get_object_or_404(AuditLog, pk=pk)

    accion = (log.action or "").lower()
    before = log.before_json or {}
    after = log.after_json or {}

    try:
        Model = apps.get_model("productos", log.entity_type)
    except LookupError:
        Model = None

    if not Model:
        messages.error(request, "No se puede deshacer: el modelo asociado no existe.")
        return redirect("lista_autoria")

    try:
        if accion == "update":
            try:
                obj = Model.objects.get(pk=log.entity_id)
            except Model.DoesNotExist:
                messages.error(request, "No se encontró el registro a revertir.")
                return redirect("lista_autoria")

            if isinstance(before, dict):
                for field, value in before.items():
                    if field in ("id", "__model__", "__str__"):
                        continue
                    setattr(obj, field, value)
                obj.save()
                messages.success(
                    request,
                    f"Se revirtió la actualización de {log.entity_label}.",
                )
            else:
                messages.error(request, "No hay datos válidos para revertir este cambio.")

        elif accion == "create":
            try:
                obj = Model.objects.get(pk=log.entity_id)
                obj.delete()
                messages.success(
                    request,
                    f"Se eliminó el registro creado {log.entity_label}.",
                )
            except Model.DoesNotExist:
                messages.warning(request, "El registro a eliminar ya no existe.")

        elif accion == "delete":
            data = before or after
            if not isinstance(data, dict) or not data:
                messages.error(
                    request,
                    "No hay datos suficientes para recrear el registro eliminado.",
                )
            else:
                campos = {
                    k: v
                    for k, v in data.items()
                    if k not in ("__model__", "__str__")
                }
                if "id" in campos:
                    campos["pk"] = campos.pop("id")
                Model.objects.create(**campos)
                messages.success(
                    request,
                    f"Se recreó el registro eliminado {log.entity_label}.",
                )
        else:
            messages.warning(
                request,
                "Esta acción no tiene una operación de deshacer definida.",
            )

    except Exception:
        messages.error(
            request,
            "Hubo un problema al intentar deshacer este cambio.",
        )

    return redirect("lista_autoria")


@permission_required("productos.ver_autoria", raise_exception=True)
@require_POST
def eliminar_autoria(request, pk):
    """
    Elimina el registro de autoría (no toca la entidad original).
    """
    log = get_object_or_404(AuditLog, pk=pk)
    log.delete()
    messages.success(request, "Registro de autoría eliminado correctamente.")
    return redirect("lista_autoria")

def ayuda(request):
    """
    Centro de ayuda al usuario:
    - acceso a un chat tipo IA (interfaz simulada)
    - videos de ayuda
    - datos de contacto rápido con la empresa
    """
    return render(request, "ayuda.html")
