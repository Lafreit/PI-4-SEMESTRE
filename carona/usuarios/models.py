from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.

class UsuarioManager(BaseUserManager):
    def create_user(self, email, nome, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, **extra_fields)
        user.set_password(password)  
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, nome, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    MOTORISTA = 'MOTORISTA'
    PASSAGEIRO = 'PASSAGEIRO'
    TIPO_USUARIO_CHOICE = [
        (MOTORISTA, 'Motorista'),
        (PASSAGEIRO, 'Passageiro'),
    ]

    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True)
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICE)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'   
    REQUIRED_FIELDS = ['nome'] 

    def __str__(self):
        return self.nome
