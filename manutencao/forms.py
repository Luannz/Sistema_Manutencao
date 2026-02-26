# ==================== FORMS.PY ====================
from django import forms
from django.forms import ClearableFileInput
from .models import Chamado, Setor, Equipamento

class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True

class ChamadoForm(forms.ModelForm):
    
    class Meta:
        model = Chamado
        fields = ['tipo', 'equipamento', 'setor_avulso', 'descricao', 'prioridade', 'producao_parada']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Descreva o problema...'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'setor_avulso': forms.Select(attrs={'class': 'form-control'}),
            'prioridade': forms.Select(attrs={'class': 'form-control'}),
            'producao_parada': forms.RadioSelect(choices=[(True, 'Sim'), (False, 'Não')], attrs={'class': 'form-check-input'}),
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
        self.fields['equipamento'].widget.attrs.update({'class': 'form-control','id': 'id_equipamento' })
        self.fields['equipamento'].queryset = self.fields['equipamento'].queryset.order_by('nome')
        self.fields['equipamento'].label_from_instance = lambda obj: f"{obj.nome} ({obj.codigo})"

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
        fields = ['nome', 'setor', 'codigo', 'descricao', 'imagem', 'energia']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'setor': forms.Select(attrs={'class': 'form-control'}),
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'energia': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Ex: 1220','pattern': '[0-9]*','title': 'Informe apenas os 4 dígitos do padrão'
            }),
        }