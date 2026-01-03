from decimal import InvalidOperation
from django import forms
from .models import Corrida

class CorridaForm(forms.ModelForm):
    # Campos ocultos para autocomplete (endereço)
    bairro_origem = forms.CharField(widget=forms.HiddenInput(), required=False)
    cidade_origem = forms.CharField(widget=forms.HiddenInput(), required=False)
    estado_origem = forms.CharField(widget=forms.HiddenInput(), required=False)
    cep_origem = forms.CharField(widget=forms.HiddenInput(), required=False)

    bairro_destino = forms.CharField(widget=forms.HiddenInput(), required=False)
    cidade_destino = forms.CharField(widget=forms.HiddenInput(), required=False)
    estado_destino = forms.CharField(widget=forms.HiddenInput(), required=False)
    cep_destino = forms.CharField(widget=forms.HiddenInput(), required=False)

    # Campos lat/lon como DecimalField para validação (hidden)
    origem_lat = forms.DecimalField(
        widget=forms.HiddenInput(),
        required=False,
        max_digits=10,
        decimal_places=7
    )
    origem_lon = forms.DecimalField(
        widget=forms.HiddenInput(),
        required=False,
        max_digits=10,
        decimal_places=7
    )
    destino_lat = forms.DecimalField(
        widget=forms.HiddenInput(),
        required=False,
        max_digits=10,
        decimal_places=7
    )
    destino_lon = forms.DecimalField(
        widget=forms.HiddenInput(),
        required=False,
        max_digits=10,
        decimal_places=7
    )

    # Novo campo: periodicidade (diária, semanal, mensal)
    PERIODICIDADE_CHOICES = [
        ('', '— Nenhuma / Ocorrência única —'),
        ('daily', 'Diariamente'),
        ('weekly', 'Semanalmente'),
        ('monthly', 'Mensalmente'),
    ]
    periodicidade = forms.ChoiceField(
        choices=PERIODICIDADE_CHOICES,
        required=False,
        label="Periodicidade",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Corrida
        fields = [
            'origem', 'destino', 'data', 'vagas_disponiveis',
            'horario_saida', 'horario_chegada', 'valor', 'observacoes',
            # campos de endereço/geo (hidden)
            'origem_lat', 'origem_lon', 'destino_lat', 'destino_lon',
            'bairro_origem', 'cidade_origem', 'estado_origem', 'cep_origem',
            'bairro_destino', 'cidade_destino', 'estado_destino', 'cep_destino',
            # campo de periodicidade adicionado ao form (opcional)
            'periodicidade',
        ]
        widgets = {
            'origem': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'id': 'origem',
                'autocomplete': 'off',
                'placeholder': 'Digite origem...'
            }),
            'destino': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'id': 'destino',
                'autocomplete': 'off',
                'placeholder': 'Digite destino...'
            }),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_chegada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'vagas_disponiveis': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            # hidden fields: IDs compatíveis com o JS (id_lat_origem, id_lon_origem, etc)
            'origem_lat': forms.HiddenInput(attrs={'id': 'id_lat_origem'}),
            'origem_lon': forms.HiddenInput(attrs={'id': 'id_lon_origem'}),
            'destino_lat': forms.HiddenInput(attrs={'id': 'id_lat_destino'}),
            'destino_lon': forms.HiddenInput(attrs={'id': 'id_lon_destino'}),

            'bairro_origem': forms.HiddenInput(attrs={'id': 'id_bairro_origem'}),
            'cidade_origem': forms.HiddenInput(attrs={'id': 'id_cidade_origem'}),
            'estado_origem': forms.HiddenInput(attrs={'id': 'id_estado_origem'}),
            'cep_origem': forms.HiddenInput(attrs={'id': 'id_cep_origem'}),

            'bairro_destino': forms.HiddenInput(attrs={'id': 'id_bairro_destino'}),
            'cidade_destino': forms.HiddenInput(attrs={'id': 'id_cidade_destino'}),
            'estado_destino': forms.HiddenInput(attrs={'id': 'id_estado_destino'}),
            'cep_destino': forms.HiddenInput(attrs={'id': 'id_cep_destino'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        saida = cleaned_data.get('horario_saida')
        chegada = cleaned_data.get('horario_chegada')

        if saida and chegada and saida >= chegada:
            raise forms.ValidationError("O horário de chegada deve ser posterior ao horário de saída.")
        return cleaned_data
