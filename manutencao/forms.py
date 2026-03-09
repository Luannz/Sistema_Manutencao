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
        fields = ['nome', 'descricao', 'energia']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'energia': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
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
            'imagem': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*','capture': 'environment'}),
            'energia': forms.Select(attrs={'class': 'form-select'}),
        }
    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')

        # 1. Se o código estiver vazio (ou for None), não fazemos nada.
        # O banco permitirá múltiplos NULLs se o campo for null=True.
        if not codigo:
            return None

        # 2. Verifica se já existe um equipamento com esse código.
        # O self.instance ajuda a ignorar o próprio equipamento se estivermos EDITANDO.
        exists = Equipamento.objects.filter(codigo=codigo).exclude(pk=self.instance.pk).exists()
        
        if exists:
            raise forms.ValidationError("Este código de equipamento já está em uso por outra máquina.")
        
        return codigo