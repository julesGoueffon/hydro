from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, LongType, StringType
from common.config import AppConfig

print("📸 Démarrage du processeur Spark (Images -> Postgres)...")

# 1. Le schéma EXACT envoyé par ton FastAPI
schema = StructType([
    StructField("sensor_name", StringType()),
    StructField("timestamp", LongType()),  # LongType car c'est un timestamp Unix
    StructField("image_path", StringType())
])

spark = SparkSession.builder \
    .appName("ImageStreamingProcessor") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.postgresql:postgresql:42.7.3") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

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
    .select("data.*")


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
query.awaitTermination()