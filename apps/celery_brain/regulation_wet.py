import os
import json
import uuid
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor

from apps.celery_brain.common import get_kafka_producer, delivery_report, get_db_connection, app
# Import de ta configuration centralisée
from common.config import AppConfig

# ==========================================
# CONFIGURATION MÉTIER
# ==========================================
SIM_SPEED = float(os.getenv("SIM_SPEED", 1.0))

print(f"Vitesse d'execution : x{SIM_SPEED}")
DEVICE_ID = "mock_node2_wet"  # Identifiant du node cible[cite: 2]

# Cibles (Hardcodées pour le MVP)
TARGET_PH = 6.0
TARGET_EC = 1.4

# Paramètres de la boucle
MIXING_DELAY_REAL_SEC = 60.0
MIXING_DELAY_SEC = MIXING_DELAY_REAL_SEC / SIM_SPEED
BASE_PULSE_MS = 1000


# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def send_kafka_command(target_pump, duration_ms):
    """Pousse la commande dans Kafka avec confluent-kafka"""
    cmd_id = str(uuid.uuid4())
    payload = {
        "action": "PULSE",
        "cmd_id": cmd_id,
        "target": target_pump,
        "duration_ms": duration_ms,
        "device_id": "mock_node2_wet"
    }

    print(f"Préparation payload: {payload}")
    payload_bytes = json.dumps(payload).encode('utf-8')

    # On récupère le producer du worker actuel
    prod = get_kafka_producer()

    prod.produce(
        topic="command_stream",
        value=payload_bytes,
        callback=delivery_report
    )
    print("produced")

    # On force l'envoi avec un timeout de sécurité (très important !)
    messages_restants = prod.flush(timeout=5.0)

    if messages_restants > 0:
        print(f"⚠️ ERREUR : {messages_restants} messages bloqués. Kafka (Redpanda) est injoignable !")
    else:
        print("flush OK")

    print(f"🚀 ORDRE PRÉPARÉ : {target_pump} pendant {duration_ms}ms (Cmd ID: {cmd_id})")
    
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

        metrics = {row["metric"]: row["avg_val"] for row in cursor.fetchall()}

        if "ph" not in metrics or "ec" not in metrics:
            print("⚠️ Pas assez de données pour prendre une décision.")
            return "NO_DATA"

        current_ph = metrics["ph"]
        current_ec = metrics["ec"]
        last_pump = last_action["actuator_id"] if last_action else None

        print(f"📊 ÉTAT : pH={current_ph:.2f} (Cible: {TARGET_PH}) | EC={current_ec:.2f} (Cible: {TARGET_EC})")

        # 3. LOGIQUE DE DÉCISION
        if SIM_SPEED<1.1 and ( current_ec > (TARGET_EC + 0.3) or current_ph < 4.5 or current_ph > 8.0):
            print("🚨 SÉCURITÉ : Valeurs critiques. ##Arrêt.")
            #return "EMERGENCY_STOP"
        print(f"(TARGET_EC - current_ec) > 0.05 : {(TARGET_EC - current_ec)}" )

        if (TARGET_EC - current_ec) > 0.05:
            print("ici")
            if last_pump != "pump_nutri_1":
                print("iciA")

                send_kafka_command("pump_nutri_1", BASE_PULSE_MS)
                return "DOSE_NUTRI_A"
            else:
                print("iciB")

                send_kafka_command("pump_nutri_2", BASE_PULSE_MS)
                return "DOSE_NUTRI_B"
        print(f"abs(current_ph - TARGET_PH) > 0.15 { abs(current_ph - TARGET_PH)}")

        if abs(current_ph - TARGET_PH) > 0.15:
            if current_ph > TARGET_PH:
                print("iciC")

                send_kafka_command("pump_ph_minus", BASE_PULSE_MS)
                return "DOSE_PH_MINUS"
            else:
                print("iciD")

                send_kafka_command("pump_ph_plus", BASE_PULSE_MS)
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