import os
import json
import uuid
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from celery import Celery
import paho.mqtt.publish as publish

# Import de ta configuration centralisée
from common.config import AppConfig

# ==========================================
# CONFIGURATION MÉTIER
# ==========================================
SIM_SPEED = float(os.getenv("SIM_SPEED", 1.0))
DEVICE_ID = "mock_node2_wet"  # Identifiant du node cible

# Cibles (Hardcodées pour le MVP, idéalement lues en BDD plus tard)
TARGET_PH = 6.0
TARGET_EC = 1.4

# Paramètres de la boucle
MIXING_DELAY_REAL_SEC = 60.0
MIXING_DELAY_SEC = MIXING_DELAY_REAL_SEC / SIM_SPEED
BASE_PULSE_MS = 1000

# Configuration Celery (Redis reste notre broker pour les tâches)
app = Celery('hydro_brain', broker=AppConfig.REDIS_URL)

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================
def get_db_connection():
    return psycopg2.connect(
        host=AppConfig.DB_HOST,
        database=AppConfig.DB_NAME,
        user=AppConfig.DB_USER,
        password=AppConfig.DB_PASS
    )

def send_mqtt_command(target_pump, duration_ms):
    """Pousse la commande directement sur le broker MQTT"""
    cmd_id = str(uuid.uuid4())
    payload = {
        "action": "PULSE",
        "cmd_id": cmd_id,
        "target": target_pump,
        "duration_ms": duration_ms
    }

    # On extrait l'ID du noeud pour construire le bon topic MQTT (ex: mock_node2_wet -> node2)
    try:
        node_id = DEVICE_ID.split('_')[1]
    except IndexError:
        node_id = DEVICE_ID

    topic = f"hydro/{node_id}/commands"
    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")

    try:
        # publish.single ouvre, publie et ferme la connexion MQTT d'un coup
        publish.single(
            topic,
            payload=json.dumps(payload),
            hostname=broker_host,
            port=1883
        )
        print(f"🚀 ORDRE MQTT ENVOYÉ : {target_pump} ({duration_ms}ms) sur le topic '{topic}'")
    except Exception as e:
        print(f"❌ Échec de l'envoi MQTT : {e}")


# ==========================================
# LA TÂCHE PRINCIPALE (SÉQUENCEUR)
# ==========================================
@app.task(name="evaluate_and_control")
def evaluate_and_control():
    print(f"🧠 Démarrage évaluation pour {DEVICE_ID} (SIM_SPEED={SIM_SPEED})")
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. VERROU : VÉRIFICATION DU DÉLAI DE MÉLANGE
        cursor.execute("""
            SELECT time, actuator_id, action 
            FROM actuator_logs 
            WHERE action = 'COMPLETED'
            ORDER BY time DESC LIMIT 1
        """)
        last_action = cursor.fetchone()

        if last_action:
            now_utc = datetime.now(timezone.utc)
            elapsed_sec = (now_utc - last_action["time"]).total_seconds()

            if elapsed_sec < MIXING_DELAY_SEC:
                print(f"⏳ MÉLANGE : Action il y a {elapsed_sec:.1f}s. Attente de {MIXING_DELAY_SEC:.1f}s.")
                return "WAITING"

        # 2. LECTURE DE LA TÉLÉMÉTRIE (Moyenne lissée)
        lookback_sec = max(10, 120 / SIM_SPEED)
        cursor.execute(f"""
            SELECT metric, AVG(value) as avg_val 
            FROM telemetry 
            WHERE device_id = %s AND time >= NOW() - INTERVAL '{lookback_sec} seconds'
            GROUP BY metric
        """, (DEVICE_ID,))

        metrics = {row["metric"]: row["avg_val"] for row in cursor.fetchall() if row["avg_val"] is not None}

        if "ph" not in metrics or "ec" not in metrics:
            print("⚠️ Pas assez de données pour prendre une décision.")
            return "NO_DATA"

        current_ph = metrics["ph"]
        current_ec = metrics["ec"]
        last_pump = last_action["actuator_id"] if last_action else None

        print(f"📊 ÉTAT : pH={current_ph:.2f} (Cible: {TARGET_PH}) | EC={current_ec:.2f} (Cible: {TARGET_EC})")

        # 3. LOGIQUE DE DÉCISION
        if current_ec > (TARGET_EC + 0.3) or current_ph < 4.5 or current_ph > 8.0:
            print("🚨 SÉCURITÉ : Valeurs critiques. Arrêt.")
            return "EMERGENCY_STOP"

        if (TARGET_EC - current_ec) > 0.05:
            if last_pump != "pump_nutri_1":
                send_mqtt_command("pump_nutri_1", BASE_PULSE_MS)
                return "DOSE_NUTRI_A"
            else:
                send_mqtt_command("pump_nutri_2", BASE_PULSE_MS)
                return "DOSE_NUTRI_B"

        if abs(current_ph - TARGET_PH) > 0.15:
            if current_ph > TARGET_PH:
                send_mqtt_command("pump_ph_minus", BASE_PULSE_MS)
                return "DOSE_PH_MINUS"
            else:
                send_mqtt_command("pump_ph_plus", BASE_PULSE_MS)
                return "DOSE_PH_PLUS"

        print("✅ STABLE. Aucune action.")
        return "STABLE"

    except Exception as e:
        print(f"❌ Erreur worker : {str(e)}")
        raise e
    finally:
        cursor.close()
        conn.close()


# Scheduler
app.conf.beat_schedule = {
    'run-control-loop-frequently': {
        'task': 'evaluate_and_control',
        'schedule': max(1.0, 60.0 / SIM_SPEED),
    },
}