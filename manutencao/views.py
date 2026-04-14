# ==================== VIEWS.PY ====================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Case, When, Value, IntegerField, Q , Max, F
from .models import Usuario, Setor, Equipamento, Chamado, ImagemChamado, Energia
from .forms import ChamadoForm, SetorForm, EquipamentoForm
from datetime import datetime, timedelta
import os


def login_view(request):
    if request.user.is_authenticated:
        return redirect ('dashboard')
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
    if request.user.tipo in ['mecanico_admin', 'mecanico']:
        return redirect('mecanico_dashboard')
    # Se não for mecânico, trata como solicitante
    else: 
        return redirect('solicitante_dashboard')
    


@login_required
def solicitante_dashboard(request):
    if request.user.tipo not in ['solicitante', 'solicitante_admin']:
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
def dashboard_admin_manutencao(request):
    if request.user.tipo not in ['mecanico_admin', 'solicitante_admin']:
        return redirect('dashboard')
    
    # 1 Chamados NOVOS (Aguardando designacao)
    chamados_novos = Chamado.objects.filter(mecanicos__isnull=True).order_by('-criado_em')
    
    # 2 Chamados EM ANDAMENTO (ja designados)
    queryset_andamento = Chamado.objects.filter(mecanicos__isnull=False)\
        .select_related('equipamento', 'equipamento__setor', 'setor_avulso')\
        .prefetch_related('mecanicos')\
        .order_by('-criado_em')\
        .distinct()
    
    total_andamento = queryset_andamento.count()
    chamados_em_andamento = queryset_andamento[:10]
    
    # 3 Dados auxiliares para o dashboard
    mecanicos = Usuario.objects.filter(tipo__in=['mecanico', 'mecanico_admin'])
    setores = Setor.objects.all()
    equipamentos = Equipamento.objects.all()
    
    
    return render(request, 'manutencao/admin_dashboard.html', {
        'chamados_novos': chamados_novos,
        'chamados_em_andamento': chamados_em_andamento,
        'mecanicos': mecanicos,
        'setores': setores,
        'equipamentos': equipamentos,
        'total_andamento': total_andamento
    })

@login_required
def atribuir_chamado(request, chamado_id):
    if request.user.tipo not in ['mecanico_admin', 'solicitante_admin']:
        return redirect('dashboard')
        
    chamado = get_object_or_404(Chamado, id=chamado_id)
    
    if request.method == 'POST':
        #  Captura a nova prioridade definida pelo Admin e salva no banco
        nova_prioridade = request.POST.get('prioridade')
        if nova_prioridade:
            chamado.prioridade = int(nova_prioridade)
            chamado.save() # importante salvar para a prioridade persistir

        # Atribui a equipe de mecânicos
        mecanicos_ids = request.POST.getlist('mecanicos')
        if mecanicos_ids:
            chamado.mecanicos.set(mecanicos_ids)
            messages.success(request, f"Chamado {chamado.id} atribuído e prioridade atualizada!")
        else:
            messages.warning(request, f"Chamado {chamado.id} atualizado, mas sem equipe técnica.")
            
    return redirect('dashboard_admin_manutencao')

@login_required
def mecanico_dashboard(request):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    # --- LÓGICA DE PERMISSÃO ---
    if request.user.tipo == 'mecanico_admin':
        # Admin vê TUDO que ja tenha mecanicos atribuidos (removendo o filtro de mecanicos=request.user)
        chamados_list = Chamado.objects.filter(mecanicos__isnull=False).distinct() # Garante que só traga chamados com mecanicos atribuidos
    else:
        # Mecânico comum vê apenas os dele
        chamados_list = Chamado.objects.filter(mecanicos=request.user)

    # lógica de filtros continua IGUAL 
    chamados_list = chamados_list.annotate(
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
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    # Captura dos filtros do GET
    lista_todos_setores = Setor.objects.all().order_by('nome')
    setores = Setor.objects.all()
    equipamentos = Equipamento.objects.all().select_related('energia', 'setor__energia')
    q = request.GET.get('q') or ''
    setor_id = request.GET.get('setor')
    status_filtro = request.GET.get('status')

    # Se houver filtro de status
    filtro_status_eq = Q(chamado__isnull=False)
    filtro_status_st = Q(chamado__tipo='avulso')

    if status_filtro:
        filtro_status_eq &= Q(chamado__status=status_filtro)
        filtro_status_st &= Q(chamado__status=status_filtro)

    # 1. Anotações com filtro de status
    equipamentos = equipamentos.annotate(
        ultima_atividade=Max('chamado__criado_em', filter=filtro_status_eq)
    )

    if q:
        equipamentos = equipamentos.filter(
            Q(nome__icontains=q) | 
            Q(codigo__icontains=q) |
            Q(energia__numero__icontains=q) |
            Q(setor__energia__numero__icontains=q)
        ).distinct()

    if setor_id:
        equipamentos = equipamentos.filter(setor_id=setor_id)
    if status_filtro:
        equipamentos = equipamentos.filter(ultima_atividade__isnull=False)
    # 2. Ordenamos pela atividade mais recente (quem teve chamado hoje aparece primeiro)
    # Usamos F() com nulls_last para garantir que quem nunca teve chamado fique por último
    equipamentos = equipamentos.order_by(F('ultima_atividade').desc(nulls_last=True))[:10]

    # --- SETORES (Mesma lógica para os avulsos) ---
    setores = setores.annotate(
        ultima_atividade_avulso=Max('chamado__criado_em', filter=Q(chamado__tipo='avulso'))
    )

    if setor_id:
        setores = setores.filter(id=setor_id)
    if status_filtro:
        setores = setores.filter(ultima_atividade_avulso__isnull=False)

    setores = setores.order_by(F('ultima_atividade_avulso').desc(nulls_last=True))[:10]
    
    # --- PREENCHIMENTO PARA O TEMPLATE ---
    for eq in equipamentos:
        qs_chamados = Chamado.objects.filter(equipamento=eq)
        if status_filtro:
            qs_chamados = qs_chamados.filter(status=status_filtro)
        eq.ultimo_chamado = qs_chamados.order_by('-criado_em').first()

    for st in setores:
        qs_avulsos = Chamado.objects.filter(setor_avulso=st, tipo='avulso')
        if status_filtro:
            qs_avulsos = qs_avulsos.filter(status=status_filtro)
        st.ultimo_avulso = qs_avulsos.order_by('-criado_em').first()

    return render(request, 'manutencao/historicos.html', {
        'equipamentos': equipamentos,
        'setores': setores,
        'todos_setores': lista_todos_setores,
        'search_query': q,
        'setor_selecionado': setor_id,
        'status_selecionado': status_filtro,
    })


@login_required
def historico_equipamento(request, equipamento_id):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    equipamento = get_object_or_404(Equipamento, id=equipamento_id)
    chamados = Chamado.objects.filter(equipamento=equipamento).order_by('-criado_em')
    
    return render(request, 'manutencao/historico_equipamento.html', {
        'equipamento': equipamento,
        'chamados': chamados
    })

@login_required
def historico_setor(request, setor_id):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    setor = get_object_or_404(Setor, id=setor_id)
    # Filtra apenas chamados do tipo avulso para este setor
    chamados = Chamado.objects.filter(setor_avulso=setor, tipo='avulso').order_by('-criado_em')
    
    return render(request, 'manutencao/historico_setor.html', {
        'setor': setor,
        'chamados': chamados
    })



@login_required
def criar_chamado(request):

    equip_id_vinda_do_qr = request.GET.get('equip_id')

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
                
            messages.success(request, "Chamado criado com sucesso!")

            if request.user.tipo == 'mecanico_admin':
                return redirect('mecanico_dashboard')
            return redirect('solicitante_dashboard')

        else:
            messages.error(request, "Erro ao criar chamado, Verifique os campos")
    else:
        if equip_id_vinda_do_qr:
            # Busca o equipamento para descobrir o setor dele
            equipamento = Equipamento.objects.filter(id=equip_id_vinda_do_qr).first()
            
            initial_data = {
                'equipamento': equip_id_vinda_do_qr,
                'tipo': 'equipamento'
            }
            
            # Se o equipamento existir e tiver setor, passa o ID do setor também
            if equipamento and equipamento.setor:
                initial_data['setor_avulso'] = equipamento.setor.id # Verifique se o nome no form é este mesmo
            
            form = ChamadoForm(initial=initial_data)
        else:
            # Só cria o form vazio se NÃO for QR Code
            form = ChamadoForm()
    #Deixando os campos mecanicos e setores fora do else pra eles carregarem mesmo se der erro no form    
    mecanicos = Usuario.objects.filter(tipo='mecanico')
    setores = Setor.objects.all()
    equipamentos = Equipamento.objects.all()

    return render(request, 'manutencao/criar_chamado.html', {
        'form': form,
        'mecanicos': mecanicos,
        'setores': setores,
        'equipamentos': equipamentos
    })


@login_required
def atualizar_status(request, chamado_id):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    if request.user.tipo == 'mecanico_admin':
        chamado = get_object_or_404(Chamado, id=chamado_id)
    else:
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
            elif novo_status == 'concluido':
                if not chamado.concluido_em:
                    chamado.concluido_em = timezone.now()
                chamado.concluido_por = request.user
            
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
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SetorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Setor cadastrado com sucesso!')
            return redirect('gerenciar_setores')
    else:
        form = SetorForm()
    
    total_setores = Setor.objects.count()
    setores = Setor.objects.all().select_related('energia').order_by('nome')
    return render(request, 'manutencao/gerenciar_setores.html', {
        'form': form,
        'setores': setores,
        'total_setores': total_setores
    })

def editar_setor(request, pk):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    setor = get_object_or_404(Setor, pk=pk)
    
    if request.method == 'POST':
        form = SetorForm(request.POST, instance=setor)
        if form.is_valid():
            form.save()
            return redirect('gerenciar_setores')
    else:
        form = SetorForm(instance=setor)

    #busca todos os setores para a lista lateral não ficar vazia
    setores = Setor.objects.all().order_by('nome')
    
    return render(request, 'manutencao/gerenciar_setores.html', {
        'form': form,
        'setores': setores,
        'editando': True
    })

@login_required
def gerenciar_equipamentos(request):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EquipamentoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipamento cadastrado com sucesso!')
            return redirect('gerenciar_equipamentos')
    else:
        form = EquipamentoForm()

    # 1. Correção do nome: 'search' (estava 'serach')
    busca = request.GET.get('search', '')

    # 2. Filtragem dos equipamentos
    equipamentos_list = Equipamento.objects.all().order_by('-id') # Adicionei order_by para os novos aparecerem primeiro
    if busca:
        equipamentos_list = equipamentos_list.filter(
            Q(nome__icontains=busca) | 
            Q(codigo__icontains=busca) |
            Q(energia__numero__icontains=busca)
        )
    
    # 3. Paginação
    paginator = Paginator(equipamentos_list, 10)
    page_number = request.GET.get('page')
    equipamentos = paginator.get_page(page_number)

    # 4. Contador inteligente (mostra o total filtrado)
    total_equipamentos = equipamentos_list.count()
    
    return render(request, 'manutencao/gerenciar_equipamentos.html', {
        'form': form,
        'equipamentos': equipamentos,
        'total_equipamentos': total_equipamentos,
        'busca': busca 
    })

@login_required
def editar_equipamento(request, pk):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    equipamento = get_object_or_404(Equipamento, pk=pk)
    imagem_antiga = equipamento.imagem # Guarda a referência antes de mudar
    
    if request.method == 'POST':
        form = EquipamentoForm(request.POST, request.FILES, instance=equipamento)
        if form.is_valid():
            # Se enviaram uma imagem nova E já existia uma antiga
            if 'imagem' in request.FILES and imagem_antiga:
                if os.path.exists(imagem_antiga.path):
                    os.remove(imagem_antiga.path)
            
            form.save()
            return redirect('gerenciar_equipamentos')
    else:
        form = EquipamentoForm(instance=equipamento)

    busca = request.GET.get('search', '')
    
    equipamentos_list = Equipamento.objects.all().order_by('-id')
    if busca:
        equipamentos_list = equipamentos_list.filter(
            Q(nome__icontains=busca) | 
            Q(codigo__icontains=busca) |
            Q(energia__numero__icontains=busca)
        )

    paginator = Paginator(equipamentos_list, 10)
    page_number = request.GET.get('page')
    equipamentos_paginados = paginator.get_page(page_number)
    
    return render(request, 'manutencao/gerenciar_equipamentos.html', {
        'form': form,
        'equipamentos': equipamentos_paginados,
        'total_equipamentos': equipamentos_list.count(),
        'busca': busca,
        'editando': True # Variável para mudar os textos no HTML
    })

@login_required
def gerenciar_energia(request):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    if request.method == 'POST':
        numero = request.POST.get('numero')
        if numero:
            Energia.objects.get_or_create(numero=numero)
            messages.success(request, "Número de energia cadastrado!")
            return redirect('gerenciar_energia')

    energias = Energia.objects.all().order_by('numero')
    return render(request, 'manutencao/gerenciar_energia.html', {'energias': energias})

@login_required
def get_equipamentos_por_setor(request, setor_id):
    equipamentos = Equipamento.objects.filter(setor_id=setor_id).values('id', 'nome','codigo', 'imagem')
    # Converter caminho da imagem para URL completa
    for eq in equipamentos:
        if eq['imagem']:
            eq['imagem'] = request.build_absolute_uri('/media/' + eq['imagem'])
    return JsonResponse(list(equipamentos), safe=False)

@login_required
def api_detalhes_equipamento(request, pk):
    if not request.user.is_manutencao:
        return JsonResponse({'error': 'Acesso negado. Permissão insuficiente.'}, status=403)
    
    equip = get_object_or_404(Equipamento, pk=pk)
    return JsonResponse({
        'id': equip.id,
        'nome': equip.nome,
        'setor_id': equip.setor.id if equip.setor else None,
        'imagem_url': equip.imagem.url if equip.imagem else None,
        'codigo': equip.codigo
    })

@login_required
def painel_qr_equipamento(request, pk):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    
    equipamento = get_object_or_404(Equipamento, pk=pk)
    return render(request, 'manutencao/painel_qr.html', {'equipamento': equipamento})

@login_required
def gerador_etiquetas(request):
    if not request.user.is_manutencao:
        return redirect('dashboard')
    # pega o parametro setorr da URL (se n vier nada, traz None)
    setor_filtrado = request.GET.get('setor')
    
    # inicia a query
    equipamentos = Equipamento.objects.all()
    
    # se o usuario escolheu um setor, filtra os resultados
    if setor_filtrado:
        equipamentos = equipamentos.filter(setor=setor_filtrado)
    
    # pegam todos os setores únicos para preencher o select no HTML

    # .values_list('setor', flat=True) traz uma lista simples de nomes
    setores = Equipamento.objects.values('setor__id', 'setor__nome').distinct().order_by('setor__nome')

    host = request.get_host() 
    for eq in equipamentos:
        eq.link_qr = f"http://{host}/painel-qr/{eq.id}/"
        
    context = {
        'equipamentos': equipamentos,
        'setores': setores,
        'setor_selecionado': setor_filtrado
    }
        
    return render(request, 'manutencao/gerador_etiquetas.html', context)
