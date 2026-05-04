📋 Board de Tâches - Version 1 (Mocks & Contrôle)

Objectif de l'Épic : Remplacer le "ping/pong" de la V0 par de vraies données (simulées) et implémenter la logique métier d'asservissement (réagir à une baisse de pH, allumer la lumière, etc.).

🎟️ Ticket V1.1 : Modélisation de la Base de Données (Postgres)

Description : Remplacer la table events basique de la V0 par le schéma relationnel final (ou presque) via SQLAlchemy (ou Alembic pour les migrations).
Tâches :

[ ] Créer la table telemetry (id, timestamp, ph, ec, water_temp, air_temp, humidity, water_level).

[ ] Créer la table actuator_logs (id, timestamp, actuator_name, action, duration_ms) pour garder un historique des pompages.

[ ] Créer la table system_state (id, timestamp, mode) pour stocker l'état actuel (Normal, Maintenance...).
DoD : Les tables sont créées automatiquement au lancement de FastAPI, prêtes à recevoir des données structurées.

🎟️ Ticket V1.2 : Développement du "Digital Twin" (Mocks ESP32)

Description : Créer un script Python robuste qui simule le comportement physique de la serre. C'est lui qui publiera sur MQTT.
Tâches :

[ ] Créer un script mock_serre.py.

[ ] Implémenter une boucle (ex: toutes les 10s) qui génère des valeurs réalistes : pH autour de 6.0 avec une lente dérive vers le haut, température qui monte le jour et baisse la nuit. Ajouter un bruit gaussien (random.gauss) pour le réalisme.

[ ] Mettre en place un callback MQTT qui écoute les ordres du backend. Exemple : si le mock reçoit l'ordre "allumer pompe pH- 3 secondes", la variable interne de pH du mock chute de 0.2 d'un coup.
DoD : Le script tourne en continu et publie des JSON complets sur Kafka (via le bridge de la V0). Quand on lui envoie une commande manuelle MQTT, ses futures mesures sont impactées.

🎟️ Ticket V1.3 : La Boucle de Contrôle (Backend Logic)

Description : Le cerveau de l'opération. L'API analyse les métriques entrantes et décide des actions.
Tâches :

[ ] Créer un "Control Manager" dans FastAPI.

[ ] Implémenter la logique de Rate Limiting (ex: "Ne pas autoriser plus de 5 secondes de pompe pH- par heure" pour éviter les chocs).

[ ] Écrire la logique d'asservissement : SI pH_actuel > pH_cible + marge ALORS publier commande MQTT (Pompe pH-, 2000ms) ET enregistrer dans actuator_logs.
DoD : Lorsqu'on lance le mock_serre.py avec un pH de départ à 7.5, on voit dans les logs du backend qu'il envoie des ordres de pompe, et le mock réagit jusqu'à ce que le pH se stabilise autour de 6.0.

🎟️ Ticket V1.4 : Tests Automatisés (Pytest) - Le Flex GitHub

Description : Prouver que la boucle de contrôle de la V1.3 est fiable et sécurisée.
Tâches :

[ ] Installer pytest dans l'environnement backend.

[ ] Écrire un test qui vérifie que le Rate Limiting fonctionne (le système refuse une commande si la limite horaire est atteinte).

[ ] Écrire un test qui vérifie que le système ne fait rien si le capteur renvoie une valeur aberrante (ex: pH = -2).

[ ] (Optionnel) Ajouter une GitHub Action pour lancer ces tests à chaque git push.
DoD : La commande pytest passe au vert (100% de succès) sur les règles métier de sécurité.

🎟️ Ticket V1.5 : Mock de l'ESP32-CAM & MinIO

Description : Simuler la caméra pour valider l'upload HTTP multipart et le stockage objet S3.
Tâches :

[ ] Créer un endpoint FastAPI POST /api/v1/camera/upload qui accepte un fichier image.

[ ] Configurer le client MinIO dans FastAPI (Boto3 ou client MinIO) pour stocker cette image dans un bucket hydro-images.

[ ] Créer un petit script Python mock_camera.py qui prend une image JPEG aléatoire sur ton disque dur et fait un POST HTTP vers ton API toutes les X minutes.
DoD : On voit les images s'empiler proprement dans l'interface web de MinIO.

🎟️ Ticket V1.6 : Le "Hello World" Hardware (Facultatif mais satisfaisant)

Description : Valider que la stack fonctionne aussi avec une vraie puce.
Tâches :

[ ] Brancher un ESP32 en USB, installer VS Code + PlatformIO.

[ ] Écrire un code C++ basique qui se connecte au Wi-Fi.

[ ] Utiliser la librairie PubSubClient pour publier un "Hello from real ESP32" sur ton broker MQTT local.
DoD : Le message apparaît dans la base de données Postgres, prouvant que le hardware physique peut remplacer le Mock à tout moment.