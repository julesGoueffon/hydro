from fastapi import FastAPI, Request
from confluent_kafka import Producer
from minio import Minio
import json
import time
import io


#PYTHONPATH=. uvicorn apps.ingestion_image.image_main:app --host 0.0.0.0 --port 5000

from common.config import AppConfig
app = FastAPI()

# --- 1. Configuration de MinIO ---
# À adapter avec ce que tu mettras dans ton docker-compose
minio_client = Minio(
    AppConfig.MINIO_ENDPOINT,
    access_key=AppConfig.MINIO_ACCESS_KEY,
    secret_key=AppConfig.MINIO_SECRET_KEY,
    secure=False
)

# On s'assure que le "dossier" (bucket) 'images' existe dans MinIO
bucket_name = "images"
try:
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
except Exception as e:
    print(f"⚠️ Attention, MinIO n'est pas joignable : {e}")

# --- 2. Configuration de Redpanda/Kafka ---
conf = {
    'bootstrap.servers': 'localhost:9092',  # 'redpanda:9092' dans Docker
    'client.id': 'esp32-image-ingestor'
}
producer = Producer(conf)


@app.post("/upload")
async def upload_image(request: Request):
    image_data = await request.body()
    timestamp = int(time.time())

    # Le nom du fichier dans MinIO
    object_name = f"image_{timestamp}.jpg"

    # --- Étape A : Sauvegarde directe dans MinIO ---
    # io.BytesIO permet de faire croire à MinIO que nos données en mémoire sont un fichier
    minio_client.put_object(
        bucket_name,
        object_name,
        data=io.BytesIO(image_data),
        length=len(image_data),
        content_type="image/jpeg"
    )

    # Le chemin "logique" qu'on va envoyer à Spark
    storage_path = f"{bucket_name}/{object_name}"

    # --- Étape B : Envoi du message à Kafka ---
    event = {
        "sensor_name": "esp32_cam_serre",
        "timestamp": timestamp,
        "image_path": storage_path
        # Plus de statut, on garde l'essentiel !
    }

    producer.produce(
        topic='image_events',
        value=json.dumps(event).encode('utf-8')
    )
    producer.flush()

    return {"message": "Image stockée dans MinIO et notifiée", "path": storage_path}