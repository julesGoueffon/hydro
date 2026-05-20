# 🌿 HydroStack : Serre Hydroponique Autonome & Intelligente

## 📖 À propos du projet

HydroStack est un projet de serre hydroponique (systèmes NFT et RDWC) entièrement autonome. L'objectif n'est pas seulement de faire pousser des plantes de manière optimale, mais de concevoir une architecture logicielle de classe industrielle (Edge to Web) pour ingérer, traiter et agir sur les données de la serre en temps réel.

Ce projet sert de démonstrateur technique complet, alliant une conception matérielle sur-mesure (conteneurs hydroponiques en béton moulé, prototypage 3D) à une infrastructure logicielle asynchrone ultra-légère. Développé nativement sous environnement Linux, le système se passe des usines à gaz Big Data traditionnelles au profit d'une stack "Zéro Graisse" garantissant une fiabilité et une faible latence sur du matériel embarqué (Raspberry Pi).

## ✨ Fonctionnalités Principales

* 📊 **Télémétrie & Monitoring :** Suivi en temps réel et historisation de toutes les métriques (pH, Électroconductivité (EC), Température air/eau, Humidité).
* 🤖 **Contrôle en Temps Réel :** Ajustement automatisé de l'environnement via un moteur asynchrone (pompes doseuses pour pH+/pH-/Nutriments, brassage continu).
* 📅 **Recettes de Culture (Crop Recipes) :** Moteur de séquençage permettant de définir des profils de croissance par étapes (ex: Tomate stade végétatif -> EC 1.2 ; Tomate stade floraison -> EC 1.5). Le système fait évoluer les consignes automatiquement.
* 🚨 **Alerting & Sécurité :** Remontée d'alertes critiques (température de l'eau, dérive de l'EC) et forçage manuel (Arrêt d'urgence) via une interface unifiée.
* 👁️ **Computer Vision :** Prise de photos régulière via ESP32-CAM, évaluation du score de flou par OpenCV, et génération d'un flux de supervision visuel.
* 🧠 **Machine Learning :** Modèles prédictifs pour anticiper les variations de pH et optimiser l'injection de nutriments afin de maximiser le rendement.

## 🏗️ Architecture & Stack Technique

Le projet repose sur une architecture microservices conteneurisée, découpée logiquement entre l'infrastructure de base et les applications métier.

### 🔌 Hardware & Edge
* **Microcontrôleur :** ESP32 (C/C++) pour l'acquisition des capteurs et le pilotage des actionneurs.
* **Capteurs & Actionneurs :** Sondes pH/EC industrielles, capteurs de température, pompes péristaltiques et module caméra ESP32-CAM.
* **Structure physique :** Conception modulaire incluant des pots en béton (Jesmonite) coulés sur-mesure pour une intégration optimisée.

### 📡 Ingestion & Middleware
* **Mosquitto (MQTT) :** Broker de messages léger et robuste pour la transmission bidirectionnelle ultra-rapide entre l'ESP32 et le serveur.

### ⚙️ Backend, Traitement & Orchestration
* **Python Worker (MQTT -> DB) :** Micro-service d'ingestion direct dédié à la lecture du broker MQTT et à l'écriture des séries temporelles.
* **FastAPI (Python) :** API REST centrale. Elle gère la configuration, réceptionne les images de l'Edge et sert les données au client web.
* **Celery & Redis :** Le cerveau asynchrone du système. Planification des tâches (traitement OpenCV en arrière-plan) et exécution de la boucle de régulation des nutriments (Beat/Worker).

### 🗄️ Persistance des Données
* **PostgreSQL :** Base de données relationnelle pour le stockage des séries temporelles (télémétrie), des configurations et de l'état du système.
* **MinIO :** Object storage (compatible S3) pour la sauvegarde des images brutes et des médias générés par l'Edge.

### 📈 Visualisation & Contrôle (IHM Industrielle)
* **React + Vite + TypeScript :** Application web frontend (Single Page Application) faisant office de panneau de contrôle SCADA.
* **Tailwind CSS & Recharts :** Design system industriel intégrant des jauges de tolérance linéaires, des matrices d'activité temporelles (Heatmaps) et des graphiques interactifs.

### 🚀 Déploiement
L'ensemble de l'infrastructure est défini de manière modulaire via Docker Compose pour une empreinte RAM minimale sur des architectures ARM (ex: Raspberry Pi 4).
* `docker-compose.infra.yml` : Gère les fondations (Postgres, Mosquitto, Redis, MinIO).
* `docker-compose.app.yml` : Gère le code métier (FastAPI, Celery, MQTT Worker).