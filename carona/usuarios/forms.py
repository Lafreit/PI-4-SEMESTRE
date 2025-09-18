from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario

class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'telefone', 'tipo_usuario']

class LoginForm (AuthenticationForm):
    username = forms.EmailField(label="Email")
