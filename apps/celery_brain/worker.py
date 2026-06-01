
from celery import Celery

from common.config import AppConfig

# Configuration Celery
app = Celery('hydro_brain', broker=AppConfig.REDIS_URL)


# Configurez les tâches ici ou utilisez 'include' pour charger vos fichiers de tâches
app.conf.update(
    include=['apps.celery_brain.regulation_wet','apps.celery_brain.meteo'], # Importe vos fichiers de tâches
    beat_schedule={
        'run-control-loop-frequently': {
            'task': 'evaluate_and_control', # Doit correspondre au nom de la tâche
            'schedule': 3.0, # Fréquence en secondes
        },
        'fetch-weather-auxerre': {
            'task': 'fetch_and_save_weather',  # Le nom défini dans le @app.task
            'schedule': 10.0,  # Toutes les 5 minutes (300 secondes) pour éviter de spammer l'API météo
        },

    },
)