# ==================== VIEWS.PY ====================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Case, When, Value, IntegerField, Q
from .models import Usuario, Setor, Equipamento, Chamado, ImagemChamado
from .forms import ChamadoForm, SetorForm, EquipamentoForm
from datetime import datetime, timedelta


def login_view(request):
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Credenciais inválidas')
    return render(request, 'manutencao/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.tipo == 'mecanico':
        return redirect('mecanico_dashboard')
    else:
        return redirect('solicitante_dashboard')


@login_required
def solicitante_dashboard(request):
    if request.user.tipo != 'solicitante':
        return redirect('dashboard')
    
    #Pega a lista base 
    chamados_list = Chamado.objects.filter(solicitante=request.user)

    #Aplica os filtros na lista completa
    status_filtro = request.GET.get('status')
    if status_filtro:
        chamados_list = chamados_list.filter(status=status_filtro)

    data_filtro = request.GET.get('data')
    if data_filtro == 'hoje':
        chamados_list = chamados_list.filter(criado_em__date=datetime.today())
    elif data_filtro == 'semana':
        uma_semana_atras = datetime.today() - timedelta(days=7)
        chamados_list = chamados_list.filter(criado_em__gte=uma_semana_atras)

    ordem = request.GET.get('ordem', '-criado_em')
    chamados_list = chamados_list.order_by(ordem)

    # Paginação (depois dos filtros)
    paginator = Paginator(chamados_list, 12) # chamados por pagina
    page_number = request.GET.get('page')
    chamados_paginados = paginator.get_page(page_number)

    return render(request, 'manutencao/solicitante_dashboard.html', {
        'chamados': chamados_paginados, 
        'status_atual': status_filtro,
        'ordem_atual': ordem,
        'data_atual': data_filtro,
    })


@login_required
def mecanico_dashboard(request):
    if request.user.tipo != 'mecanico':
        return redirect('dashboard')
    
    # lógica de filtros continua IGUAL até o final
    chamados_list = Chamado.objects.filter(mecanicos=request.user).annotate(
        ordem_status=Case(
            When(status='pendente', then=Value(1)),
            When(status='em_progresso', then=Value(2)),
            When(status='concluido', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    )

    status_filtro = request.GET.get('status')
    if status_filtro:
        chamados_list = chamados_list.filter(status=status_filtro)

    data_filtro = request.GET.get('data')
    if data_filtro == 'hoje':
        chamados_list = chamados_list.filter(criado_em__date=datetime.today())
    elif data_filtro == 'semana':
        uma_semana_atras = datetime.today() - timedelta(days=7)
        chamados_list = chamados_list.filter(criado_em__gte=uma_semana_atras)

    ordem = request.GET.get('ordem', 'ordem_status') # ajustado para respeitar a anotação se não houver ordem
    chamados_list = chamados_list.order_by(ordem, '-criado_em')

    # 2. CALCULAR OS TOTAIS ANTES DA PAGINACÃO
    pendentes = chamados_list.filter(status='pendente').count()
    em_progresso = chamados_list.filter(status='em_progresso').count()
    concluidos = chamados_list.filter(status='concluido').count()

    # 3. APLICAR A PAGINACÃO
    itens_por_pagina = 12 
    paginator = Paginator(chamados_list, itens_por_pagina)
    
    page_number = request.GET.get('page')
    chamados_paginados = paginator.get_page(page_number)

    return render(request, 'manutencao/mecanico_dashboard.html', {
        'chamados': chamados_paginados, 
        'pendentes': pendentes,
        'em_progresso': em_progresso,
        'concluidos': concluidos,
        'status_atual': status_filtro,
        'ordem_atual': ordem,
        'data_atual': data_filtro, 
    })


@login_required
def historicos(request):
    if request.user.tipo != 'mecanico':
        return redirect('dashboard')
    
    setores = Setor.objects.all()
    equipamentos = Equipamento.objects.all()

    q = request.GET.get('q') or ''
    setor_id = request.GET.get('setor')

    # Filtro de Equipamentos
    if q:
        equipamentos = equipamentos.filter(
            Q(nome__icontains=q) | Q(codigo__icontains=q)
        )
    if setor_id:
        equipamentos = equipamentos.filter(setor_id=setor_id)
    
    # limita o tanto de chamado que vai mostrar e só limita o setor se nao tiver nenhum selecionado
    equipamentos = equipamentos[:10]
    if not setor_id:
        setores = setores[:10]

    #Anexa último chamado ao EQUIPAMENTO
    for eq in equipamentos:
        eq.ultimo_chamado = Chamado.objects.filter(
            equipamento=eq, status='concluido'
        ).order_by('-concluido_em').first()

    #Anexa ultimo chamado AVULSO ao SETOR
    #permite ver a última manutenção predial/infra do setor
    for st in setores:
        st.ultimo_avulso = Chamado.objects.filter(
            setor_avulso=st, tipo='avulso', status='concluido'
        ).order_by('-concluido_em').first()

    return render(request, 'manutencao/historicos.html', {
        'equipamentos': equipamentos,
        'setores': setores,
        'search_query': q,
        'setor_selecionado': setor_id,
    })


@login_required
def historico_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id)
    chamados = Chamado.objects.filter(equipamento=equipamento).order_by('-criado_em')
    
    return render(request, 'manutencao/historico_equipamento.html', {
        'equipamento': equipamento,
        'chamados': chamados
    })

@login_required
def historico_setor(request, setor_id):
    setor = get_object_or_404(Setor, id=setor_id)
    # Filtra apenas chamados do tipo avulso para este setor
    chamados = Chamado.objects.filter(setor_avulso=setor, tipo='avulso').order_by('-criado_em')
    
    return render(request, 'manutencao/historico_setor.html', {
        'setor': setor,
        'chamados': chamados
    })



@login_required
def criar_chamado(request):
    if request.method == 'POST':
        form = ChamadoForm(request.POST, request.FILES)
        if form.is_valid():
            chamado = form.save(commit=False)
            
        
            chamado.solicitante = request.user 
            
            # Lógica para setor avulso
            if chamado.tipo == 'avulso':
                setor_id = request.POST.get('setor_avulso')
                if setor_id:
                    chamado.setor_avulso_id = setor_id
            
            # Agora o save() não vai mais falhar porque o solicitante_id não será NULL
            chamado.save()

            # Salvar mecânicos (Muitos-para-Muitos)
            mecanicos_ids = request.POST.getlist('mecanicos')
            if mecanicos_ids:
                chamado.mecanicos.set(mecanicos_ids)

            # Salvar as múltiplas imagens do JavaScript
            arquivos = request.FILES.getlist('imagens')
            for f in arquivos:
                ImagemChamado.objects.create(chamado=chamado, imagem=f)

            return redirect('solicitante_dashboard')
    else:
        form = ChamadoForm()
    mecanicos = Usuario.objects.filter(tipo='mecanico')
    setores = Setor.objects.all()
    
    return render(request, 'manutencao/criar_chamado.html', {
        'form': form,
        'mecanicos': mecanicos,
        'setores': setores
    })


@login_required
def atualizar_status(request, chamado_id):
    if request.user.tipo != 'mecanico':
        return redirect('dashboard')
    
    chamado = get_object_or_404(Chamado, id=chamado_id, mecanicos=request.user)
    if chamado.status == 'concluido':
        messages.error(request, 'Este chamado já foi concluído.')
        return redirect('chamado_detalhe', chamado.id)

    if request.method == 'POST':
        novo_status = request.POST.get('status')
        observacoes = request.POST.get('observacoes', '')
        
        if novo_status in ['pendente', 'em_progresso', 'concluido']:
            chamado.status = novo_status
            
            if novo_status == 'em_progresso' and not chamado.iniciado_em:
                chamado.iniciado_em = timezone.now()
            elif novo_status == 'concluido' and not chamado.concluido_em:
                chamado.concluido_em = timezone.now()
            
            if observacoes:
                chamado.observacoes_mecanico = observacoes
            
            chamado.save()
            messages.success(request, 'Status atualizado com sucesso!')
        
        return redirect('mecanico_dashboard')
    
    return render(request, 'manutencao/atualizar_status.html', {
        'chamado': chamado
    })


@login_required
def gerenciar_setores(request):
    if request.user.tipo != 'mecanico':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SetorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Setor cadastrado com sucesso!')
            return redirect('gerenciar_setores')
    else:
        form = SetorForm()
    
    setores = Setor.objects.all()
    return render(request, 'manutencao/gerenciar_setores.html', {
        'form': form,
        'setores': setores
    })


@login_required
def gerenciar_equipamentos(request):
    if request.user.tipo != 'mecanico':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EquipamentoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipamento cadastrado com sucesso!')
            return redirect('gerenciar_equipamentos')
    else:
        form = EquipamentoForm()
    
    equipamentos = Equipamento.objects.all()
    return render(request, 'manutencao/gerenciar_equipamentos.html', {
        'form': form,
        'equipamentos': equipamentos
    })


@login_required
def get_equipamentos_por_setor(request, setor_id):
    equipamentos = Equipamento.objects.filter(setor_id=setor_id).values('id', 'nome', 'imagem')
    # Converter caminho da imagem para URL completa
    for eq in equipamentos:
        if eq['imagem']:
            eq['imagem'] = request.build_absolute_uri('/media/' + eq['imagem'])
    return JsonResponse(list(equipamentos), safe=False)
