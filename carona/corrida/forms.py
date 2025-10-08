from django import forms
from .models import Corrida

class CorridaForm(forms.ModelForm):
    class Meta:
        model = Corrida
        fields = [
            'origem', 'destino', 'data', 'vagas_disponiveis',
            'horario_saida', 'horario_chegada', 'valor', 'observacoes'
        ]
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horario_saida': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_chegada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'origem': forms.TextInput(attrs={'class': 'form-control'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'vagas_disponiveis': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        saida = cleaned_data.get('horario_saida')
        chegada = cleaned_data.get('horario_chegada')

        if saida and chegada and saida >= chegada:
            raise forms.ValidationError("O horário de chegada deve ser posterior ao horário de saída.")
        
        return cleaned_data
