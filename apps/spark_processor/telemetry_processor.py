from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, lit
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
from common.config import AppConfig
import pyspark

print("🚀 Démarrage du processeur Spark (Télémétrie & Actionneurs -> Postgres)...")

# 💡 ASTUCE INDUS : On récupère dynamiquement la version exacte de PySpark
spark_version = pyspark.__version__
kafka_pkg = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{spark_version}"

spark = SparkSession.builder \
    .appName("HydroTelemetryProcessor") \
    .config("spark.jars.packages", f"{kafka_pkg},org.postgresql:postgresql:42.7.3") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# ==============================================================================
# 1. FLUX TÉLÉMÉTRIE (Capteurs)
# ==============================================================================

# Schéma attendu depuis les mocks (format "étroit")
telemetry_schema = StructType([
    StructField("device_id", StringType()),
    StructField("metric", StringType()),
    StructField("value", DoubleType())
])

raw_telemetry_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", AppConfig.KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", "telemetry_stream") \
    .option("startingOffsets", "latest") \
    .load()

# On parse le JSON et on ajoute le timestamp d'arrivée
telemetry_df = raw_telemetry_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), telemetry_schema).alias("data")) \
    .select("data.*") \
    .withColumn("time", current_timestamp())

def write_telemetry_to_postgres(df, batch_id):
    count = df.count()
    if count > 0:
        print(f"📥 [Télémétrie] Batch {batch_id} : {count} mesures insérées dans TimescaleDB.")
        df.write \
            .mode("append") \
            .format("jdbc") \
            .option("url", f"jdbc:postgresql://{AppConfig.DB_HOST}:5432/{AppConfig.DB_NAME}") \
            .option("dbtable", "telemetry") \
            .option("user", AppConfig.DB_USER) \
            .option("password", AppConfig.DB_PASS) \
            .option("driver", "org.postgresql.Driver") \
            .save()

query_telemetry = telemetry_df.writeStream \
    .foreachBatch(write_telemetry_to_postgres) \
    .start()


# ==============================================================================
# 2. FLUX ACTIONNEURS (Acks des pompes et relais)
# ==============================================================================

# Schéma attendu depuis les messages d'acquittement (ACK) des mocks
actuator_schema = StructType([
    StructField("cmd_id", StringType()),
    StructField("status", StringType()),             # ex: "STARTED", "COMPLETED"
    StructField("actuator", StringType()),           # ex: "pump_ph_minus"
    StructField("actual_duration_ms", IntegerType()),# Si pulse terminé
    StructField("expected_duration_ms", IntegerType()),# Si pulse démarré
    StructField("position", IntegerType()),          # Si persiennes
    StructField("new_state", StringType())           # Si relais ON/OFF
])

raw_actuator_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", AppConfig.KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", "actuator_stream") \
    .option("startingOffsets", "latest") \
    .load()

# On transforme les données pour qu'elles collent PARFAITEMENT à la table SQL `actuator_logs`
actuator_df = raw_actuator_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), actuator_schema).alias("data")) \
    .select("data.*") \
    .withColumn("time", current_timestamp()) \
    .withColumnRenamed("actuator", "actuator_id") \
    .withColumnRenamed("status", "action") \
    .withColumn("duration_ms", col("actual_duration_ms")) \
    .withColumn("trigger_source", lit("auto_backend")) \
    .select("time", "actuator_id", "action", "duration_ms", "trigger_source")

def write_actuators_to_postgres(df, batch_id):
    count = df.count()
    if count > 0:
        print(f"⚙️ [Actionneurs] Batch {batch_id} : {count} actions logguées.")
        df.write \
            .mode("append") \
            .format("jdbc") \
            .option("url", f"jdbc:postgresql://{AppConfig.DB_HOST}:5432/{AppConfig.DB_NAME}") \
            .option("dbtable", "actuator_logs") \
            .option("user", AppConfig.DB_USER) \
            .option("password", AppConfig.DB_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .save()

query_actuators = actuator_df.writeStream \
    .foreachBatch(write_actuators_to_postgres) \
    .start()

# Maintient le script en vie pour écouter indéfiniment les deux flux
spark.streams.awaitAnyTermination()