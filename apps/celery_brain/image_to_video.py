import io
import os
import subprocess
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
from psycopg2.extras import RealDictCursor
from minio import Minio

from apps.celery_brain.common import app, get_db_connection
from common.config import AppConfig

# --- Configuration ---
SEUIL_NETTETE = 100.0


def filter_chunk_of_3(chunk):
    """Prend la 1ère image nette, sinon la 2ème, sinon la moins pire."""
    if len(chunk) == 0:
        return None
    row1 = chunk.iloc[0]
    if row1['blur_score'] >= SEUIL_NETTETE:
        return row1
    if len(chunk) > 1:
        row2 = chunk.iloc[1]
        if row2['blur_score'] >= SEUIL_NETTETE:
            return row2
    return chunk.loc[chunk['blur_score'].idxmax()]


def celery_task_video(image_keys, path, minio_client):
    """Génère une vidéo MP4 à partir d'un flux d'images MinIO."""
    cmd = [
        'ffmpeg', '-y',
        '-f', 'image2pipe',
        '-vcodec', 'mjpeg',
        '-i', '-',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        path
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for key in image_keys:
        # CORRECTION : Utilisation du vrai bucket d'images via AppConfig
        response = minio_client.get_object(AppConfig.MINIO_BUCKET_NAME, key)
        try:
            process.stdin.write(response.read())
        finally:
            response.close()
            response.release_conn()

    process.stdin.close()
    process.wait()


def concat_hourly_videos(video_paths_local, output_daily_path):
    """Fusionne plusieurs vidéos MP4 bout à bout sans ré-encodage."""
    list_file_path = "/tmp/concat_list.txt"
    with open(list_file_path, "w") as f:
        for vp in video_paths_local:
            f.write(f"file '{vp}'\n")

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file_path,
        '-c', 'copy',
        output_daily_path
    ]
    subprocess.run(cmd, check=True)
    os.remove(list_file_path)


# CORRECTION : Changement du nom de la tâche pour ne pas écraser le contrôle des pompes
@app.task(name="generate_timelapses")
def generate_timelapses():
    print("🎬 Démarrage de la génération des Timelapses...")
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        now_utc = datetime.now(timezone.utc)
        now_utc_min = now_utc - timedelta(seconds=5)
        now_utc_previous_hours = now_utc_min.replace(minute=0, second=0, microsecond=0)
        ts_limit = int(now_utc_previous_hours.timestamp())

        minio_client = Minio(
            AppConfig.MINIO_ENDPOINT,
            access_key=AppConfig.MINIO_ACCESS_KEY,
            secret_key=AppConfig.MINIO_SECRET_KEY,
            secure=False
        )
        bucket_videos = getattr(AppConfig, "MINIO_VIDEO_BUCKET", "videos")

        if not minio_client.bucket_exists(bucket_videos):
            minio_client.make_bucket(bucket_videos)

        # ==========================================
        # 1. TRAITEMENT DES VIDÉOS HORAIRES
        # ==========================================
        request_images = """
                         SELECT timestamp, image_path, blur_score, sensor_name
                         FROM image_metrics
                         WHERE timestamp < %s
                         ORDER BY timestamp \
                         """
        df = pd.read_sql_query(request_images, conn, params=(ts_limit,))

        if not df.empty:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            df['groupe_heure'] = df['datetime'].dt.floor('h')

            groupes = df.groupby(['groupe_heure', 'sensor_name'])

            for (heure, sensor), groupe_df in groupes:
                groupe_df = groupe_df.sort_values('timestamp')
                groupe_df['chunk_id'] = np.arange(len(groupe_df)) // 3
                filtered_df = groupe_df.groupby('chunk_id').apply(filter_chunk_of_3).reset_index(drop=True)

                paths_to_delete = groupe_df['image_path'].tolist()

                cur.execute("""
                            SELECT count(*)
                            FROM video_metrics
                            WHERE "timestamp" = %s
                              AND sensor_name = %s
                              AND video_type = 'hour'
                            """, (int(heure.timestamp()), sensor))

                existe = cur.fetchone()[0]

                if existe == 0:
                    object_name = f"{sensor}_{heure.strftime('%Y_%m_%d_%H')}_hour.mp4"
                    path_local = f"/tmp/{object_name}"

                    celery_task_video(filtered_df['image_path'], path_local, minio_client)

                    result = minio_client.fput_object(bucket_videos, object_name, path_local, content_type="video/mp4")
                    if result:
                        if os.path.exists(path_local): os.remove(path_local)

                        # Inscription en base
                        cur.execute("""
                                    INSERT INTO video_metrics (sensor_name, "timestamp", video_path, video_type)
                                    VALUES (%s, %s, %s, 'hour')
                                    """, (sensor, int(heure.timestamp()), object_name))

                        # CORRECTION : Nettoyage BDD ET nettoyage physique MinIO
                        cur.execute("DELETE FROM image_metrics WHERE image_path = ANY(%s)", (paths_to_delete,))
                        for img_path in paths_to_delete:
                            minio_client.remove_object(AppConfig.MINIO_BUCKET_NAME, img_path)

                        conn.commit()
                        print(
                            f"✅ Vidéo horaire {object_name} créée. {len(paths_to_delete)} images supprimées de MinIO et Postgres.")
                else:
                    # CORRECTION : Nettoyage physique MinIO même si la vidéo existait déjà
                    cur.execute("DELETE FROM image_metrics WHERE image_path = ANY(%s)", (paths_to_delete,))
                    for img_path in paths_to_delete:
                        minio_client.remove_object(AppConfig.MINIO_BUCKET_NAME, img_path)
                    conn.commit()
                    print(f"⏭️ Vidéo horaire déjà existante pour {sensor} à {heure.strftime('%H:%M')}. Images purgées.")
        else:
            print("Aucune nouvelle image horaire à traiter.")

        # ==========================================
        # 2. AGRÉGATION JOURNALIÈRE (VEILLE)
        # ==========================================
        yesterday = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        yesterday_ts = int(yesterday.timestamp())
        ts_today = yesterday_ts + 86400

        cur.execute("""
                    SELECT DISTINCT sensor_name
                    FROM video_metrics
                    WHERE video_type = 'hour'
                      AND "timestamp" >= %s
                      AND "timestamp" < %s
                    """, (yesterday_ts, ts_today))

        sensors_hier = [row[0] for row in cur.fetchall()]

        for sensor in sensors_hier:
            cur.execute("""
                        SELECT count(*)
                        FROM video_metrics
                        WHERE "timestamp" = %s
                          AND sensor_name = %s
                          AND video_type = 'daily'
                        """, (yesterday_ts, sensor))

            if cur.fetchone()[0] == 0:
                print(f"\n🔄 Création de la vidéo journalière pour {sensor} ({yesterday.strftime('%Y-%m-%d')})...")

                cur.execute("""
                            SELECT video_path
                            FROM video_metrics
                            WHERE video_type = 'hour'
                              AND sensor_name = %s
                              AND "timestamp" >= %s
                              AND "timestamp" < %s
                            ORDER BY "timestamp" ASC
                            """, (sensor, yesterday_ts, ts_today))

                hourly_videos = [row[0] for row in cur.fetchall()]
                local_hourly_paths = []

                for video_path_minio in hourly_videos:
                    local_path = f"/tmp/{video_path_minio}"
                    minio_client.fget_object(bucket_videos, video_path_minio, local_path)
                    local_hourly_paths.append(local_path)

                daily_object_name = f"{sensor}_{yesterday.strftime('%Y_%m_%d')}_daily.mp4"
                daily_local_path = f"/tmp/{daily_object_name}"

                try:
                    concat_hourly_videos(local_hourly_paths, daily_local_path)
                    minio_client.fput_object(bucket_videos, daily_object_name, daily_local_path,
                                             content_type="video/mp4")

                    cur.execute("""
                                INSERT INTO video_metrics (sensor_name, "timestamp", video_path, video_type)
                                VALUES (%s, %s, %s, 'daily')
                                """, (sensor, yesterday_ts, daily_object_name))
                    conn.commit()
                    print(f"✅ Vidéo journalière {daily_object_name} générée avec succès.")

                finally:
                    if os.path.exists(daily_local_path): os.remove(daily_local_path)
                    for lp in local_hourly_paths:
                        if os.path.exists(lp): os.remove(lp)
            else:
                print(f"⏭️ Vidéo journalière déjà existante pour {sensor} ({yesterday.strftime('%Y-%m-%d')}).")

    except Exception as e:
        print(f"❌ Erreur lors de la génération des timelapses : {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()