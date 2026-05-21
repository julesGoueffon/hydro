
from celery import Celery

from common.config import AppConfig

# Configuration Celery
app = Celery('hydro_brain', broker=AppConfig.REDIS_URL)


# Configurez les tâches ici ou utilisez 'include' pour charger vos fichiers de tâches
app.conf.update(
    include=['apps.celery_brain.regulation_wet'], # Importe vos fichiers de tâches
    beat_schedule={
        'run-control-loop-frequently': {
            'task': 'evaluate_and_control', # Doit correspondre au nom de la tâche
            'schedule': 5.0, # Fréquence en secondes
        },
        # Vous pouvez ajouter d'autres tâches ici facilement
        # 'ma-deuxieme-tache': {
        #     'task': 'mon_autre_module.ma_tache',
        #     'schedule': 60.0,
        # },
    },
)