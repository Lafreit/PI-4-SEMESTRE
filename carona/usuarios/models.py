from django.db import models
from django.utils import timezone

# Create your models here.

class Usuario (models.Model):
    MOTORISTA = 'MOTORISTA'
    PASSAGEIRO = 'PASSAGEIRO'

    TIPO_USUARIO_CHOICE = [
        (MOTORISTA, 'Motorista'),
        (PASSAGEIRO, 'Passageiro'),
    ]

    usuario_id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=128)
    telefone = models.CharField(max_length=20, blank=True)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICE)
    data_cadastro = models.DateField(default=timezone.now)

    def __str__(self):
        return self.nome