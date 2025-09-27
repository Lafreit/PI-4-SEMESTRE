from django.db import models

class Veiculo(models.Model):
    motorista = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    modelo = models.CharField(max_length=100)
    placa = models.CharField(max_length=10, unique=True)
    capacidade = models.IntegerField()

    def __str__(self):
        return f"{self.modelo} - {self.placa}"

class Itinerario(models.Model):
    motorista = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)
    origem = models.CharField(max_length=255)
    destino = models.CharField(max_length=255)
    horario_saida = models.TimeField()
    horario_chegada = models.TimeField()
    vagas_disponiveis = models.IntegerField()
    custo_por_passageiro = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Rota de {self.origem} para {self.destino}"

class SolicitacaoCarona(models.Model):
    itinerario = models.ForeignKey(Itinerario, on_delete=models.CASCADE)
    colaborador = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceita', 'Aceita'),
        ('recusada', 'Recusada'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_solicitacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solicitação de {self.colaborador.nome} para {self.itinerario}"




# Create your models here.
