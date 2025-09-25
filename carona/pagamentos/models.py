from django.db import models

class Pagamento(models.Model):
    solicitacao_carona = models.OneToOneField('passageiros.SolicitacaoCarona', on_delete=models.CASCADE)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    taxa_app = models.DecimalField(max_digits=10, decimal_places=2)
    valor_motorista = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=50)
    STATUS_CHOICE = [
        ('penddente', 'Pendente'),
        ('processado', 'Processado'),
        ('falha', 'falha'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICE, default='penddente')
    data_pagamento = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Pagamento {self.solicitacao_carona.id}'