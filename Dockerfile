# Image légère basée sur Debian, parfaite pour la production
FROM python:3.10-slim

# ==========================================
# 1. DÉPENDANCES SYSTÈME (Lourdes)
# ==========================================
# Explication : 
# - default-jre : Requis par PySpark pour s'exécuter
# - libgl1-mesa-glx & libglib2.0-0 : Requis par OpenCV pour traiter les images
RUN apt-get update && apt-get install -y \
    default-jre \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Définition de la variable d'environnement pour Java (Indispensable pour Spark)
ENV JAVA_HOME=/usr/lib/jvm/default-java

# On crée le dossier de travail dans le conteneur
WORKDIR /app

# ==========================================
# 2. DÉPENDANCES PYTHON
# ==========================================
# On copie uniquement le requirements.txt en premier.
# Cela permet à Docker de "cacher" cette étape si tu modifies juste ton code Python.
COPY requirements.txt .

# Installation des paquets (sans garder le cache pour alléger l'image finale)
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# 3. COPIE DU CODE SOURCE
# ==========================================
# On copie l'intégralité du projet (backend, processors, bridge, common...)
COPY . .

# IMPORTANT : Il n'y a PAS de CMD ou ENTRYPOINT.
# C'est ton fichier docker-compose.app.yml qui décidera s'il lance FastAPI ou un script Spark.