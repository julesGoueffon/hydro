import json
import time
import psycopg2
from psycopg2 import pool
import paho.mqtt.client as mqtt
from common.config import AppConfig

print("🔧 Démarrage du Worker MQTT (Processus Indépendant)...")

# --- 1. POOL DE CONNEXIONS BDD ---
while True:
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 5,
            host=AppConfig.DB_HOST,
            database=AppConfig.DB_NAME,
            user=AppConfig.DB_USER,
            password=AppConfig.DB_PASS
        )
        print("✅ Connecté à PostgreSQL.")
        break
    except Exception as e:
        print(f"⏳ Base de données injoignable, nouvelle tentative dans 3s... ({e})")
        time.sleep(3)


# --- 2. CALLBACKS ---

def handle_weather(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        conn = db_pool.getconn()
        cursor = conn.cursor()

        query = """
            INSERT INTO weather_metrics (temperature, windspeed, weathercode, time, sensor_name)
            VALUES (%s, %s, %s, CAST(%s AS TIMESTAMP), %s)
        """
        cursor.execute(query, (
            float(data.get("temperature", 0.0)),
            float(data.get("windspeed", 0.0)),
            int(data.get("weathercode", 0)),
            data.get("time"),
            data.get("sensor_name", "unknown")
        ))
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        print(f"🌤️ [Météo] Insérée : {data.get('temperature')}°C")
    except Exception as e:
        print(f"❌ Erreur Météo : {e}")
        if 'conn' in locals(): db_pool.putconn(conn)


def handle_telemetry(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        conn = db_pool.getconn()
        cursor = conn.cursor()

        query = """
            INSERT INTO telemetry (time, device_id, metric, value)
            VALUES (NOW(), %s, %s, %s)
        """
        cursor.execute(query, (data.get("device_id"), data.get("metric"), float(data.get("value", 0.0))))
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        print(f"📥 [Télémétrie] {data.get('device_id')} | {data.get('metric')}")
    except Exception as e:
        print(f"❌ Erreur Télémétrie : {e}")
        if 'conn' in locals(): db_pool.putconn(conn)


def handle_actuator(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        conn = db_pool.getconn()
        cursor = conn.cursor()

        query = """
            INSERT INTO actuator_logs (time, actuator_id, action, duration_ms, trigger_source)
            VALUES (NOW(), %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.get("actuator"), data.get("status"),
            data.get("actual_duration_ms"), "auto_backend"
        ))
        conn.commit()
        cursor.close()
        db_pool.putconn(conn)
        print(f"⚙️ [Actionneur] {data.get('actuator')} | {data.get('status')}")
    except Exception as e:
        print(f"❌ Erreur Actionneur : {e}")
        if 'conn' in locals(): db_pool.putconn(conn)


# --- 3. DÉMARRAGE BLOQUANT ---
def start_worker():
    client = mqtt.Client()

    client.message_callback_add("weather_raw", handle_weather)
    client.message_callback_add("telemetry_stream", handle_telemetry)
    client.message_callback_add("actuator_stream", handle_actuator)

    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")

    while True:
        try:
            client.connect(broker_host, 1883, 60)
            break
        except ConnectionRefusedError:
            print("⏳ Attente du broker MQTT...")
            time.sleep(2)

    client.subscribe("weather_raw")
    client.subscribe("telemetry_stream")
    client.subscribe("actuator_stream")

    print("📡 Worker MQTT prêt et en écoute (Boucle infinie)...")
    client.loop_forever()  # <-- Bloque le script ici et écoute indéfiniment


if __name__ == "__main__":
    start_worker()