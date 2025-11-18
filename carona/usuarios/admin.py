from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Profile

class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ('email', 'nome', 'tipo_usuario', 'is_staff', 'is_superuser')
    list_filter = ('tipo_usuario', 'is_staff', 'is_superuser')
    search_fields = ('email', 'nome')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informações Pessoais', {'fields': ('nome', 'telefone', 'tipo_usuario')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas importantes', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nome', 'telefone', 'tipo_usuario', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

admin.site.register(Usuario, UsuarioAdmin)

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpf', 'placa', 'modelo_veiculo')
    search_fields = ('user__nome', 'cpf', 'placa')

admin.site.register(Profile, ProfileAdmin)