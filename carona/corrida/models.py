from django.db import models
from django.conf import settings

class Corrida(models.Model):

    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('cancelada', 'Cancelada'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ativa'
    )

    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corridas_motorista'
    )

    # Origem
    origem = models.CharField(max_length=100)
    bairro_origem = models.CharField(max_length=50, blank=True, null=True)
    cidade_origem = models.CharField(max_length=50, blank=True, null=True)
    estado_origem = models.CharField(max_length=50, blank=True, null=True)
    cep_origem = models.CharField(max_length=10, blank=True, null=True)

    # Destino
    destino = models.CharField(max_length=100)
    bairro_destino = models.CharField(max_length=50, blank=True, null=True)
    cidade_destino = models.CharField(max_length=50, blank=True, null=True)
    estado_destino = models.CharField(max_length=50, blank=True, null=True)
    cep_destino = models.CharField(max_length=10, blank=True, null=True)

    data = models.DateField()
    vagas_disponiveis = models.PositiveIntegerField()
    horario_saida = models.TimeField()
    horario_chegada = models.TimeField()
    valor = models.DecimalField(max_digits=6, decimal_places=2)
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Corrida de {self.origem} para {self.destino} por {self.motorista.email}'
