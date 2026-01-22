# ==================== URLS.PY ====================
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('solicitante/', views.solicitante_dashboard, name='solicitante_dashboard'),
    path('mecanico/', views.mecanico_dashboard, name='mecanico_dashboard'),
    path('chamado/criar/', views.criar_chamado, name='criar_chamado'),
    path('chamado/<int:chamado_id>/status/', views.atualizar_status, name='atualizar_status'),
    path('setores/', views.gerenciar_setores, name='gerenciar_setores'),
    path('equipamentos/', views.gerenciar_equipamentos, name='gerenciar_equipamentos'),
    path('api/equipamentos/setor/<int:setor_id>/', views.get_equipamentos_por_setor, name='get_equipamentos_por_setor'),
    path('historicos/', views.historicos, name='historicos'),
    path('historicos/equipamento/<int:equipamento_id>/', views.historico_equipamento, name='historico_equipamento'),
    path('historicos/setor/<int:setor_id>/', views.historico_setor, name='historico_setor'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)