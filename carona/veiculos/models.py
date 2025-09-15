from django.db import models

# Create your models here.
class Veiculo (models.Model):
    Veiculo_id = models.AutoField(primary_key=True)
    motorista = models.ForeignKey(
        'usuarios.Usuario', 
        on_delete= models.CASCADE,
        related_name= 'veiculos'
    )

    modelo = models.CharField(max_length=50)
    placa = models.CharField(max_length=20, unique=True)
    cor = models.CharField(max_length=20, blank=True)
    ano = models.IntegerField()

    def __str__(self):
        return f"{self.modelo} - {self.placa}"