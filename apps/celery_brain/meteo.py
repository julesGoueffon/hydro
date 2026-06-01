import requests
import logging
from datetime import datetime
from apps.celery_brain.worker import app
from apps.celery_brain.common import get_db_connection

logger = logging.getLogger(__name__)


@app.task(name='fetch_and_save_weather')
def fetch_and_save_weather():
    """
    Récupère la météo d'Auxerre et insère directement en base de données.
    """
    lat, lon = 47.79, 3.57
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        weather = data['current_weather']

        # Préparation des données avec un device_id explicite
        metric = "air_temp_source_meteo"
        value = weather['temperature']
        device_id = "auxerre_outdoor_station"  # Identifiant pour satisfaire la contrainte BDD
        timestamp = datetime.now()

        # Insertion corrigée incluant device_id
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
                    INSERT INTO telemetry (metric, value, time, device_id)
                    VALUES (%s, %s, %s, %s)
                    """, (metric, value, timestamp, device_id))
        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Météo insérée en BDD : {value}°C")

    except Exception as e:
        logger.error(f"⚠️ Erreur lors de l'ingestion météo : {e}")