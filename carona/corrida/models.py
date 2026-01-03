from django.db import models
from django.conf import settings
from django.utils import timezone


class CorridaTemplate(models.Model):
    """
    Template de corrida (trajeto recorrente). Lógica de geração fica fora - em services.
    """
    FREQ_DAILY = "daily"
    FREQ_WEEKLY = "weekly"
    FREQ_MONTHLY = "monthly"
    FREQ_CHOICES = [
        (FREQ_DAILY, "Diariamente"),
        (FREQ_WEEKLY, "Semanalmente"),
        (FREQ_MONTHLY, "Mensalmente"),
    ]

    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corrida_templates'
    )

    titulo = models.CharField(max_length=120, blank=True, null=True)
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

    horario_saida = models.TimeField(null=True, blank=True)
    horario_chegada = models.TimeField(null=True, blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    frequency = models.CharField(max_length=10, choices=FREQ_CHOICES, default=FREQ_WEEKLY)
    days_of_week = models.JSONField(default=list, blank=True)  # [0..6] 0=segunda

    max_passengers = models.PositiveIntegerField(default=4)
    valor = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template de Corrida"
        verbose_name_plural = "Templates de Corrida"

    def __str__(self):
        titulo = self.titulo or f"{self.origem} → {self.destino}"
        return f"Template {titulo} ({self.motorista})"


class Corrida(models.Model):
    """
    Ocorrência de corrida (executável). Métodos que alteram somente o estado do objeto ficam aqui.
    """
    STATUS_ATIVA = 'ativa'
    STATUS_EM_ANDAMENTO = 'em_andamento'
    STATUS_FINALIZADA = 'finalizada'
    STATUS_CANCELADA = 'cancelada'

    STATUS_CHOICES = [
        (STATUS_ATIVA, 'Ativa'),
        (STATUS_EM_ANDAMENTO, 'Em andamento'),
        (STATUS_FINALIZADA, 'Finalizada'),
        (STATUS_CANCELADA, 'Cancelada'),
    ]

    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corridas_motorista'
    )

    parent_template = models.ForeignKey(CorridaTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs')

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

    data = models.DateField(null=True, blank=True)
    horario_saida = models.TimeField(null=True, blank=True)
    horario_chegada = models.TimeField(null=True, blank=True)

    vagas_disponiveis = models.PositiveIntegerField(default=1)
    valor = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ATIVA)

    origem_lat = models.FloatField(null=True, blank=True)
    origem_lon = models.FloatField(null=True, blank=True)
    destino_lat = models.FloatField(null=True, blank=True)
    destino_lon = models.FloatField(null=True, blank=True)

    rota = models.JSONField(default=list, blank=True)
    distancia_m = models.FloatField(null=True, blank=True)
    pontos_count = models.PositiveIntegerField(default=0)

    bbox_min_lat = models.FloatField(null=True, blank=True)
    bbox_max_lat = models.FloatField(null=True, blank=True)
    bbox_min_lon = models.FloatField(null=True, blank=True)
    bbox_max_lon = models.FloatField(null=True, blank=True)

    iniciada_em = models.DateTimeField(null=True, blank=True)
    encerrada_em = models.DateTimeField(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Corrida {self.origem} → {self.destino} ({self.motorista})'

    @classmethod
    def create_from_template(cls, template: CorridaTemplate, run_date):
        """
        Factory simples - cria uma Corrida a partir de um template e uma data.
        """
        return cls.objects.create(
            motorista=template.motorista,
            parent_template=template,
            origem=template.origem,
            bairro_origem=template.bairro_origem,
            cidade_origem=template.cidade_origem,
            estado_origem=template.estado_origem,
            cep_origem=template.cep_origem,
            destino=template.destino,
            bairro_destino=template.bairro_destino,
            cidade_destino=template.cidade_destino,
            estado_destino=template.estado_destino,
            cep_destino=template.cep_destino,
            data=run_date,
            horario_saida=template.horario_saida,
            horario_chegada=template.horario_chegada,
            vagas_disponiveis=template.max_passengers,
            valor=template.valor,
            observacoes=template.observacoes
        )

    def set_bbox_from_rota(self):
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

    # ---- métodos que ALTERAM APENAS O PRÓPRIO OBJETO (bons no model) ----
    def iniciar(self):
        if self.status != self.STATUS_ATIVA:
            return False

        self.status = self.STATUS_EM_ANDAMENTO
        self.iniciada_em = timezone.now()
        self.save(update_fields=['status', 'iniciada_em', 'atualizado_em'])

        # --- gera Payment automaticamente ---
        from pagamentos.models import Payment
        from pagamentos.services import criar_pix_qr  # ajuste para onde você implementou

        if not Payment.objects.filter(corrida=self).exists():
            valor = self.valor or (self.parent_template.valor if self.parent_template else 0)
            amount_cents = int(round(float(valor) * 100))

            p = Payment.objects.create(
                corrida=self,
                user=None,  # passageiros ainda não definidos
                amount_cents=amount_cents,
                status="PENDING"
            )

            external_id = f"corrida-{self.id}-payment-{p.id}"
            result = criar_pix_qr(amount_cents, f"Pagamento corrida #{self.id}", external_id)

            if result.get("ok"):
                data = result.get("data", {})
                p.brCode = data.get("brCode")
                p.brCodeBase64 = data.get("brCodeBase64")
                p.abacate_id = data.get("id")
                p.status = "CREATED"
                p.save()

        return True


    def encerrar(self):
        if self.status != self.STATUS_EM_ANDAMENTO:
            return False
        self.status = self.STATUS_FINALIZADA
        self.encerrada_em = timezone.now()
        self.save(update_fields=['status', 'encerrada_em', 'atualizado_em'])
        return True

    def decrease_vaga(self):
        if self.vagas_disponiveis <= 0:
            return False
        self.vagas_disponiveis -= 1
        self.save(update_fields=['vagas_disponiveis', 'atualizado_em'])
        return True

    def increase_vaga(self):
        # respeita max_passengers do template quando presente
        if self.parent_template:
            max_p = self.parent_template.max_passengers
            if self.vagas_disponiveis >= max_p:
                return False
        self.vagas_disponiveis += 1
        self.save(update_fields=['vagas_disponiveis', 'atualizado_em'])
        return True

    def confirmed_passengers_count(self):
        from .models import SolicitacaoCarona
        return SolicitacaoCarona.objects.filter(corrida=self, status=SolicitacaoCarona.STATUS_ACEITA).count()

    def confirmed_passengers(self):
        from .models import SolicitacaoCarona
        return SolicitacaoCarona.objects.filter(corrida=self, status=SolicitacaoCarona.STATUS_ACEITA).select_related('passageiro')


class SolicitacaoCarona(models.Model):
    STATUS_PENDENTE = 'PENDENTE'
    STATUS_ACEITA = 'ACEITA'
    STATUS_RECUSADA = 'RECUSADA'
    STATUS_CANCELADA = 'CANCELADA'

    STATUS_CHOICES = [
        (STATUS_PENDENTE, 'Pendente'),
        (STATUS_ACEITA, 'Aceita'),
        (STATUS_RECUSADA, 'Recusada'),
        (STATUS_CANCELADA, 'Cancelada'),
    ]

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name='solicitacoes')
    passageiro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solicitacoes')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDENTE)

    class Meta:
        unique_together = ('corrida', 'passageiro')
        indexes = [
            models.Index(fields=['corrida', 'status']),
        ]

    def __str__(self):
        return f"{self.passageiro} → {self.corrida} ({self.status})"



