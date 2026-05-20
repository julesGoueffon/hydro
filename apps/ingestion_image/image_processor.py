import cv2
import numpy as np
import boto3
import psycopg2
from common.config import AppConfig


def process_and_save_image_from_minio(sensor_name: str, timestamp: int, image_key: str):
    """
    1. Télécharge l'image depuis MinIO (en RAM)
    2. Calcule le score de flou avec OpenCV
    3. Sauvegarde les métriques dans PostgreSQL
    """
    print(f"📸 Traitement de l'image {image_key} depuis MinIO...")
    blur_score = 0.0

    # --- 1. LECTURE DEPUIS MINIO (EN MÉMOIRE) ---
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=f"http://{AppConfig.MINIO_ENDPOINT}",  # ex: minio:9000
            aws_access_key_id=AppConfig.MINIO_ACCESS_KEY,
            aws_secret_access_key=AppConfig.MINIO_SECRET_KEY
        )

        response = s3.get_object(Bucket=AppConfig.MINIO_BUCKET_NAME, Key=image_key)
        image_bytes = response['Body'].read()

        # --- 2. TRAITEMENT OPENCV ---
        # On convertit les bytes directement en image OpenCV sans toucher au disque dur
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is not None:
            # Variance du Laplacien (plus le score est élevé, plus c'est net)
            blur_score = float(cv2.Laplacian(img, cv2.CV_64F).var())
        else:
            print(f"⚠️ Image {image_key} corrompue ou illisible.")

    except Exception as e:
        print(f"❌ Erreur lors de la lecture MinIO ou calcul OpenCV: {e}")
        # On continue quand même pour insérer la ligne avec un score de 0.0

    # --- 3. INSERTION DANS POSTGRESQL ---
    try:
        conn = psycopg2.connect(
            host=AppConfig.DB_HOST,  # ex: greenhouse_db
            database=AppConfig.DB_NAME,
            user=AppConfig.DB_USER,
            password=AppConfig.DB_PASS
        )
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO image_metrics (sensor_name, timestamp, image_path, blur_score)
            VALUES (%s, to_timestamp(%s), %s, %s)
        """
        # Note: image_path garde le chemin "logique" (ex: images/photo_123.jpg)
        cursor.execute(insert_query, (sensor_name, timestamp, image_key, blur_score))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Métriques insérées avec succès ! (Flou: {blur_score:.2f})")

    except Exception as e:
        print(f"❌ Erreur lors de l'insertion Postgres : {e}")