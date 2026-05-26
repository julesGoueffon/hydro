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
import logging
from apps.rest_api.image_processor import process_and_save_image_from_minio
from common.config import AppConfig

print("🚀 Démarrage de l'API HydroStack...")
logging.basicConfig(level=logging.INFO)
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


class CalibrationData(BaseModel):
    device_id: str
    expected_value: float  # Ex: 7.0 pour la solution tampon pH
    metric_type: str       # 'ph' ou 'ec'

class CommandOverride(BaseModel):
    target: str
    duration_ms: int
    device_id: str = "mock_node2_wet"


class CalibrationData(BaseModel):
    sensor_id: str
    slope: float
    intercept: float
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
    """Renvoie l'historique brut (format étroit) pour les graphiques filtrés."""
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

        # On renvoie les données telles quelles, le frontend s'occupe du filtrage
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
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

# @app.get("/api/camera/latest")
# def get_latest_camera():
#     """Génère une URL de visualisation sécurisée pour la dernière photo stockée."""
#     conn = get_db_connection()
#     cursor = conn.cursor(cursor_factory=RealDictCursor)
#     try:
#         cursor.execute("""
#                        SELECT image_path
#                        FROM image_metrics
#                        ORDER BY timestamp DESC
#                            LIMIT 1
#                        """)
#         result = cursor.fetchone()
#         if not result:
#             return {"url": None}
#
#         # Génération d'une URL présignée par MinIO (valide 1 heure) pour l'affichage img src
#         url = minio_client.get_presigned_url(
#             "GET",
#             BUCKET_NAME,
#             result["image_path"],
#             expires=timedelta(hours=1)
#         )
#         return {"url": url}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#     finally:
#         cursor.close()
#         conn.close()



@app.get("/api/actuators/history")
def get_actuator_history():
    """Récupère le nombre d'activations par pompe et par heure sur les dernières 24h."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # On filtre ici avec "status = 'COMPLETED'"
        cursor.execute("""
            SELECT 
                actuator_id, 
                EXTRACT(HOUR FROM "time") as hour, 
                COUNT(*) as activations
            FROM actuator_logs 
            WHERE "time" >= NOW() - INTERVAL '24 hours' 
              AND status = 'COMPLETED'
            GROUP BY actuator_id, hour
        """)
        data = cursor.fetchall()
        return {"status": "success", "data": data}
    except Exception as e:
        print(f"❌ Erreur SQL Actuators: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# 2. La route API sécurisée
@app.post("/api/command/override")
def trigger_manual_override(cmd: CommandOverride):
    """Déclenche une pompe manuellement ou coupe tout, SAUF en maintenance."""
    # Vérification du verrouillage
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:

        cursor.execute("SELECT system_mode FROM system_config WHERE id = 1")
        config = cursor.fetchone()

        if config and config["system_mode"] == "MAINTENANCE":
            raise HTTPException(
                status_code=403,
                detail="Intervention physique en cours : Commandes manuelles verrouillées."
            )
    finally:
        cursor.close()
        conn.close()

    # Construction du payload MQTT (On distingue le PULSE classique du STOP d'urgence)
    payload = {
        "action": "STOP" if cmd.target == "ALL_STOP" else "PULSE",
        "cmd_id": f"manual_api_{int(time.time())}",
        "target": cmd.target,
        "duration_ms": cmd.duration_ms,
        "device_id": cmd.device_id
    }

    # Envoi via Mosquitto
    topic = f"hydro/{cmd.device_id}/commands"
    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")
    publish.single(topic, payload=json.dumps(payload), hostname=broker_host)
    print("ici", topic, payload)

    return {"status": "success", "message": f"Ordre relayé à l'actionneur : {cmd.target}"}


from pydantic import BaseModel
from fastapi import HTTPException


# 1. Le modèle qui correspond EXACTEMENT à ce que React envoie
class CalibrationUpdate(BaseModel):
    sensor_id: str  # ex: "mock_node2_wet_ph"
    slope: float  # le fameux "a" calculé par React
    intercept: float  # le fameux "b" calculé par React


# 2. La route de sauvegarde
@app.post("/api/calibration")
def update_calibration(cal: CalibrationUpdate):
    """Enregistre la nouvelle équation mathématique de la sonde."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
                       INSERT INTO sensor_calibrations (sensor_id, slope, intercept, last_calibrated)
                       VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (sensor_id) 
            DO
                       UPDATE SET
                           slope = EXCLUDED.slope,
                           intercept = EXCLUDED.intercept,
                           last_calibrated = CURRENT_TIMESTAMP
                       """, (cal.sensor_id, cal.slope, cal.intercept))

        conn.commit()
        return {
            "status": "success",
            "message": f"Sonde {cal.sensor_id} mise à jour (a={cal.slope:.3f}, b={cal.intercept:.3f})"
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


class SensorAcquisition(BaseModel):
    device_id: str
    sensor_type: str  # "ph" ou "ec"
    duration_ms: int = 2000  # Temps de lissage sur l'ESP32


@app.post("/api/command/acquire")
def trigger_sensor_acquisition(cmd: SensorAcquisition):
    """Ordonne à l'ESP32 de faire une lecture isolée et lissée d'une sonde spécifique."""

    # Payload MQTT pour l'ESP32
    payload = {
        "action": "READ_SENSOR",
        "sensor": cmd.sensor_type,
        "duration_ms": cmd.duration_ms
    }

    topic = f"hydro/{cmd.device_id}/commands"
    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")
    publish.single(topic, payload=json.dumps(payload), hostname=broker_host)

    print(f"🔬 [Acquisition] Ordre envoyé à {cmd.device_id} pour lire {cmd.sensor_type}")

    return {"status": "success", "message": f"Acquisition {cmd.sensor_type} lancée."}


class DeviceSettingsUpdate(BaseModel):
    device_id: str
    telemetry_interval_sec: int
    ph_read_interval_ms: int
    ec_read_interval_ms: int
    temp_read_interval_ms: int


@app.get("/api/device/{device_id}/settings")
def get_device_settings(device_id: str):
    """Récupère la configuration matérielle d'un ESP32."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM device_settings WHERE device_id = %s", (device_id,))
        settings = cursor.fetchone()
        if not settings:
            raise HTTPException(status_code=404, detail="Device non trouvé")
        return {"status": "success", "data": settings}
    finally:
        cursor.close()
        conn.close()


@app.put("/api/device/settings")
def update_device_settings(settings: DeviceSettingsUpdate):
    """Met à jour la BDD et envoie la nouvelle config à l'ESP32 via MQTT."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Sauvegarde en Base de Données
        cursor.execute("""
                       INSERT INTO device_settings (device_id, telemetry_interval_sec, ph_read_interval_ms,
                                                    ec_read_interval_ms, temp_read_interval_ms)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (device_id) DO
                       UPDATE SET
                           telemetry_interval_sec = EXCLUDED.telemetry_interval_sec,
                           ph_read_interval_ms = EXCLUDED.ph_read_interval_ms,
                           ec_read_interval_ms = EXCLUDED.ec_read_interval_ms,
                           temp_read_interval_ms = EXCLUDED.temp_read_interval_ms,
                           updated_at = CURRENT_TIMESTAMP
                       """, (settings.device_id, settings.telemetry_interval_sec, settings.ph_read_interval_ms,
                             settings.ec_read_interval_ms, settings.temp_read_interval_ms))
        conn.commit()

        # 2. Synchronisation MQTT avec l'ESP32
        payload = {
            "action": "SYNC_SETTINGS",
            "telemetry_sec": settings.telemetry_interval_sec,
            "ph_ms": settings.ph_read_interval_ms,
            "ec_ms": settings.ec_read_interval_ms,
            "temp_ms": settings.temp_read_interval_ms
        }
        topic = f"hydro/{settings.device_id}/settings"
        broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")
        publish.single(topic, payload=json.dumps(payload), hostname=broker_host)

        return {"status": "success", "message": "Configuration synchronisée avec l'ESP32"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()