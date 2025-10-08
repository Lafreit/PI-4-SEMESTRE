from django.db import models
from django.conf import settings

class Corrida(models.Model):
    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corridas_motorista'
    )
    origem = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    data = models.DateField()  # Alterado para DateField
    vagas_disponiveis = models.PositiveIntegerField()
    horario_saida = models.TimeField()
    horario_chegada = models.TimeField()
    valor = models.DecimalField(max_digits=6, decimal_places=2)
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Corrida de {self.origem} para {self.destino} por {self.motorista.username}'
