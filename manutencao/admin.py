# ==================== ADMIN.PY ====================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Setor, Equipamento, Chamado, ImagemChamado

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais', {'fields': ('tipo', 'telefone')}),
    )
    list_display = ['username', 'email', 'tipo', 'is_staff']
    list_filter = ['tipo', 'is_staff']


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'criado_em']
    search_fields = ['nome']


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'setor', 'criado_em']
    list_filter = ['setor']
    search_fields = ['nome', 'codigo']


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = ['id', 'solicitante', 'status', 'tipo', 'prioridade', 'criado_em']
    list_filter = ['status', 'tipo', 'prioridade']
    search_fields = ['descricao']


@admin.register(ImagemChamado)
class ImagemChamadoAdmin(admin.ModelAdmin):
    list_display = ['id', 'chamado', 'descricao', 'enviado_em']
    list_filter = ['enviado_em']