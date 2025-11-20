#Aqui registramos los modelos
from django.contrib import admin
from django.contrib.admin import AdminSite
#from .models import Usuario

# Personalización visual del panel
admin.site.site_header = "Administración Js Glitz 🍷"
admin.site.site_title = "Panel Js Glitz"
admin.site.index_title = "Bienvenido al sistema de gestión de inventario"


#CSS personalizado
class CustomAdminSite(admin.AdminSite):
    def each_context(self, request):
        context = super().each_context(request)
        context["css_files"] = ["css/admin.css"]
        return context
# Resto de registros
#admin.site.register(Usuario)
