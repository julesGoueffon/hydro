📋 Board de Tâches - Version 0 (Walking Skeleton)

Objectif de l'Épic : Déployer l'infrastructure locale complète et valider que la donnée transite d'un bout à l'autre (Edge simulé -> MQTT -> Kafka -> Backend -> BDD -> MQTT -> Edge).
Aucune logique métier complexe n'est attendue ici.

🎟️ Ticket V0.1 : Initialisation de l'Infrastructure Docker

Description : Créer le dépôt Git du projet et configurer le fichier d'orchestration global qui fera tourner tous les services d'infrastructure en local.
Tâches (Checklist) :

[ ] Initialiser un repo Git (hydrostack).

[ ] Créer le fichier docker-compose.yml à la racine.

[ ] Ajouter le service PostgreSQL (avec variables d'environnement pour User, Password, DB hydrodb).

[ ] Ajouter le service MinIO (avec console web activée et identifiants par défaut).

[ ] Ajouter le service Redpanda (Kafka-compatible) avec son interface web (Redpanda Console).

[ ] Ajouter le service Eclipse Mosquitto (Broker MQTT) avec un fichier mosquitto.conf basique (autorisant les connexions anonymes pour le dev local).
Definition of Done (DoD) : La commande docker compose up -d démarre tous les conteneurs sans erreur. Les interfaces web (MinIO et Redpanda Console) sont accessibles via le navigateur.

🎟️ Ticket V0.2 : Setup du Backend FastAPI (Base)

Description : Créer le squelette de l'API Python qui servira de cerveau au système.
Tâches :

[ ] Créer un dossier backend/ avec un environnement virtuel Python (Poetry ou pip).

[ ] Installer les dépendances : fastapi, uvicorn, sqlalchemy, psycopg2-binary (ou asyncpg), confluent-kafka (ou aiokafka), paho-mqtt.

[ ] Créer le point d'entrée main.py avec une simple route GET /health renvoyant {"status": "ok"}.

[ ] Créer la connexion à la base de données PostgreSQL via SQLAlchemy.

[ ] Créer une table basique events en BDD (colonnes : id, timestamp, message).
DoD : L'API démarre, la route /health répond 200 OK, et la table events est bien créée dans Postgres au démarrage.

🎟️ Ticket V0.3 : Le Bridge MQTT -> Kafka (Ingestion)

Description : Les ESP (et nos futurs mocks) parlent en MQTT (léger). Le backend, lui, préfère consommer Kafka (robuste, distribué). Il faut lier les deux.
Note : On peut utiliser un connecteur tout fait, mais pour apprendre, un petit script Python est idéal.
Tâches :

[ ] Créer un script (ou un module dans le backend) mqtt_kafka_bridge.py.

[ ] Le script se connecte au broker Mosquitto et s'abonne au topic hydro/+/telemetry.

[ ] À chaque message MQTT reçu, le script le transfère (produit) vers un topic Kafka nommé telemetry_stream sur Redpanda.
DoD : Si on publie manuellement un message sur Mosquitto, on le voit apparaître dans la console web de Redpanda sur le topic telemetry_stream.

🎟️ Ticket V0.4 : Consommation Kafka & Écriture BDD (Backend)

Description : Le backend doit écouter Kafka, traiter la donnée et la sauvegarder.
Tâches :

[ ] Ajouter un Consumer Kafka dans le backend FastAPI qui écoute le topic telemetry_stream.

[ ] Configurer ce consumer pour qu'il tourne en tâche de fond au démarrage de l'API (via les lifespan events de FastAPI ou asyncio.create_task).

[ ] À chaque message reçu de Kafka (ex: {"action": "ping"}), écrire une nouvelle ligne dans la table Postgres events.
DoD : Un message dans le topic Kafka crée automatiquement une nouvelle entrée dans la base de données PostgreSQL.

🎟️ Ticket V0.5 : La boucle retour (Le "Pong")

Description : Le backend doit prouver qu'il peut envoyer un ordre vers l'Edge après avoir traité une donnée.
Tâches :

[ ] Modifier la logique du Consumer Kafka (Ticket V0.4) : Juste après avoir sauvegardé le "ping" en BDD, le backend se connecte à Mosquitto (MQTT).

[ ] Le backend publie un message {"action": "pong", "status": "saved"} sur le topic MQTT hydro/serre1/commands.
DoD : Le pipeline complet Backend -> Edge fonctionne.

🎟️ Ticket V0.6 : Le script "Edge" final (Le Testeur)

Description : Créer le script Python ultra-basique qui simule notre futur ESP32 pour cette phase de test de tuyauterie.
Tâches :

[ ] Créer un script edge_v0.py.

[ ] S'abonner au topic MQTT hydro/serre1/commands pour écouter les réponses du backend.

[ ] Publier un message JSON {"action": "ping", "timestamp": "..."} sur le topic hydro/serre1/telemetry.

[ ] Afficher un log triomphant ("PONG REÇU !") lorsque la boucle est bouclée.
DoD : En lançant edge_v0.py, le message part, traverse MQTT, Kafka, le Backend, la BDD, et revient via MQTT jusqu'au script en moins d'une seconde. Le Walking Skeleton est terminé ! 🎉