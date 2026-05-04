🌿 HydroStack : Serre Hydroponique Autonome & Intelligente

📖 À propos du projet

HydroStack est un projet de serre hydroponique (système NFT - Nutrient Film Technique) entièrement autonome. L'objectif n'est pas seulement de faire pousser des plantes de manière optimale, mais de concevoir une architecture logicielle de classe industrielle (Big Data / MLOps) pour ingérer, traiter et agir sur les données de la serre en temps réel.

Ce projet sert de démonstrateur technique complet, allant de l'électronique embarquée jusqu'à l'inférence de modèles de Machine Learning, en passant par le traitement de flux de données distribués.

✨ Fonctionnalités Principales

📊 Télémétrie & Monitoring : Suivi en temps réel et historisation de toutes les métriques (pH, Électroconductivité (EC), Température air/eau, Humidité, Luminosité, Niveaux d'eau).

🤖 Contrôle en Temps Réel : Ajustement automatisé de l'environnement (pompes doseuses pour pH+/pH-/Nutriments, gestion de l'extracteur d'air, brassage, cycles lumineux).

📅 Recettes de Culture (Crop Recipes) : Moteur de séquençage permettant de définir des profils de croissance par étapes (ex: Tomate stade végétatif -> EC 1.2, 15h de lumière ; Tomate stade floraison -> EC 1.5, 13h de lumière). Le système fait évoluer les consignes automatiquement dans le temps.

🚨 Alerting & Sécurité : Remontée d'alertes critiques (température de l'eau critique, niveau de la cuve bas) avec mode de fonctionnement dégradé pour la survie des plantes.

👁️ Computer Vision : Prise de photos régulière, génération de timelapses de croissance, et évaluation de la santé de la biomasse par analyse d'image.

🧠 Machine Learning : Modèles prédictifs pour anticiper les variations de pH et optimiser l'injection de nutriments afin de maximiser le rendement.

🏗️ Architecture & Stack Technique

Le projet repose sur une architecture microservices conteneurisée, orientée événements.

🔌 Hardware & Edge

Microcontrôleur : ESP32 (C/C++) pour l'acquisition des capteurs et le pilotage des actionneurs (pompes, ventilateurs, LEDs).

Capteurs : pH, EC, Température, niveaux d'eau, Caméra (ESP32-CAM ou module USB).

📡 Ingestion & Middleware

MQTT : Protocole léger pour la transmission des données de l'ESP32 vers le backend.

Redpanda (Kafka) : Broker de messages haute performance pour distribuer les flux de télémétrie aux différents consommateurs.

⚙️ Backend, Traitement & Orchestration

FastAPI (Python) : API backend centrale. Elle gère la logique métier, la création des Crop Recipes, et interagit avec le système pour envoyer des commandes à l'Edge.

Apache Spark : Traitement distribué des données (batch et streaming) pour le nettoyage, l'agrégation et le calcul des métriques complexes.

Celery & Redis : Planification des tâches asynchrones (ex: déclenchement des prises de vue, routines de nettoyage, mise à jour quotidienne des consignes de la recette en cours).

🗄️ Persistance des Données

PostgreSQL : Base de données relationnelle pour le stockage des séries temporelles, des configurations, de l'état du système et des recettes de culture.

MinIO : Object storage (compatible S3) pour la sauvegarde des images brutes et des vidéos générées.

📈 Visualisation & MLOps

Grafana : Dashboards dynamiques pour la visualisation des métriques et des alertes.

MLflow : (Optionnel) Suivi du cycle de vie des modèles d'IA (tracking des expériences de prédiction du pH).

🚀 Déploiement

L'ensemble de l'infrastructure logicielle est définie via Docker Compose (ou Kubernetes en local) pour garantir une reproductibilité parfaite de l'environnement de développement à la production simulée.