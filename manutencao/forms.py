# ==================== FORMS.PY ====================
from django import forms
from django.forms import ClearableFileInput
from .models import Chamado, Setor, Equipamento

class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True

class ChamadoForm(forms.ModelForm):
    
    class Meta:
        model = Chamado
        fields = ['tipo', 'equipamento', 'setor_avulso', 'descricao', 'prioridade']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Descreva o problema...'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'equipamento': forms.Select(attrs={'class': 'form-control'}),
            'setor_avulso': forms.Select(attrs={'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        equipamento = cleaned_data.get('equipamento')
        setor_avulso = cleaned_data.get('setor_avulso')
        
        if tipo == 'equipamento' and not equipamento:
            raise forms.ValidationError('Selecione um equipamento para este tipo de chamado')
        
        if tipo == 'avulso' and not setor_avulso:
            raise forms.ValidationError('Selecione um setor para chamado avulso')
        
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk and self.instance.status == 'concluido':
            for field in self.fields.values():
                field.disabled = True


class SetorForm(forms.ModelForm):
    class Meta:
        model = Setor
        fields = ['nome', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = ['nome', 'setor', 'codigo', 'descricao', 'imagem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'setor': forms.Select(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }