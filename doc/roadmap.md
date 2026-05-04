🗺️ Roadmap & Scopes de Versions - HydroStack

Ce document définit les étapes de développement du projet, avec une approche linéaire "Walking Skeleton" : on construit d'abord l'infrastructure complète avec des données simulées, puis on ajoute la logique métier de manière incrémentale.

🎯 Version 0 : Le Squelette Infra (Walking Skeleton)

Objectif : Déployer la stack technologique complète en local et prouver que la donnée circule de bout en bout, de manière basique.

Infra (Docker Compose) : Mise en place de MQTT, Redpanda (Kafka), PostgreSQL, MinIO, FastAPI (vide).

Flux de données : * Un script Python très simple envoie un message MQTT "ping".

Kafka le route.

FastAPI le lit, écrit dans Postgres, et renvoie un ordre MQTT "pong".

Succès = Le tuyau n'a pas de fuite.

🚀 Version 1 : Les Mocks & La Boucle de Contrôle (Asservissement)

Objectif : Simuler l'ensemble du matériel et implémenter la logique de régulation de base (maintien des constantes vitales).

Edge (Mocking) : Création des 3 scripts de simulation :

Mock Capteurs : Publie des JSON de télémétrie (pH, EC, Temp) avec un bruit réaliste.

Mock Actionneurs : Écoute les ordres MQTT et met à jour les variables du Mock Capteurs (ex: si ordre "pompe pH-", le pH simulé baisse).

Mock Caméra : Envoie des images de test vers l'API.

Backend : * Définition finale des schémas de base de données (Postgres).

Implémentation de la logique de contrôle basique (ex: Si pH > Seuil, envoi d'un ordre d'activation pompe de 2s toutes les 15 minutes jusqu'au retour à la normale).

📊 Version 2 : Dashboarding & Tâches Asynchrones

Objectif : Rendre le système observable et gérer les opérations lourdes hors du thread principal.

UI / Observabilité : Création d'un Grafana "Indus" complet connecté à Postgres (courbes, jauges, statuts des actionneurs).

Data Processing : * Intégration de Celery & Redis.

Création du "Worker Vidéo" : une tâche Celery télécharge les images du jour depuis MinIO, compile un timelapse (via OpenCV/FFmpeg) et le restocke.

🛡️ Version 3 : Résilience & Gestion des États

Objectif : Rendre l'architecture robuste face aux pannes et permettre les opérations de maintenance.

Backend : Implémentation du système de "Heartbeat" (ping).

Logique Métier : Développement des modes opératoires :

Mode Sécurité : Déclenchement si métriques aberrantes -> Verrouillage des pompes.

Mode Maintenance : Interface API pour suspendre l'asservissement pendant la calibration.

Mode Dégradé (Simulé) : Le backend détecte si le Mock Capteurs s'arrête de publier et lève une alerte.

📋 Version 4 : Sûreté & Maintenance

Objectif : Gestion du cycle de vie et interface utilisateur complète.

Moteur de "Crop Recipes" (State Machine).

UI (React/Vue/Streamlit) pour piloter les recettes.

🧠 Version 5 : Machine Learning & MLOps

Objectif : Ajouter la couche d'intelligence artificielle pour l'anticipation et l'analyse.

MLOps : Déploiement de MLflow.

Forecasting : Modèle prédictif (ex: Prophet ou XGBoost) entraîné sur les données historiques Postgres pour prédire la consommation des cuves de pH/Nutriments.

Computer Vision : Analyse des images MinIO pour détecter le stade de développement de la plante (apparition des fleurs).

🔐 Version 6 : Advanced & Indus (Final Polish)

Objectif : Durcissement et fonctionnalités avancées.

OTA (Over-The-Air) : Mise à jour du firmware à distance.

Flushing : Procédure de vidange et rinçage automatique.

Sécurité (E) : TLS, JWT, et isolation des réseaux.