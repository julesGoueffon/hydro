# common/config.py
import os
from dotenv import load_dotenv


load_dotenv()  # Cherche le .env à la racine par défaut

class AppConfig:
    # --- INFRA ---
    # Remplacé 'localhost:9092' par 'redpanda:9092'
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')

    # --- DATABASE ---
    DB_USER = os.getenv('POSTGRES_USER', 'admin')
    DB_PASS = os.getenv('POSTGRES_PASSWORD', 'password')
    DB_NAME = os.getenv('POSTGRES_DB', 'greenhouse')
    # Remplacé 'localhost' par 'greenhouse_db'
    DB_HOST = os.getenv('POSTGRES_HOST', 'greenhouse_db')

    # --- API WEATHER ---
    WEATHER_URL = os.getenv('WEATHER_API_URL', '')
    LAT = os.getenv('CITY_LAT', '47.79')
    LON = os.getenv('CITY_LON', '3.57')

    # --- STORAGE (MINIO) ---
    # Remplacé 'localhost:9000' par 'minio-storage:9000'
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio-storage:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'admin')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'password')
    MINIO_BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'images')

    # --- celery ---
    REDIS_URL = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
