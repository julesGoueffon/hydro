FROM python:3.10-slim

# ==========================================
# 1. DÉPENDANCES SYSTÈME (Uniquement OpenCV)
# ==========================================
# Java et l'environnement associé ont été supprimés (Gain de place et RAM massif pour ARM)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# On crée le dossier de travail dans le conteneur
WORKDIR /app

# ==========================================
# 2. DÉPENDANCES PYTHON
# ==========================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Le téléchargement des Jars Spark-Kafka-Postgres a été supprimé
ENV PYTHONPATH=/app

# ==========================================
# 3. COPIE DU CODE SOURCE
# ==========================================
COPY . .