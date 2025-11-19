# pagamentos/admin.py
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "corrida", "user", "amount_display", "status", "abacate_id", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("abacate_id", "corrida__origem", "corrida__destino", "user__email")
    readonly_fields = ("payload", "created_at", "updated_at")
