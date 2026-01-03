from django.db import models
from django.conf import settings
from django.utils import timezone
from corrida.models import Corrida

class Payment(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_CREATED = "CREATED"
    STATUS_PAID = "PAID"
    STATUS_EXPIRED = "EXPIRED"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendente"),
        (STATUS_CREATED, "Criado"),
        (STATUS_PAID, "Pago"),
        (STATUS_EXPIRED, "Expirado"),
        (STATUS_FAILED, "Falhou"),
    ]

    PAYMENT_TYPE_CORRIDA = "CORRIDA"
    PAYMENT_TYPE_DEPOSITO = "DEPOSITO"
    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_TYPE_CORRIDA, "Pagamento Corrida"),
        (PAYMENT_TYPE_DEPOSITO, "Depósito Carteira"),
    ]

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="BRL")
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default=PAYMENT_TYPE_CORRIDA)

    abacate_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    external_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    billing_url = models.URLField(null=True, blank=True)

    brCode = models.TextField(null=True, blank=True)
    brCodeBase64 = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=32, null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["abacate_id"]),
            models.Index(fields=["external_id"]),
            models.Index(fields=["status"]),
        ]

    def amount_display(self) -> str:
        try:
            return f"R$ {self.amount_cents/100:.2f}"
        except Exception:
            return f"{self.amount_cents} (cents)"

    def mark_paid(self, when=None, carteira_motorista=None, taxa_percentual: float = 0.0):
        if when is None:
            when = timezone.now()
        self.status = self.STATUS_PAID
        if not self.paid_at:
            self.paid_at = when
        self.save(update_fields=["status", "paid_at", "updated_at"])

        if self.payment_type == self.PAYMENT_TYPE_CORRIDA and self.corrida and carteira_motorista:
            valor_total = self.amount_cents / 100
            taxa = valor_total * taxa_percentual / 100
            repasse = valor_total - taxa
            carteira_motorista.depositar(repasse)


class Carteira(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def depositar(self, valor: float):
        self.saldo += valor
        self.save(update_fields=["saldo", "updated_at"])

    def retirar(self, valor: float):
        if valor > self.saldo:
            raise ValueError("Saldo insuficiente")
        self.saldo -= valor
        self.save(update_fields=["saldo", "updated_at"])

    def __str__(self):
        return f"{self.user.nome} - R${self.saldo:.2f}"


class WebhookEventProcessed(models.Model):
    """
    Registro de eventos processados para idempotência.
    event_id: top-level "id" do payload do AbacatePay.
    """
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, blank=True)
    payload = models.JSONField(null=True, blank=True)  # funciona com SQLite no Django moderno
    processed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"
