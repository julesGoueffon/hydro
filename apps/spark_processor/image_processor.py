import cv2
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.sql.types import StructType, StructField, LongType, StringType, FloatType
from common.config import AppConfig
import boto3 # Pour lire l'image dans MinIO

print("📸 Démarrage du processeur Spark (Images -> Postgres)...")

def start_image_stream(spark):

    # 1. Le schéma EXACT envoyé par ton FastAPI
    schema = StructType([
        StructField("sensor_name", StringType()),
        StructField("timestamp", LongType()),  # LongType car c'est un timestamp Unix
        StructField("image_path", StringType())
    ])


    # --- LOGIQUE DE DETECTION DE FLOU ---
    def get_blur_score(image_path):
        try:
            # Connexion à MinIO pour récupérer l'image
            s3 = boto3.client('s3',
                              endpoint_url=f"http://{AppConfig.MINIO_ENDPOINT}",
                              aws_access_key_id=AppConfig.MINIO_ACCESS_KEY,
                              aws_secret_access_key=AppConfig.MINIO_ACCESS_KEY
                              )

            # On récupère l'objet
            response = s3.get_object(Bucket=AppConfig.MINIO_BUCKET_NAME, Key=image_path.replace("images/", ""))
            image_bytes = response['Body'].read()

            # OpenCV processing
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

            if img is None: return 0.0

            # Variance du Laplacien
            return float(cv2.Laplacian(img, cv2.CV_64F).var())
        except Exception as e:
            print(f"Erreur calcul flou pour {image_path}: {e}")
            return 0.0

    blur_udf = udf(get_blur_score, FloatType())

    # 2. On écoute le NOUVEAU topic
    raw_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", AppConfig.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "image_events") \
        .option("startingOffsets", "earliest") \
        .load()

    # 3. Décodage du JSON
    json_df = raw_df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")\
        .withColumn("blur_score", blur_udf(col("image_path"))) # On ajoute la colonne calculée


    def write_to_postgres(df, batch_id):
        print(f"📥 Traitement des images - Batch {batch_id} avec {df.count()} lignes...")
        jdbc_url = f"jdbc:postgresql://{AppConfig.DB_HOST}:5432/{AppConfig.DB_NAME}"

        try:
            df.write \
                .mode("append") \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", "image_metrics") \
                .option("user", AppConfig.DB_USER) \
                .option("password", AppConfig.DB_PASS) \
                .option("driver", "org.postgresql.Driver") \
                .save()
            print(f"✅ Batch {batch_id} (Images) inséré avec succès !")
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion : {e}")


    # 4. Lancement du flux
    query = json_df.writeStream.foreachBatch(write_to_postgres).start()
    return query
