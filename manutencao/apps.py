from django.apps import AppConfig
import sys


class ManutencaoConfig(AppConfig):
    name = 'manutencao'

    def ready(self):
        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'shell']):
            return
        self._registrar_schedule_rotinas()

    def _registrar_schedule_rotinas(self):
        try:
            from django_celery_beat.models import PeriodicTask, CrontabSchedule
            import json

            # Roda todo dia às 06:00 (horário de Brasília)
            schedule, _ = CrontabSchedule.objects.get_or_create(
                hour=6, minute=0,
                timezone='America/Sao_Paulo'
            )
            PeriodicTask.objects.get_or_create(
                name='Verificar Rotinas de Manutenção',
                defaults={
                    'crontab': schedule,
                    'task': 'manutencao.tasks.verificar_rotinas',
                    'args': json.dumps([]),
                }
            )
        except Exception:
            pass  # Ignora se o banco ainda não existir (primeiro migrate)
