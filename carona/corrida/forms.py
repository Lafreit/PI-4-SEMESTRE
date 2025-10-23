from django import forms
from .models import Corrida

class CorridaForm(forms.ModelForm):
    # Campos ocultos para autocomplete
    bairro_origem = forms.CharField(widget=forms.HiddenInput(), required=False)
    cidade_origem = forms.CharField(widget=forms.HiddenInput(), required=False)
    estado_origem = forms.CharField(widget=forms.HiddenInput(), required=False)
    cep_origem = forms.CharField(widget=forms.HiddenInput(), required=False)

    bairro_destino = forms.CharField(widget=forms.HiddenInput(), required=False)
    cidade_destino = forms.CharField(widget=forms.HiddenInput(), required=False)
    estado_destino = forms.CharField(widget=forms.HiddenInput(), required=False)
    cep_destino = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Corrida
        fields = [
            'origem', 'destino', 'data', 'vagas_disponiveis',
            'horario_saida', 'horario_chegada', 'valor', 'observacoes',
            'bairro_origem', 'cidade_origem', 'estado_origem', 'cep_origem',
            'bairro_destino', 'cidade_destino', 'estado_destino', 'cep_destino', 'status',
        ]
        widgets = {
            'origem': forms.TextInput(attrs={'class': 'form-control', 'id': 'origem', 'maxlength': '100'}),
            'destino': forms.TextInput(attrs={'class': 'form-control', 'id': 'destino', 'maxlength': '100'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_chegada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'vagas_disponiveis': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control', 'initial': 'ativa'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        saida = cleaned_data.get('horario_saida')
        chegada = cleaned_data.get('horario_chegada')

        if saida and chegada and saida >= chegada:
            raise forms.ValidationError("O horário de chegada deve ser posterior ao horário de saída.")
        return cleaned_data
