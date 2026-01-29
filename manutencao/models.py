# ==================== MODELS.PY ====================
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from PIL import Image
import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
import time

class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ('solicitante', 'Solicitante'),
        ('mecanico', 'Mecânico'),
        ('mecanico_admin', 'Mecânico Admin')
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    telefone = models.CharField(max_length=15, blank=True)
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
    @property
    def is_manutencao(self):
        """Retorna True se o usuário for qualquer tipo de mecânico"""
        return self.tipo in ['mecanico', 'mecanico_admin']


class Setor(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Setor'
        verbose_name_plural = 'Setores'
        ordering = ['nome']
    
    def __str__(self):
        return self.nome

def validar_tamanho_imagem(value):
    limit = 2 * 1024 * 1024  # 2MB
    if value.size > limit:
        raise ValidationError('A imagem é muito pesada. O limite é de 2MB.')
    
def caminho_imagem_equipamento(instance, filename):
    # Pega a extensao original e força para minúsculo (.PNG > .png)
    extensao = os.path.splitext(filename)[1].lower()
    
    # Se por algum motivo o código estiver vazio, usa o nome ou um padrão
    # pra evita erros se o campo codigo falhar por algum motivo
    prefixo = instance.codigo if instance.codigo else "equip"
    
    # Gera o tempo no caso chamado timestamp (Ex: 1705934123)
    timestamp = int(time.time())
    
    # Nome final: codigo_equipamento_1705934123.png
    novo_nome = f"{prefixo}_{timestamp}{extensao}"
    
    # Retorna o caminho final dentro da pasta media
    return os.path.join('equipamentos/', novo_nome)

class Equipamento(models.Model):
    nome = models.CharField(max_length=100)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='equipamentos')
    codigo = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(upload_to=caminho_imagem_equipamento,  validators=[validar_tamanho_imagem], blank=True, null=True, max_length=500)    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Equipamento'
        verbose_name_plural = 'Equipamentos'
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} - {self.setor.nome}"


class Chamado(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('em_progresso', 'Em Progresso'),
        ('concluido', 'Concluído'),
    ]
    
    TIPO_CHOICES = [
        ('equipamento', 'Equipamento'),
        ('avulso', 'Avulso'),
    ]
    
    PRIORIDADE_CHOICES = [
        (1, 'Alta'),
        (2, 'Média'),
        (3, 'Baixa'),
    ]
    
    solicitante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='chamados_criados')
    mecanicos = models.ManyToManyField(Usuario, related_name='chamados_atribuidos', blank=True)  

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    equipamento = models.ForeignKey(Equipamento, on_delete=models.SET_NULL, null=True, blank=True)
    setor_avulso = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    prioridade = models.IntegerField(default=3, choices=PRIORIDADE_CHOICES)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    concluido_em = models.DateTimeField(null=True, blank=True)
    
    observacoes_mecanico = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Chamado'
        verbose_name_plural = 'Chamados'
        ordering = ['-criado_em']

    @property
    def nome_setor(self):
        if self.tipo == 'avulso' and self.setor_avulso:
            return self.setor_avulso.nome
        if self.tipo == 'equipamento' and self.equipamento and self.equipamento.setor:
            return self.equipamento.setor.nome
        return "N/A"
    
    def esta_concluido(self):
        return self.status == 'concluido'

    def pode_mudar_status(self, novo_status):
        if self.status == 'concluido':
            return False
        return True

    def __str__(self):
        return f"#{self.id} - {self.get_status_display()}"
    
    def tempo_aberto(self):
        """
        Retorna o tempo que o chamado ficou/está aberto
        """
        fim = self.concluido_em or timezone.now()
        return fim - self.criado_em

    def tempo_aberto_formatado(self):
        fim = self.concluido_em or timezone.now()
        delta = fim - self.criado_em

        total_minutos = int(delta.total_seconds() // 60)
        horas = total_minutos // 60
        minutos = total_minutos % 60
        dias = horas // 24
        horas_restantes = horas % 24

        if dias > 0:
            return f"{dias}d {horas_restantes}h"
        elif horas > 0:
            return f"{horas}h {minutos}min"
        else:
            return f"{minutos}min"
        
    def save(self, *args, **kwargs):
    # salva o chamado primeiro
        super().save(*args, **kwargs)

        # Se concluido processa as fotos para economizar espaço
        if self.status == 'concluido':
            imagens = self.imagens.all()
            
            for img_obj in imagens:
                if img_obj.imagem:
                    # 1 Abrir a imagem original
                    img_path = img_obj.imagem.path
                    
                    # Verifica se o arquivo existe e se ja nao é um .webp (para não processar duas vezes)
                    if os.path.exists(img_path) and not img_path.lower().endswith('.webp'):
                        img = Image.open(img_path)

                        # 2 Redimensionar (Mantendo a proporção)
                        # Se a foto for gigante, limita a largura máxima para 800px
                        max_width = 800
                        if img.width > max_width:
                            output_size = (max_width, int((max_width / img.width) * img.height))
                            img = img.resize(output_size, Image.LANCZOS)

                        # 3 Converter para WebP em memória
                        temp_thumb = BytesIO()
                        img.save(temp_thumb, format='WEBP', quality=70) # Qualidade 70 
                        temp_thumb.seek(0)

                        # 4 Atualiza o arquivo no objeto
                        # Muda a extensão do nome do arquivo
                        nome_arquivo = os.path.splitext(os.path.basename(img_path))[0] + ".webp"
                        
                        # Salva o novo arquivo e deleta o antigo automaticamente
                        img_obj.imagem.save(nome_arquivo, ContentFile(temp_thumb.read()), save=False)
                        img_obj.save()
                        
                        # 5 Remove o arquivo original antigo  
                        # mas para garantir espaço em disco imediato):
                        if os.path.exists(img_path) and not img_path.endswith('.webp'):
                            os.remove(img_path)


class ImagemChamado(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.ImageField(upload_to='chamados/')
    descricao = models.CharField(max_length=200, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Imagem do Chamado'
        verbose_name_plural = 'Imagens dos Chamados'
        ordering = ['enviado_em']
    
    def __str__(self):
        return f"Imagem #{self.id} - Chamado #{self.chamado.id}"