# notificacao/models.py
from django.db import models
from django.conf import settings




class Notificacao(models.Model):
    TIPO_SOLICITACAO_RECEBIDA = 'solicitacao_recebida'
    TIPO_SOLICITACAO_RESPONDIDA = 'solicitacao_respondida'
    TIPO_CHOICES = [
        (TIPO_SOLICITACAO_RECEBIDA, 'Solicitação recebida'),
        (TIPO_SOLICITACAO_RESPONDIDA, 'Solicitação respondida'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificacoes')
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    dados = models.JSONField(default=dict, blank=True)  # ex: {"corrida_id": 12, "solicitacao_id": 33}
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em']

    def __str__(self):
        return f"{self.usuario} - {self.titulo}"
