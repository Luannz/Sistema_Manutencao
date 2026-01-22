# ==================== MODELS.PY ====================
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
import os

class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ('solicitante', 'Solicitante'),
        ('mecanico', 'Mecânico'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    telefone = models.CharField(max_length=15, blank=True)
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'


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


class Equipamento(models.Model):
    nome = models.CharField(max_length=100)
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='equipamentos')
    codigo = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(upload_to='equipamentos/', blank=True, null=True)
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
    mecanicos = models.ManyToManyField(Usuario, related_name='chamados_atribuidos', limit_choices_to={'tipo': 'mecanico'})
    
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
        # primeiro salva o chamado normalmente
        super().save(*args, **kwargs)
        # SE o status for concluído, deletamos as imagens relacionadas
        if self.status == 'concluido':
            imagens = self.imagens.all() # 'imagens' é o related_name usado
            for img in imagens:
                # Deleta o arquivo físico do HD/Servidor
                if img.imagem and os.path.isfile(img.imagem.path):
                    os.remove(img.imagem.path)
                # Deleta o registro no banco de dados
                img.delete()


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