from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# ----------------------------------------------------------------------
# 1. MANAGER DE USUÁRIO: Define como criar usuários e superusuários.
#    Obrigatório ao usar AbstractBaseUser.
# ----------------------------------------------------------------------
class UsuarioManager(BaseUserManager):
    def create_user(self, email, nome, password=None, **extra_fields):
        """Cria e salva um Usuário com o email e password dados."""
        if not email:
            raise ValueError('O email é obrigatório para o cadastro.')
        
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, **extra_fields)
        user.set_password(password)  # Hashing da senha
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, password=None, **extra_fields):
        """Cria e salva um superusuário."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, nome, password, **extra_fields)

# ----------------------------------------------------------------------
# 2. MODELO DE USUÁRIO: O modelo de autenticação principal (substitui o User padrão).
# ----------------------------------------------------------------------
class Usuario(AbstractBaseUser, PermissionsMixin):
    # Constantes para os TIPOS DE USUÁRIO
    MOTORISTA = 'motorista'
    PASSAGEIRO = 'passageiro'
    ADMIN = 'admin'
    
    # Constante TIPO_CHOICES: Usada pelo formulário de edição (anteriormente o erro)
    TIPO_CHOICES = [
        (PASSAGEIRO, 'Passageiro'),
        (MOTORISTA, 'Motorista'),
        (ADMIN, 'Administrador'),
    ]

    # CAMPOS DE AUTENTICAÇÃO
    email = models.EmailField(unique=True)
    
    # CAMPOS DE PERFIL BÁSICO
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True)
    
    # CAMPO PRINCIPAL DO TIPO DE USUÁRIO
    tipo_usuario = models.CharField(
        max_length=20, 
        choices=TIPO_CHOICES,
        default=PASSAGEIRO,
        verbose_name='Tipo de Conta'
    )
    
    # CAMPOS DE PERMISSÃO/ESTADO
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Configurações do Manager e Campos de Login
    objects = UsuarioManager()
    USERNAME_FIELD = 'email'  # Campo usado para login
    REQUIRED_FIELDS = ['nome']  # Campos obrigatórios na criação de superusuário

    def __str__(self):
        return self.nome
        
# ----------------------------------------------------------------------
# 3. MODELO DE PERFIL (Profile): Armazena dados extras específicos de Carona.
# ----------------------------------------------------------------------
class Profile(models.Model):
    # Relação 1-para-1 com o modelo Usuario
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_data' 
    )
    
    # CAMPOS ESPECÍFICOS (Principalmente para Motoristas)
    cpf = models.CharField(max_length=11, blank=True, null=True, verbose_name='CPF')
    placa = models.CharField(max_length=8, blank=True, null=True, verbose_name='Placa do Veículo')
    modelo_veiculo = models.CharField(max_length=100, blank=True, null=True, verbose_name='Modelo do Veículo')

    def __str__(self):
        return f'Perfil de {self.user.nome}'
