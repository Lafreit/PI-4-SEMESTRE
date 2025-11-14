from django.contrib import admin
from .models import Corrida, SolicitacaoCarona

class SolicitacaoInline(admin.TabularInline):
    model = SolicitacaoCarona
    extra = 0
    readonly_fields = ("passageiro", "data_solicitacao", "status")
    can_delete = False

@admin.register(Corrida)
class CorridaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "origem",
        "destino",
        "data",
        "horario_saida",
        "vagas_disponiveis",
        "valor",
        "status",
        "criado_em",
    )
    list_filter = ("data", "status", "cidade_origem", "cidade_destino")
    search_fields = ("origem", "destino", "bairro_origem", "cidade_origem", "bairro_destino", "cidade_destino", "motorista__username")
    readonly_fields = ("criado_em", "atualizado_em")
    date_hierarchy = "data"
    ordering = ("-data", "-horario_saida")
    inlines = [SolicitacaoInline]
    actions = ["marcar_cancelada", "exportar_selecionadas_json"]

    def marcar_cancelada(self, request, queryset):
        updated = queryset.update(status="cancelada")
        self.message_user(request, f"{updated} corrida(s) marcadas como canceladas.")
    marcar_cancelada.short_description = "Marcar corridas selecionadas como canceladas"

    def exportar_selecionadas_json(self, request, queryset):
        # ação simples que demonstra extensão — redireciona após criar um arquivo ou similar
        count = queryset.count()
        self.message_user(request, f"{count} corrida(s) selecionadas — exportação fictícia executada.")
    exportar_selecionadas_json.short_description = "Exportar corridas selecionadas (exemplo)"

@admin.register(SolicitacaoCarona)
class SolicitacaoCaronaAdmin(admin.ModelAdmin):
    list_display = ("id", "corrida", "passageiro", "status", "data_solicitacao")
    list_filter = ("status", "data_solicitacao")
    search_fields = ("passageiro__username", "corrida__origem", "corrida__destino")
    readonly_fields = ("data_solicitacao",)
