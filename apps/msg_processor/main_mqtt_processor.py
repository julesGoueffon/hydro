import json
import time
import psycopg2
from psycopg2 import pool
import paho.mqtt.client as mqtt
from common.config import AppConfig

from contextlib import contextmanager

@contextmanager
def acquire_conn(pool):
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)

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


def handle_actuator(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))

        # Le context manager s'occupe du getconn et du putconn automatiquement
        with acquire_conn(db_pool) as conn:
            with conn.cursor() as cursor:
                query = """
                        INSERT INTO actuator_logs (actuator_id, status, duration_ms, triggered_by)
                        VALUES (%s, %s, %s, %s) \
                        """
                cursor.execute(query, (
                    data.get("target"),
                    data.get("status"),
                    data.get("duration_ms"),
                    "auto_backend"
                ))
                conn.commit()

        print(f"⚙️ [Actionneur] {data.get('target')} | {data.get('status')}")
    except Exception as e:
        print(f"❌ Erreur Actionneur : {e}")


def handle_telemetry(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        device_id = data.get("device_id", "unknown")

        raw_ph = data.get("ph")
        raw_ec = data.get("ec")

        # Récupération des connexions via le pool sécurisé
        with acquire_conn(db_pool) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # 1. Lecture des coefficients de calibration du pH
                cursor.execute("""
                               SELECT slope, intercept
                               FROM sensor_calibrations
                               WHERE sensor_id = %s
                               """, (f"{device_id}_ph",))
                cal_ph = cursor.fetchone() or {"slope": 1.0, "intercept": 0.0}

                # 2. Lecture des coefficients de calibration de l'EC
                cursor.execute("""
                               SELECT slope, intercept
                               FROM sensor_calibrations
                               WHERE sensor_id = %s
                               """, (f"{device_id}_ec",))
                cal_ec = cursor.fetchone() or {"slope": 1.0, "intercept": 0.0}

                # 3. Application de la formule mathématique linéaire : (Brut * Pente) + Décalage
                calibrated_ph = (raw_ph * cal_ph["slope"]) + cal_ph["intercept"] if raw_ph is not None else None
                calibrated_ec = (raw_ec * cal_ec["slope"]) + cal_ec["intercept"] if raw_ec is not None else None

                # 4. Enregistrement de la donnée propre dans TimescaleDB
                query = """
                        INSERT INTO telemetry_metrics (timestamp, device_id, ph, ec, water_temp, air_temp, humidity)
                        VALUES (NOW(), %s, %s, %s, %s, %s, %s) \
                        """
                cursor.execute(query, (
                    device_id,
                    calibrated_ph,
                    calibrated_ec,
                    data.get("water_temp"),
                    data.get("air_temp"),
                    data.get("humidity")
                ))
                conn.commit()

        print(
            f"📈 [Télémétrie] {device_id} | pH corrigé: {calibrated_ph:.2f} (brut: {raw_ph}) | EC corrigée: {calibrated_ec:.2f}")
    except Exception as e:
        print(f"❌ Erreur lors du traitement de la télémétrie : {e}")

# --- 3. DÉMARRAGE BLOQUANT ---
def start_worker():
    # Initialisation robuste pour supporter Paho-MQTT v1 et v2
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    client.message_callback_add("hydro/+/weather", handle_weather)
    client.message_callback_add("hydro/+/telemetry", handle_telemetry)
    client.message_callback_add("hydro/+/acks", handle_actuator)

    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")

    while True:
        try:
            client.connect(broker_host, 1883, 60)
            break
        except ConnectionRefusedError:
            print("⏳ Attente du broker MQTT...")
            time.sleep(2)

    # Le '+' permet d'écouter tous les devices
    client.subscribe("hydro/+/weather")
    client.subscribe("hydro/+/telemetry")
    client.subscribe("hydro/+/acks")

    print("📡 Worker MQTT prêt et en écoute (Boucle infinie)...")
    client.loop_forever()

if __name__ == "__main__":
    start_worker()