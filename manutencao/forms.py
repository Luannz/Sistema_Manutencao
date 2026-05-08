# ==================== FORMS.PY ====================
from django import forms
from django.forms import ClearableFileInput
from .models import Chamado, Setor, Equipamento, RotinaManutencao

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
    

class RotinaManutencaoForm(forms.ModelForm):
    class Meta:
        model = RotinaManutencao
        fields = ['nome_rotina','tipo','setor','equipamento', 'descricao', 'prioridade', 
                  'frequencia', 'intervalo_dias', 'proxima_execucao']
        widgets = {
            'proxima_execucao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'nome_rotina': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            # O setor é preenchido via JS baseado no select de auxílio, então deixamos oculto
            'setor': forms.HiddenInput(attrs={'id': 'id_setor'}),
            'equipamento': forms.Select(attrs={'class': 'form-select'}),
            'prioridade': forms.Select(choices=[(1, 'Alta'), (2, 'Média'), (3, 'Baixa')], attrs={'class': 'form-select'}),
            'frequencia': forms.Select(attrs={'class': 'form-select'}),
            'intervalo_dias': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 15'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Como o usuário vai alternar entre Equipamento e Setor,
        # esses campos não podem ser obrigatórios no nível do Python (validação do formulário),
        # pois um deles sempre estará vazio.
        self.fields['equipamento'].widget.attrs['disabled'] = 'disabled'
        self.fields['equipamento'].choices = [('', 'Selecione um setor primeiro...')]
        self.fields['equipamento'].required = False
        self.fields['setor'].required = False
        self.fields['intervalo_dias'].required = False