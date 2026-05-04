📋 Board de Tâches - Version 2 (Dashboarding & Tâches Asynchrones)

Objectif de l'Épic : Rendre le système observable (monitoring avancé) et implémenter le traitement asynchrone pour les opérations lourdes (génération de vidéos) sans bloquer l'API principale.

🎟️ Ticket V2.1 : Intégration de Redis & Celery (Infra)

Description : Ajouter la brique d'exécution asynchrone à la stack. FastAPI ne doit jamais bloquer sur une tâche longue.
Tâches :

[ ] Ajouter le service redis dans le docker-compose.yml (servira de message broker pour Celery).

[ ] Ajouter un service worker dans le docker-compose.yml. Ce conteneur utilisera la même image Docker que le backend mais lancera la commande celery -A ton_app.worker worker --loglevel=info.

[ ] Installer la dépendance celery dans ton projet Python.

[ ] Créer une tâche Celery de test ping_task(delay: int) qui fait un time.sleep(delay) puis écrit dans les logs.
DoD : Le lancement complet de la stack démarre Redis et le worker Celery. Appeler un endpoint API POST /test-celery déclenche la tâche en arrière-plan sans faire patienter la réponse HTTP.

🎟️ Ticket V2.2 : Provisioning Grafana & Connexion BDD

Description : Déployer Grafana en tant que code (Infrastructure as Code) pour que tes dashboards soient versionnés sur GitHub.
Tâches :

[ ] Ajouter le service grafana dans le docker-compose.yml.

[ ] Configurer le Data Source Provisioning : Créer un fichier YAML pour que Grafana se connecte automatiquement à PostgreSQL au démarrage (sans configuration manuelle).

[ ] Créer un premier dashboard basique "Télémétrie brute" avec des requêtes SQL filtrant la table telemetry par metric (ex: SELECT time, value FROM telemetry WHERE metric = 'ph').
DoD : Au lancement de docker compose up, Grafana est accessible sur le port 3000, la base Postgres est déjà connectée, et un graphique affiche les fausses données générées par le Mock de la V1.

🎟️ Ticket V2.3 : Tableaux de bord "Indus" (State Timeline & Gauges)

Description : Aller plus loin que de simples courbes pour afficher l'état réel de la machine.
Tâches :

[ ] Ajouter des "Gauges" (Jauges) pour le niveau des cuves et le pH actuel avec des seuils de couleur (Vert = OK, Rouge = Danger).

[ ] Utiliser le panel "State Timeline" de Grafana branché sur la table actuator_logs pour visualiser exactement quand et combien de temps les pompes se sont allumées par rapport aux variations de pH/EC.

[ ] Créer un panel "Alerts" basé sur la table system_events.
DoD : Le dashboard a une allure de centre de contrôle industriel permettant de corréler l'action d'une pompe avec la variation d'une courbe.

🎟️ Ticket V2.4 : Le Proxy Média (FastAPI)

Description : Grafana ne peut pas lire directement dans MinIO de façon sécurisée et dynamique sans bidouillage. On va passer par l'API.
Tâches :

[ ] Créer une route FastAPI GET /api/v1/media/latest/image qui interroge la table media_metadata pour trouver la dernière photo prise.

[ ] Le backend va chercher cette image dans MinIO et la renvoie en format binaire (StreamingResponse en Python).

[ ] Dans Grafana, utiliser le plugin "Dynamic Text" ou "HTML" pour afficher cette image (avec un auto-refresh toutes les minutes).
DoD : Le dashboard Grafana affiche fièrement la dernière photo prise par le Mock Caméra.

🎟️ Ticket V2.5 : Le Worker Vidéo (Génération de Timelapse)

Description : C'est la tâche lourde. Créer une vidéo à partir des centaines de photos de la journée.
Tâches :

[ ] Créer une tâche Celery generate_daily_timelapse(session_id, date).

[ ] Configurer Celery Beat (le cron de Celery) pour déclencher cette tâche tous les jours à 00h01.

[ ] Logique de la tâche :

Récupérer dans media_metadata toutes les photos de la journée passée.

Télécharger ces images depuis MinIO dans un dossier temporaire.

Utiliser opencv-python ou un appel système à ffmpeg pour compiler ces images en un fichier .mp4 (ex: 30 fps).

Uploader le .mp4 sur MinIO.

Insérer une nouvelle ligne dans media_metadata (type: TIMELAPSE_VIDEO).

Nettoyer le dossier temporaire.
DoD : En lançant la tâche manuellement, un fichier .mp4 est généré, stocké sur S3, enregistré en BDD, et lisible.