from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType
from common.config import AppConfig
import pyspark

print("🚀 Démarrage du processeur Spark (Télémétrie & Actionneurs -> Postgres)...")



def start_telemetry_stream(spark):

# ==============================================================================
    # 1. FLUX TÉLÉMÉTRIE (Capteurs)
    # ==============================================================================
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

    telemetry_df = raw_telemetry_df.selectExpr("CAST(value AS STRING)") \
        .select(from_json(col("value"), telemetry_schema).alias("data")) \
        .select("data.*") \
        .withColumn("time", current_timestamp())


    def write_telemetry_to_postgres(df, batch_id):
        count = df.count()
        if count > 0:
            print(f"📥 [Télémétrie] Batch {batch_id} : {count} mesures insérées dans TimescaleDB.")
            try:
                df.write \
                    .mode("append") \
                    .format("jdbc") \
                    .option("url", f"jdbc:postgresql://{AppConfig.DB_HOST}:5432/{AppConfig.DB_NAME}") \
                    .option("dbtable", "telemetry") \
                    .option("user", AppConfig.DB_USER) \
                    .option("password", AppConfig.DB_PASS) \
                    .option("driver", "org.postgresql.Driver") \
                    .save()
            except Exception as e:
                print(f"❌ [Télémétrie] Erreur d'écriture DB : {e}")


    query_telemetry = telemetry_df.writeStream \
        .foreachBatch(write_telemetry_to_postgres) \
        .start()

    # ==============================================================================
    # 2. FLUX ACTIONNEURS (Acks des pompes)
    # ==============================================================================
    # Le schéma qui correspond EXACTEMENT à ce que ton mock envoie
    ack_schema = StructType() \
        .add("cmd_id", StringType()) \
        .add("status", StringType()) \
        .add("target", StringType()) \
        .add("duration_ms", IntegerType())

    df_acks_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", AppConfig.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "actuator_stream") \
        .load()

    # Parsing et formatage pour Postgres
    df_acks = df_acks_raw.select(
        from_json(col("value").cast("string"), ack_schema).alias("data")
    ).select("data.*")

    df_final = df_acks.select(
        current_timestamp().alias("time"),
        col("target").alias("actuator_id"),
        col("status").alias("action"),
        col("duration_ms"),
        col("cmd_id").alias("trigger_source")
    )


    # Fonction intelligente avec Filtre (DLQ) + Try/Catch de sécurité
    def write_actuators_to_postgres(df, batch_id):
        df.persist()  # On garde en mémoire pour éviter de recalculer

        # 1. Gestion des erreurs (Filtre des NULL)
        bad_df = df.filter(col("actuator_id").isNull())
        bad_count = bad_df.count()
        if bad_count > 0:
            print(f"🚨 ALERTE [Actionneurs] Batch {batch_id} : {bad_count} messages rejetés (target manquant) !")
            bad_df.show(truncate=False)  # Affiche les coupables dans la console

        # 2. Écriture des données saines
        good_df = df.filter(col("actuator_id").isNotNull())
        good_count = good_df.count()

        if good_count > 0:
            print(f"⚙️ [Actionneurs] Batch {batch_id} : {good_count} actions prêtes à être logguées.")
            try:
                good_df.write \
                    .mode("append") \
                    .format("jdbc") \
                    .option("url", f"jdbc:postgresql://{AppConfig.DB_HOST}:5432/{AppConfig.DB_NAME}") \
                    .option("dbtable", "actuator_logs") \
                    .option("user", AppConfig.DB_USER) \
                    .option("password", AppConfig.DB_PASS) \
                    .option("driver", "org.postgresql.Driver") \
                    .save()
            except Exception as e:
                print(f"❌ [Actionneurs] Erreur fatale DB (ex: Postgres injoignable) : {e}")

        df.unpersist()


    # Lancement de l'écriture en base
    query_acks = df_final.writeStream \
        .foreachBatch(write_actuators_to_postgres) \
        .start()

    # Flux de debug console (Optionnel, tu peux le commenter plus tard)
    debug_query = df_acks.writeStream \
        .outputMode("append") \
        .format("console") \
        .start()

    return query_telemetry,query_acks,debug_query

# Maintient le script en vie
spark.streams.awaitAnyTermination()