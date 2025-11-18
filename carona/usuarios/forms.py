from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario, Profile 
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password 
from django.contrib.auth.password_validation import validate_password 

Usuario = get_user_model()

# ----------------------------------------------------------------------
# 1. FORMULÁRIO DE REGISTRO (RegistroForm) — sem campos de senha
# ----------------------------------------------------------------------
class RegistroForm(forms.ModelForm):
    # Campos de senha personalizados
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text='',
    )
    password2 = forms.CharField(
        label="Confirmação de Senha",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        strip=False,
        help_text='Digite a mesma senha novamente para verificar.'
    )

    class Meta:
        model = Usuario
        fields = ('nome', 'email', 'telefone', 'tipo_usuario', 'password', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Labels em português
        self.fields['nome'].label = 'Nome Completo'
        self.fields['email'].label = 'E-mail'
        self.fields['telefone'].label = 'Telefone'
        self.fields['tipo_usuario'].label = 'Tipo de Conta'

        # Aplica a classe Bootstrap a todos os campos
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")

        if password and password2 and password != password2:
            raise forms.ValidationError("As duas senhas digitadas não coincidem.")

        # Validação padrão do Django
        if password:
            validate_password(password, self.instance)

        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data["password"]
        user.password = make_password(password)
        if commit:
            user.save()
        return user
# ----------------------------------------------------------------------
# 2. FORMULÁRIO DE LOGIN (LoginForm)
# ----------------------------------------------------------------------
class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite seu e-mail'
        })
    )

    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garante que ambos os campos estejam estilizados corretamente
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})

# ----------------------------------------------------------------------
# 3. FORMULÁRIO DE PERFIL (Passageiro)
# ----------------------------------------------------------------------
class PerfilPassageiroForm(forms.ModelForm):
    nome = forms.CharField(
        label='Nome Completo',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    telefone = forms.CharField(
        label='Telefone',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    tipo_usuario = forms.ChoiceField(
        label='Tipo de Conta',
        choices=Usuario.TIPO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    new_password1 = forms.CharField(
        label='Nova Senha',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Deixe em branco se não quiser alterar a senha.'
    )
    new_password2 = forms.CharField(
        label='Confirme a Nova Senha',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = ['nome', 'email', 'telefone', 'tipo_usuario']

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password1 != new_password2:
            self.add_error('new_password2', 'As novas senhas não coincidem.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password1 = self.cleaned_data.get('new_password1')

        if new_password1:
            user.password = make_password(new_password1)

        if commit:
            user.save()

        return user

# ----------------------------------------------------------------------
# 4. FORMULÁRIO DE PERFIL (Motorista)
# ----------------------------------------------------------------------
class PerfilMotoristaForm(forms.ModelForm):
    cpf = forms.CharField(
        label='CPF',
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apenas números'})
    )
    placa = forms.CharField(
        label='Placa do Veículo',
        max_length=8,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    modelo_veiculo = forms.CharField(
        label='Modelo do Veículo',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profile
        fields = ['cpf', 'placa', 'modelo_veiculo']
class VeiculoForm(forms.ModelForm):
    placa = forms.CharField(
        label='Placa do Veículo',
        max_length=8,
        required=True,  # Alterado para obrigatório na atualização
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: ABC-1234'})
    )
    modelo_veiculo = forms.CharField(
        label='Modelo e Ano',
        max_length=100,
        required=True, # Alterado para obrigatório na atualização
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Fiat Palio 2018'})
    )
    cor = forms.CharField( # Adicionando cor, que é um campo comum para Veículo
        label='Cor',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Prata'})
    )
    assentos = forms.IntegerField( # Assumindo que você tem um campo 'assentos' no modelo Profile/Veiculo
        label='Assentos Disponíveis (Excluindo o motorista)',
        min_value=1,
        max_value=6,
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profile
        # Campos que o Motorista pode querer atualizar sobre o veículo
        fields = ['placa', 'modelo_veiculo', 'cor', 'assentos'] 
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
