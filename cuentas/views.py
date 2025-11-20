# cuentas/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme

@login_required
def inicio(request):
    """
    Panel único. La plantilla 'cuentas/inicio.html' decide qué mostrar
    según permisos/rol usando los filtros de plantilla (in_group, can).
    Nada de inicio_admin/inicio_bodeguero/inicio_vendedor.
    """
    return render(request, "cuentas/inicio.html")


def login_view(request):
    """
    Login con soporte para ?next=/ruta/ y 'remember' (30 días).
    Tras iniciar sesión, si no hay next válido, te mando al panel único 'inicio'.
    """
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Duración de sesión
            if request.POST.get("remember"):
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 días
            else:
                request.session.set_expiry(0)  # expira al cerrar navegador

            # Redirección segura
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            # Un solo panel; la plantilla filtra por rol
            return redirect("inicio")

        messages.error(request, "Usuario o contraseña incorrectos")

    return render(request, "cuentas/login.html", {"next": next_url})
