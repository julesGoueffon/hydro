from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, DoubleType, IntegerType, StringType
from common.config import AppConfig

print("🚀🚀🚀 V3 - LE CODE PUR ET DUR 🚀🚀🚀")

# 1. Le schéma EXACT du JSON
schema = StructType([
    StructField("temperature", DoubleType()),
    StructField("windspeed", DoubleType()),
    StructField("weathercode", IntegerType()),
    StructField("time", StringType()),
    StructField("sensor_name", StringType())
])

spark = SparkSession.builder \
    .appName("WeatherStreamingProcessor") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.postgresql:postgresql:42.7.3") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", AppConfig.KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", "weather_raw") \
    .option("startingOffsets", "earliest") \
    .load()

# 2. On extrait juste la data, AUCUN renommage
json_df = raw_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

def write_to_postgres(df, batch_id):
    print(f"📥 Traitement du Batch {batch_id}...")
    try:
        # 3. On insère directement. df a "time", la BDD a "time". Fin de l'histoire.
        df.write \
            .mode("append") \
            .format("jdbc") \
            .option("url", "jdbc:postgresql://localhost:5432/greenhouse") \
            .option("dbtable", "weather_metrics") \
            .option("user", "admin") \
            .option("password", "password") \
            .option("driver", "org.postgresql.Driver") \
            .save()
        print(f"✅ Batch {batch_id} inséré avec succès !")
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion : {e}")

print("🚀 Spark écoute Redpanda et écrit dans Postgres...")
query = json_df.writeStream.foreachBatch(write_to_postgres).start()
query.awaitTermination()    