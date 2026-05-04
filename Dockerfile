# Image légère basée sur Debian, parfaite pour la production
FROM python:3.10-slim

# ==========================================
# 1. DÉPENDANCES SYSTÈME (Lourdes)
# ==========================================
RUN apt-get update && apt-get install -y \
    default-jre \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Définition de la variable d'environnement pour Java (Indispensable pour Spark)
ENV JAVA_HOME=/usr/lib/jvm/default-java

# On crée le dossier de travail dans le conteneur
WORKDIR /app

# ==========================================
# 2. DÉPENDANCES PYTHON
# ==========================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import pyspark; from pyspark.sql import SparkSession; SparkSession.builder.config('spark.jars.packages', f'org.apache.spark:spark-sql-kafka-0-10_2.12:{pyspark.__version__},org.postgresql:postgresql:42.7.3').getOrCreate()"


# ==========================================
# 3. COPIE DU CODE SOURCE
# ==========================================
# On copie proprement tout le code à la racine du WORKDIR (/app)
COPY . .