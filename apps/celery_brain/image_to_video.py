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

# --- Configuration des seuils ---
SEUIL_NETTETE = 100.0  # À AJUSTER : Si blur_score < ce seuil, l'image est considérée comme floue


def filter_chunk_of_3(chunk):
    """
    Prend la 1ère image. Si floue, la 2ème. Si floue, la moins floue des 3.
    (On suppose ici qu'un blur_score ÉLEVÉ = NET. Inverser la logique si besoin).
    """
    if len(chunk) == 0:
        return None

    row1 = chunk.iloc[0]
    if row1['blur_score'] >= SEUIL_NETTETE:
        return row1

    if len(chunk) > 1:
        row2 = chunk.iloc[1]
        if row2['blur_score'] >= SEUIL_NETTETE:
            return row2

    # Si on arrive ici, toutes sont floues (ou il n'y en a qu'une et elle est floue).
    # On prend celle avec le score le plus élevé (la moins floue des 3)
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
        response = minio_client.get_object("my-bucket", key)
        try:
            process.stdin.write(response.read())
        finally:
            response.close()
            response.release_conn()

    process.stdin.close()
    process.wait()


def concat_hourly_videos(video_paths_local, output_daily_path):
    """Fusionne plusieurs vidéos MP4 bout à bout sans ré-encodage."""
    # Créer le fichier texte requis par ffmpeg pour le concat demuxer
    list_file_path = "/tmp/concat_list.txt"
    with open(list_file_path, "w") as f:
        for vp in video_paths_local:
            f.write(f"file '{vp}'\n")

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file_path,
        '-c', 'copy',  # Copie directe, super rapide !
        output_daily_path
    ]
    subprocess.run(cmd, check=True)
    os.remove(list_file_path)


@app.task(name="evaluate_and_control")
def evaluate_and_control():
    conn = get_db_connection()
    cur = conn.cursor()

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
    bucket_videos = "videos"
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
            print(f"\n--- Groupe Horaire : {heure.strftime('%H:%M')} (Capteur: {sensor}) ---")

            # -- Appliquer l'algorithme "1 sur 3 intelligent" --
            # On trie bien chronologiquement, on crée un ID de groupe de 3, et on applique la fonction
            groupe_df = groupe_df.sort_values('timestamp')
            groupe_df['chunk_id'] = np.arange(len(groupe_df)) // 3
            filtered_df = groupe_df.groupby('chunk_id').apply(filter_chunk_of_3).reset_index(drop=True)

            paths_to_delete = groupe_df['image_path'].tolist()  # On supprime toutes les images de base

            request_existe = """
                             SELECT count(*) \
                             FROM video_metrics
                             WHERE "timestamp" = %s \
                               AND sensor_name = %s \
                               AND video_type = 'hour' \
                             """
            cur.execute(request_existe, (int(heure.timestamp()), sensor))
            existe = cur.fetchone()[0]

            if existe == 0:
                object_name = f"{sensor}_{heure.strftime('%Y_%m_%d_%H')}_hour.mp4"
                path_local = f"/tmp/{object_name}"

                # Génération avec les images filtrées
                celery_task_video(filtered_df['image_path'], path_local, minio_client)

                result = minio_client.fput_object(bucket_videos, object_name, path_local, content_type="video/mp4")
                if result:
                    if os.path.exists(path_local): os.remove(path_local)

                    # Ajouter la vidéo en base
                    insert_video = """
                                   INSERT INTO video_metrics (sensor_name, "timestamp", video_path, video_type)
                                   VALUES (%s, %s, %s, 'hour') \
                                   """
                    cur.execute(insert_video, (sensor, int(heure.timestamp()), object_name))

                    # Supprimer les images
                    cur.execute("DELETE FROM image_metrics WHERE image_path = ANY(%s)", (paths_to_delete,))
                    conn.commit()
                    print(f"✅ Vidéo horaire {object_name} créée. {len(paths_to_delete)} images purgées.")
            else:
                print(f"⏭️ Vidéo horaire déjà existante pour {sensor} à {heure.strftime('%H:%M')}. Purge des images.")
                cur.execute("DELETE FROM image_metrics WHERE image_path = ANY(%s)", (paths_to_delete,))
                conn.commit()
    else:
        print("Aucune nouvelle image horaire à traiter.")

    # ==========================================
    # 2. AGRÉGATION JOURNALIÈRE (VEILLE)
    # ==========================================
    # Calcul du timestamp de la veille à minuit pile
    yesterday = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    yesterday_ts = int(yesterday.timestamp())

    # On cherche tous les capteurs qui ont eu des vidéos horaires hier
    request_sensors = """
                      SELECT DISTINCT sensor_name
                      FROM video_metrics
                      WHERE video_type = 'hour' \
                        AND "timestamp" >= %s \
                        AND "timestamp" < %s \
                      """
    ts_today = yesterday_ts + 86400  # Minuit aujourd'hui
    cur.execute(request_sensors, (yesterday_ts, ts_today))
    sensors_hier = [row[0] for row in cur.fetchall()]

    for sensor in sensors_hier:
        # Vérifier si la vidéo daily existe déjà
        cur.execute("""
                    SELECT count(*)
                    FROM video_metrics
                    WHERE "timestamp" = %s
                      AND sensor_name = %s
                      AND video_type = 'daily'
                    """, (yesterday_ts, sensor))

        if cur.fetchone()[0] == 0:
            print(f"\n🔄 Création de la vidéo journalière pour {sensor} ({yesterday.strftime('%Y-%m-%d')})...")

            # Récupérer toutes les vidéos horaires de ce capteur pour hier, triées
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

            # Télécharger temporairement les vidéos horaires
            for video_path_minio in hourly_videos:
                local_path = f"/tmp/{video_path_minio}"
                minio_client.fget_object(bucket_videos, video_path_minio, local_path)
                local_hourly_paths.append(local_path)

            daily_object_name = f"{sensor}_{yesterday.strftime('%Y_%m_%d')}_daily.mp4"
            daily_local_path = f"/tmp/{daily_object_name}"

            # Fusionner les vidéos
            try:
                concat_hourly_videos(local_hourly_paths, daily_local_path)

                # Uploader la vidéo journalière
                minio_client.fput_object(bucket_videos, daily_object_name, daily_local_path, content_type="video/mp4")

                # Inscrire en base de données
                cur.execute("""
                            INSERT INTO video_metrics (sensor_name, "timestamp", video_path, video_type)
                            VALUES (%s, %s, %s, 'daily')
                            """, (sensor, yesterday_ts, daily_object_name))
                conn.commit()
                print(f"✅ Vidéo journalière {daily_object_name} générée avec succès.")

            finally:
                # Nettoyage des fichiers temporaires
                if os.path.exists(daily_local_path): os.remove(daily_local_path)
                for lp in local_hourly_paths:
                    if os.path.exists(lp): os.remove(lp)
        else:
            print(f"⏭️ Vidéo journalière déjà existante pour {sensor} ({yesterday.strftime('%Y-%m-%d')}).")

    cur.close()
    conn.close()