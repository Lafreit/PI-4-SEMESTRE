from django.db import models
from django.conf import settings
from decimal import Decimal

class Corrida(models.Model):
    STATUS_CHOICES = [
        ('ativa', 'Ativa'),
        ('cancelada', 'Cancelada'),
    ]

    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corridas_motorista'
    )

    # Endereços (textos preenchidos pelo motorista)
    origem = models.CharField(max_length=100)
    bairro_origem = models.CharField(max_length=50, blank=True, null=True)
    cidade_origem = models.CharField(max_length=50, blank=True, null=True)
    estado_origem = models.CharField(max_length=50, blank=True, null=True)
    cep_origem = models.CharField(max_length=10, blank=True, null=True)

    destino = models.CharField(max_length=100)
    bairro_destino = models.CharField(max_length=50, blank=True, null=True)
    cidade_destino = models.CharField(max_length=50, blank=True, null=True)
    estado_destino = models.CharField(max_length=50, blank=True, null=True)
    cep_destino = models.CharField(max_length=10, blank=True, null=True)

    # Dados da corrida
    data = models.DateField(null=True, blank=True)
    horario_saida = models.TimeField(null=True, blank=True)
    horario_chegada = models.TimeField(null=True, blank=True)
    vagas_disponiveis = models.PositiveIntegerField(default=1)
    valor = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ativa')

    # Coordenadas e rota (preenchidas automaticamente via ORS)
    origem_lat = models.FloatField(null=True, blank=True)
    origem_lon = models.FloatField(null=True, blank=True)
    destino_lat = models.FloatField(null=True, blank=True)
    destino_lon = models.FloatField(null=True, blank=True)

    # rota: armazenar lista de pontos [ [lat, lon], [lat, lon], ... ]
    rota = models.JSONField(default=list, blank=True)

    # metadados da rota
    distancia_m = models.FloatField(null=True, blank=True)
    pontos_count = models.PositiveIntegerField(default=0)

    # bbox para busca rápida
    bbox_min_lat = models.FloatField(null=True, blank=True)
    bbox_max_lat = models.FloatField(null=True, blank=True)
    bbox_min_lon = models.FloatField(null=True, blank=True)
    bbox_max_lon = models.FloatField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Corrida {self.origem} → {self.destino} ({self.motorista})'

    def set_bbox_from_rota(self):
        """
        Preenche bbox_* com base na self.rota (espera rota como [[lat, lon], ...]).
        """
        if not self.rota:
            self.bbox_min_lat = self.bbox_max_lat = None
            self.bbox_min_lon = self.bbox_max_lon = None
            return
        lats = [p[0] for p in self.rota]
        lons = [p[1] for p in self.rota]
        self.bbox_min_lat = min(lats)
        self.bbox_max_lat = max(lats)
        self.bbox_min_lon = min(lons)
        self.bbox_max_lon = max(lons)


class SolicitacaoCarona(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('ACEITA', 'Aceita'),
        ('RECUSADA', 'Recusada'),
        ('CANCELADA', 'Cancelada'),
    ]

    corrida = models.ForeignKey('Corrida', on_delete=models.CASCADE, related_name='solicitacoes')
    passageiro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitacoes')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')

    def __str__(self):
        return f"{self.passageiro} → {self.corrida} ({self.status})"