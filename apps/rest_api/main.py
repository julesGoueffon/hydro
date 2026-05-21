import time
import io
import json

import psycopg2
from psycopg2.extras import RealDictCursor
import paho.mqtt.publish as publish
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from minio import Minio
from datetime import timedelta

from apps.rest_api.image_processor import process_and_save_image_from_minio
from common.config import AppConfig

print("🚀 Démarrage de l'API HydroStack...")

app = FastAPI(title="HydroStack API")

# --- 0. CONFIGURATION CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. CLIENT MINIO ---
minio_client = Minio(
    AppConfig.MINIO_ENDPOINT,
    access_key=AppConfig.MINIO_ACCESS_KEY,
    secret_key=AppConfig.MINIO_SECRET_KEY,
    secure=False
)


BUCKET_NAME = AppConfig.MINIO_BUCKET_NAME
try:
    if not minio_client.bucket_exists(BUCKET_NAME):
        minio_client.make_bucket(BUCKET_NAME)
        print(f"📁 Bucket MinIO '{BUCKET_NAME}' créé avec succès.")
except Exception as e:
    print(f"⚠️ Attention, MinIO n'est pas joignable : {e}")


# --- 2. UTILITAIRES BDD ---
def get_db_connection():
    return psycopg2.connect(
        host=AppConfig.DB_HOST,
        database=AppConfig.DB_NAME,
        user=AppConfig.DB_USER,
        password=AppConfig.DB_PASS
    )


# --- 3. SCHÉMAS PYDANTIC ---
class ConfigUpdate(BaseModel):
    system_mode: str
    target_ph: float
    target_ec: float


class CommandOverride(BaseModel):
    target: str       # ex: "pump_ph_minus"
    duration_ms: int  # ex: 2000
    device_id: str    # ex: "node2"

class CalibrationData(BaseModel):
    device_id: str
    expected_value: float  # Ex: 7.0 pour la solution tampon pH
    metric_type: str       # 'ph' ou 'ec'


# =====================================================================
# ROUTES INGESTION (Capteurs -> Serveur)
# =====================================================================

@app.post("/api/v1/camera/upload")
async def upload_image(request: Request, background_tasks: BackgroundTasks):
    """Route appelée par l'ESP32-CAM pour déposer le JPEG."""
    image_data = await request.body()
    timestamp = int(time.time())
    device_id = request.headers.get("X-Device-ID", "esp32_cam_inconnu")
    object_name = f"{device_id}_{timestamp}.jpg"

    try:
        minio_client.put_object(
            BUCKET_NAME, object_name,
            data=io.BytesIO(image_data),
            length=len(image_data),
            content_type="image/jpeg"
        )
    except Exception as e:
        return {"status": "error", "message": f"Erreur MinIO: {e}"}

    # Inscription en BDD
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO image_metrics (sensor_name, "timestamp", image_path, blur_score) VALUES (%s, %s, %s, %s)',
        (device_id, timestamp, object_name, 100.0)
    )
    conn.commit()
    cur.close()
    conn.close()

    background_tasks.add_task(
        process_and_save_image_from_minio,
        device_id, timestamp, object_name
    )

    return {"status": "success", "message": "Image stockée et traitement lancé", "path": object_name}


# =====================================================================
# ROUTES FRONTEND (Serveur <-> React)
# =====================================================================

# --- A. SUPERVISION ---

@app.get("/api/telemetry")
def get_telemetry(hours: int = 24):
    """Renvoie l'historique pour les graphiques Recharts."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT time, metric, value
            FROM telemetry
            WHERE time >= NOW() - INTERVAL '%s hours'
            ORDER BY time ASC
        """, (hours,))
        data = cursor.fetchall()
        return {"status": "success", "data": data}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/status/live")
def get_live_status():
    """Renvoie les toutes dernières valeurs de chaque métrique pour les jauges."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT DISTINCT ON (metric) metric, value, time
            FROM telemetry
            ORDER BY metric, time DESC
        """)
        data = cursor.fetchall()
        status = {row["metric"]: {"value": row["value"], "time": row["time"]} for row in data}
        return {"status": "success", "data": status}
    finally:
        cursor.close()
        conn.close()

from fastapi.responses import StreamingResponse

@app.get("/api/camera/latest")
def get_latest_camera():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT image_path, blur_score, timestamp
            FROM image_metrics
            ORDER BY timestamp DESC LIMIT 1
        """)
        img_data = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not img_data:
        return {"status": "empty", "url": None}

    # FastAPI télécharge depuis MinIO et renvoie directement les bytes
    response = minio_client.get_object(BUCKET_NAME, img_data["image_path"])
    return StreamingResponse(
        response,
        media_type="image/jpeg",
        headers={"X-Blur-Score": str(img_data["blur_score"])}
    )

# --- B. PARAMÉTRAGE ---

@app.get("/api/config")
def get_config():
    """Lit les consignes actuelles de la serre."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT mode_auto, target_ph, target_ec FROM system_config WHERE id = 1")
        config = cursor.fetchone()
        return {"status": "success", "data": config}
    finally:
        cursor.close()
        conn.close()


@app.post("/api/config")
def update_config(config: ConfigUpdate):
    """Met à jour les consignes de régulation et historise le changement."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Mise à jour de la config active
        cursor.execute("""
                       UPDATE system_config
                       SET system_mode = %s,
                           target_ph   = %s,
                           target_ec   = %s,
                           updated_at  = NOW()
                       WHERE id = 1
                       """, (config.system_mode, config.target_ph, config.target_ec))

        # 2. Historisation pour le ML
        cursor.execute("""
                       INSERT INTO config_history (target_ph, target_ec, system_mode, changed_by)
                       VALUES (%s, %s, %s, 'api_user')
                       """, (config.target_ph, config.target_ec, config.system_mode))

        conn.commit()
        return {"status": "success", "message": "Configuration mise à jour et historisée"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# --- C. CONTRÔLE-COMMANDE ---

@app.post("/api/command/override")
def trigger_manual_override(cmd: CommandOverride):
    """Déclenche l'activation manuelle, SAUF si le système est en maintenance."""

    # 1. Le Vigile : Vérification du mode système
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT system_mode FROM system_config WHERE id = 1")
        config = cursor.fetchone()

        if config and config["system_mode"] == "MAINTENANCE":
            raise HTTPException(
                status_code=403,
                detail="Intervention physique en cours : Les commandes manuelles sont verrouillées."
            )
    finally:
        cursor.close()
        conn.close()

    # 2. L'envoi de l'ordre (si on n'est pas en maintenance)
    payload = {
        "action": "PULSE",
        "cmd_id": f"manual_api_{int(time.time())}",
        "target": cmd.target,
        "duration_ms": cmd.duration_ms,
        "device_id": cmd.device_id  # Assurez-vous que device_id est bien dans votre modèle CommandOverride
    }
    topic = f"hydro/{cmd.device_id}/commands"
    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")
    publish.single(topic, payload=json.dumps(payload), hostname=broker_host)

    return {"status": "success", "message": f"Ordre envoyé à {cmd.target}"}


# --- D. ENDPOINTS POUR LE FRONTEND (IHM) ---

@app.get("/api/telemetry/live")
def get_live_status():
    """Fournit les dernières métriques en temps réel au tableau de bord."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Récupère la ligne la plus récente de la table de télémétrie
        cursor.execute("""
                       SELECT ph, ec, water_temp, air_temp, humidity
                       FROM telemetry_metrics
                       ORDER BY timestamp DESC
                           LIMIT 1
                       """)
        result = cursor.fetchone()
        # Fallback pour éviter que le front ne crash si la BDD est vide au démarrage
        return result or {"ph": 0.0, "ec": 0.0, "water_temp": 0.0, "air_temp": 0.0, "humidity": 0.0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/api/telemetry/history")
def get_telemetry_history(hours: int = 24):
    """Retourne l'historique des métriques pour les graphiques (Recharts)."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # Récupère l'historique sur X heures (compatible TimescaleDB / Postgres standard)
        cursor.execute("""
                       SELECT timestamp, ph, ec, water_temp, air_temp, humidity
                       FROM telemetry_metrics
                       WHERE timestamp >= NOW() - INTERVAL '%s hour'
                       ORDER BY timestamp ASC
                       """, (hours,))
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.get("/api/camera/latest")
def get_latest_camera():
    """Génère une URL de visualisation sécurisée pour la dernière photo stockée."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
                       SELECT image_path
                       FROM image_metrics
                       ORDER BY timestamp DESC
                           LIMIT 1
                       """)
        result = cursor.fetchone()
        if not result:
            return {"url": None}

        # Génération d'une URL présignée par MinIO (valide 1 heure) pour l'affichage img src
        url = minio_client.get_presigned_url(
            "GET",
            BUCKET_NAME,
            result["image_path"],
            expires=timedelta(hours=1)
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@app.post("/api/sensors/calibrate")
def calibrate_sensor(data: CalibrationData):
    """Calcule et sauvegarde l'offset d'une sonde par rapport à une solution tampon."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1. Récupérer la toute dernière valeur brute envoyée par l'ESP
        query = f"SELECT {data.metric_type} FROM telemetry_metrics WHERE device_id = %s ORDER BY timestamp DESC LIMIT 1"
        cursor.execute(query, (data.device_id,))
        last_reading = cursor.fetchone()

        if not last_reading or last_reading[data.metric_type] is None:
            raise HTTPException(status_code=400, detail="Aucune donnée récente trouvée pour ce capteur.")

        raw_value = last_reading[data.metric_type]

        # 2. Calculer l'offset (Intercept)
        offset = data.expected_value - raw_value
        sensor_uid = f"{data.device_id}_{data.metric_type}"  # ex: mock_node2_wet_ph

        # 3. Sauvegarder dans la table sensor_calibrations (Upsert)
        cursor.execute("""
                       INSERT INTO sensor_calibrations (sensor_id, intercept)
                       VALUES (%s, %s) ON CONFLICT (sensor_id) 
            DO
                       UPDATE SET intercept = EXCLUDED.intercept, last_calibrated = NOW()
                       """, (sensor_uid, offset))

        # 4. OPTIONNEL : Publier l'offset en MQTT pour informer l'ESP
        topic = f"hydro/{data.device_id}/config"
        payload = {"sensor": data.metric_type, "offset": offset}
        publish.single(topic, payload=json.dumps(payload), hostname=getattr(AppConfig, "MQTT_BROKER", "mosquitto"))

        conn.commit()
        return {
            "status": "success",
            "sensor": sensor_uid,
            "raw_read": raw_value,
            "new_offset": offset
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()