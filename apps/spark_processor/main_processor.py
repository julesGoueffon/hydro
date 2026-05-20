import pyspark
from pyspark.sql import SparkSession

# On importe nos fonctions "ouvrières"
from image_processor import start_image_stream
from weather_processor import start_weather_stream
from telemetry_processor import start_telemetry_stream

print("🚀 Démarrage de l'application globale Spark...")

# 1. Création de l'UNIQUE session Spark pour tout le conteneur
spark_version = pyspark.__version__
kafka_pkg = f"org.apache.spark:spark-sql-kafka-0-10_2.12:{spark_version}"

spark = SparkSession.builder \
    .appName("GlobalHydroProcessor") \
    .config("spark.jars.packages", f"{kafka_pkg},org.postgresql:postgresql:42.7.3") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# 2. Lancement des flux en parallèle
try:
    query_weather = start_weather_stream(spark)
    query_images = start_image_stream(spark)
    query_telemetry, query_actuators = start_telemetry_stream(spark)  # Si tu retournes 2 queries

    print("✅ Tous les flux sont lancés avec succès !")

    # 3. Le verrou final : On attend indéfiniment que l'un des flux se termine (ou plante)
    spark.streams.awaitAnyTermination()

except Exception as e:
    print(f"❌ Erreur critique lors du lancement des flux : {e}")
    spark.stop()