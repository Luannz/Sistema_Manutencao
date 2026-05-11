from celery import shared_task
from django.utils import timezone
from .models import RotinaManutencao, Chamado
from datetime import timedelta

@shared_task
def verificar_rotinas():
    
    hoje = timezone.localdate()
    rotinas = RotinaManutencao.objects.filter(ativo=True, proxima_execucao__lte=hoje)

    # Pega o usuário que criou a rotina como solicitante
    for rotina in rotinas:
        Chamado.objects.create(
            solicitante=rotina.criado_por,
            tipo=rotina.tipo if rotina.tipo in ['equipamento', 'avulso'] else 'equipamento',
            equipamento=rotina.equipamento,
            setor_avulso=rotina.setor,
            descricao=f"[ROTINA] {rotina.nome_rotina}\n\n{rotina.descricao}",
            prioridade=rotina.prioridade,
            producao_parada=False,
        )

        rotina.ultima_execucao = hoje
        rotina.proxima_execucao = calcular_proxima_execucao(rotina, hoje)
        rotina.save(update_fields=['ultima_execucao', 'proxima_execucao'])


def calcular_proxima_execucao(rotina, a_partir_de):
    from datetime import timedelta

    if rotina.frequencia == 'diario':
        return a_partir_de + timedelta(days=1)
    elif rotina.frequencia == 'semanal':
        return a_partir_de + timedelta(weeks=1)
    elif rotina.frequencia == 'mensal':
        # Mesmo dia, mês seguinte
        mes = a_partir_de.month + 1
        ano = a_partir_de.year + (1 if mes > 12 else 0)
        mes = mes if mes <= 12 else 1
        return a_partir_de.replace(year=ano, month=mes)
    elif rotina.frequencia == 'personalizado':
        return a_partir_de + timedelta(days=rotina.intervalo_dias)