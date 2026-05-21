import cv2
import numpy as np
import io
import psycopg2
from minio import Minio
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
        minio_client = Minio(
            AppConfig.MINIO_ENDPOINT,
            access_key=AppConfig.MINIO_ACCESS_KEY,
            secret_key=AppConfig.MINIO_SECRET_KEY,
            secure=False
        )


        response = minio_client.get_object(AppConfig.MINIO_BUCKET_NAME, image_key)
        image_bytes = response.read()
        response.close()
        response.release_conn()

        # --- 2. TRAITEMENT OPENCV ---
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is not None:
            blur_score = float(cv2.Laplacian(img, cv2.CV_64F).var())
        else:
            print(f"⚠️ Image {image_key} corrompue ou illisible.")

    except Exception as e:
        print(f"❌ Erreur lors de la lecture MinIO ou calcul OpenCV: {e}")

    # --- 3. INSERTION DANS POSTGRESQL ---
    try:
        conn = psycopg2.connect(
            host=AppConfig.DB_HOST,
            database=AppConfig.DB_NAME,
            user=AppConfig.DB_USER,
            password=AppConfig.DB_PASS
        )
        cursor = conn.cursor()

        # timestamp est un entier Unix, on l'insère directement en bigint
        insert_query = """
            INSERT INTO image_metrics (sensor_name, timestamp, image_path, blur_score)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (sensor_name, timestamp, image_key, blur_score))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Métriques insérées avec succès ! (Flou: {blur_score:.2f})")

    except Exception as e:
        print(f"❌ Erreur lors de l'insertion Postgres : {e}")