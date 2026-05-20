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

# Configuration centralisée
from common.config import AppConfig
from image_processor import process_and_save_image_from_minio

print("🚀 Démarrage de l'API HydroStack...")

app = FastAPI(title="HydroStack API")

# --- 0. CONFIGURATION CORS (Pour React) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod, remplacer par l'IP/Port de ton React (ex: "http://localhost:5173")
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. CONFIGURATION MINIO ---
minio_client = Minio(
    AppConfig.MINIO_ENDPOINT,
    access_key=AppConfig.MINIO_ACCESS_KEY,
    secret_key=AppConfig.MINIO_SECRET_KEY,
    secure=False
)

bucket_name = AppConfig.MINIO_BUCKET_NAME
try:
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        print(f"📁 Bucket MinIO '{bucket_name}' créé avec succès.")
except Exception as e:
    print(f"⚠️ Attention, MinIO n'est pas joignable : {e}")


# --- UTILITAIRES BDD ---
def get_db_connection():
    return psycopg2.connect(
        host=AppConfig.DB_HOST,
        database=AppConfig.DB_NAME,
        user=AppConfig.DB_USER,
        password=AppConfig.DB_PASS
    )


# --- SCHÉMAS PYDANTIC (Validation des requêtes React) ---
class ConfigUpdate(BaseModel):
    mode_auto: bool
    target_ph: float
    target_ec: float


class CommandOverride(BaseModel):
    target: str  # ex: "pump_ph_minus"
    duration_ms: int  # ex: 2000
    device_id: str  # ex: "node2"


# =====================================================================
# ROUTES "INGESTION" (Capteurs -> Serveur)
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
            bucket_name, object_name,
            data=io.BytesIO(image_data),
            length=len(image_data),
            content_type="image/jpeg"
        )
    except Exception as e:
        return {"status": "error", "message": f"Erreur MinIO: {e}"}

    background_tasks.add_task(
        process_and_save_image_from_minio,
        device_id, timestamp, object_name
    )

    return {"message": "Image stockée et traitement lancé", "path": object_name}


# =====================================================================
# ROUTES "FRONTEND" (Serveur <-> React)
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
        # Transforme la liste en dictionnaire facile à lire pour React : {"ph": 6.1, "ec": 1.4}
        status = {row["metric"]: {"value": row["value"], "time": row["time"]} for row in data}
        return {"status": "success", "data": status}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/camera/latest")
def get_latest_camera():
    """Renvoie l'URL de la dernière image générée."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT image_path, blur_score, timestamp 
            FROM image_metrics 
            ORDER BY timestamp DESC LIMIT 1
        """)
        img_data = cursor.fetchone()

        if not img_data:
            return {"status": "empty", "url": None}

        # Astuce de pro : MinIO génère une URL temporaire valide 1 heure pour React
        presigned_url = minio_client.presigned_get_object(
            bucket_name,
            img_data["image_path"],
            expires=timedelta(hours=1)
        )

        return {
            "status": "success",
            "url": presigned_url,
            "blur_score": img_data["blur_score"],
            "timestamp": img_data["timestamp"]
        }
    finally:
        cursor.close()
        conn.close()


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
    """React envoie un JSON validé par Pydantic pour changer les consignes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE system_config 
            SET mode_auto = %s, target_ph = %s, target_ec = %s, updated_at = NOW()
            WHERE id = 1
        """, (config.mode_auto, config.target_ph, config.target_ec))
        conn.commit()
        return {"status": "success", "message": "Configuration mise à jour"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# --- C. CONTRÔLE-COMMANDE ---

@app.post("/api/command/override")
def trigger_manual_override(cmd: CommandOverride):
    """React demande l'activation manuelle d'une pompe via MQTT."""
    payload = {
        "action": "PULSE",
        "cmd_id": f"manual_api_{int(time.time())}",
        "target": cmd.target,
        "duration_ms": cmd.duration_ms
    }
    topic = f"hydro/{cmd.device_id}/commands"
    broker_host = getattr(AppConfig, "MQTT_BROKER", "mosquitto")

    try:
        publish.single(topic, payload=json.dumps(payload), hostname=broker_host, port=1883)
        return {"status": "success", "message": f"Ordre envoyé sur {topic}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec MQTT : {e}")