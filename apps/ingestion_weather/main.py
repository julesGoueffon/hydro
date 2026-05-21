import json
import time
import requests
from confluent_kafka import Producer

from common.config import AppConfig

# Utilisation

conf = {
    'bootstrap.servers': AppConfig.KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'weather-ingestor'
}

producer = Producer(conf)


def delivery_report(err, msg):
    """ Callback appelé une fois que le message est bien arrivé dans Redpanda """
    if err is not None:
        print(f"❌ Erreur d'envoi : {err}")
    else:
        print(f"✅ Message envoyé au topic {msg.topic()} [Partition: {msg.partition()}]")


def fetch_weather():
    """ Récupère la météo en temps réel pour Auxerre """
    # Coordonnées GPS d'Auxerre
    lat, lon = 47.79, 3.57
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Crash si l'API est down
        data = response.json()
        return data['current_weather']
    except Exception as e:
        print(f"⚠️ Erreur lors de l'appel API : {e}")
        return None


if __name__ == "__main__":
    print("🚀 Démarrage de l'ingestion météo (Ctrl+C pour arrêter)...")

    try:
        while True:
            weather = fetch_weather()

            if weather:
                # On enrichit la donnée avec un nom de capteur "virtuel"
                weather['sensor_name'] = "auxerre_outdoor_station"

                # Conversion en JSON et envoi
                payload = json.dumps(weather).encode('utf-8')
                producer.produce(
                    topic='weather_raw',
                    value=payload,
                    callback=delivery_report
                )

                # 'flush' force l'envoi immédiat
                producer.flush()
                print(f"📡 Donnée produite : {weather}")

            # On attend 1 minute avant le prochain relevé
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Arrêt du script.")