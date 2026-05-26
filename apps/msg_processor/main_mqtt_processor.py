import json
import time
import psycopg2
import psycopg2.extras
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
        payload = json.loads(msg.payload.decode('utf-8'))

        with acquire_conn(db_pool) as conn:
            with conn.cursor() as cursor:
                # On ajoute la colonne status à la requête
                query = """
                        INSERT INTO actuator_logs (time, actuator_id, action, status, duration_ms, trigger_source)
                        VALUES (NOW(), %s, %s, %s, %s, %s)
                        """
                cursor.execute(query, (
                    payload.get("actuator_id"),
                    payload.get("action", "PULSE"),
                    payload.get("status", "UNKNOWN"), # STARTED ou COMPLETED
                    payload.get("duration_ms", 0),
                    "edge_device"
                ))
                conn.commit()

        print(f"✅ [Actionneur] Événement {payload.get('status')} pour {payload.get('actuator_id')} historisé !")
    except Exception as e:
        print(f"❌ Erreur SQL Actionneur : {e}")


def handle_telemetry(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        device_id = data.get("device_id", "unknown")
        metric = data.get("metric")
        raw_value = data.get("value")

        if not metric or raw_value is None:
            return

        with acquire_conn(db_pool) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:

                # 1. Vérifier le mode actuel du système
                cursor.execute("SELECT system_mode FROM system_config WHERE id = 1")
                config_row = cursor.fetchone()
                system_mode = config_row["system_mode"] if config_row else "AUTO"

                final_value = float(raw_value)

                # --- TRAITEMENT SPÉCIFIQUE : SONDES ANALOGIQUES (pH / EC) ---
                if metric in ["ph", "ec"]:

                    # A. Sécurité absolue : on stocke TOUJOURS la tension brute
                    cursor.execute("""
                                   INSERT INTO telemetry (time, device_id, metric, value)
                                   VALUES (NOW(), %s, %s, %s)
                                   """, (device_id, f"{metric}_raw", final_value))

                    # B. Si on est en maintenance (Calibration en cours)
                    if system_mode == "MAINTENANCE":
                        # On stocke sous un nom spécifique pour l'écran de calibration du front
                        cursor.execute("""
                                       INSERT INTO telemetry (time, device_id, metric, value)
                                       VALUES (NOW(), %s, %s, %s)
                                       """, (device_id, f"{metric}_calibration", final_value))
                        conn.commit()
                        print(f"🔧 [Calibration] {device_id} | Tension {metric}: {final_value:.2f}")
                        return  # FIN DU TRAITEMENT : On ne pollue pas la métrique principale

                    # C. Si on est en mode normal, on applique l'équation de droite
                    cursor.execute("""
                                   SELECT slope, intercept
                                   FROM sensor_calibrations
                                   WHERE sensor_id = %s
                                   """, (f"{device_id}_{metric}",))
                    cal = cursor.fetchone() or {"slope": 1.0, "intercept": 0.0}

                    # Calcul de la valeur finale calibrée
                    final_value = (final_value * cal["slope"]) + cal["intercept"]

                # --- INSERTION CLASSIQUE ---
                # (S'applique aux températures directes, ou au pH/EC fraîchement calculés)
                cursor.execute("""
                               INSERT INTO telemetry (time, device_id, metric, value)
                               VALUES (NOW(), %s, %s, %s)
                               """, (device_id, metric, final_value))

                conn.commit()

        print(f"📈 [Télémétrie] {device_id} | {metric}: {final_value:.2f}")

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
    client.message_callback_add("hydro/+/actuators", handle_actuator)

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
    client.subscribe("hydro/+/actuators")

    print("📡 Worker MQTT prêt et en écoute (Boucle infinie)...")
    client.loop_forever()

if __name__ == "__main__":
    start_worker()