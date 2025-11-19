# pagamentos/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from corrida.models import Corrida

class Payment(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pendente"),
        ("CREATED", "Criado"),
        ("PAID", "Pago"),
        ("EXPIRED", "Expirado"),
        ("FAILED", "Falhou"),
    ]

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    amount_cents = models.PositiveIntegerField()
    abacate_id = models.CharField(max_length=128, null=True, blank=True)
    brCode = models.TextField(null=True, blank=True)
    brCodeBase64 = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def amount_display(self):
        return f"R$ {self.amount_cents/100:.2f}"

    def __str__(self):
        return f"Payment {self.pk} - Corrida {self.corrida_id} - {self.status}"
