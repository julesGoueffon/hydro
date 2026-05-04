📝 Spécifications Fonctionnelles - HydroStack (v1.0 & v2)

Ce document définit les fonctionnalités du système d'information (SI) de la serre hydroponique, regroupées par domaines d'action et en définissant les différents états du système.

1. Télémétrie & Acquisition (Data Ingestion)

Le système doit être capable de remonter, dater (timestamp) et stocker les métriques suivantes avec une haute fréquence (ex: 1 point / minute) :

Qualité de l'eau : pH, Électroconductivité (EC), Température de l'eau, Niveau d'eau global (en mm ou %).

Climat : Température de l'air, Hygrométrie, Luminosité (Lux/PAR).

Consommables : Niveaux estimés ou mesurés des cuves de nutriments et de pH+/pH-.

Statut des actionneurs (Feedback) : État des pompes (ON/OFF, volume estimé injecté), état des lampes, état des ventilateurs.

2. Contrôle & Automatisation (Edge & Backend Control)

Le système doit ajuster les actionneurs pour atteindre des valeurs cibles, en respectant des règles de sécurité strictes :

Cycle d'éclairage : Gestion ON/OFF et intensité (si LEDs dimmables) basée sur l'horloge et l'apport de lumière naturelle.

Régulation pH/EC (PID + Rate Limiting) : Injection de solutions correctrices avec un Delta Maximum autorisé par heure. L'objectif est d'atteindre la consigne de manière asymtotique pour éviter les chocs chimiques ou les dépassements (overshoot).

Régulation Climatique : Activation de l'extraction d'air ou du brassage en cas de dépassement des seuils de température ou d'humidité (gestion potentielle via le calcul du VPD - Vapor Pressure Deficit).

3. Gestion des Recettes & Cycle de Vie (State Machine)

L'intelligence centrale gère la croissance des plantes en suivant des profils prédéfinis :

Définition des Recettes : Création de "Crop Recipes" en base de données. Une recette est une série d'étapes (ex: Semis, Végétatif, Floraison) avec pour chacune des consignes spécifiques (pH cible, EC cible, heures de lumière/jour).

Évolution Temporelle : Le backend met à jour automatiquement les consignes envoyées à la serre en fonction du jour de croissance de la plante selon la recette active.

Interface de Configuration (v2) : Une interface utilisateur graphique (GUI) permettant de configurer manuellement le cycle de vie : sélection de la recette, saisie manuelle du type de plante, de son âge (jour 0), et forçage manuel des données si l'automatisation fait défaut.

4. Traitement Vidéo & Computer Vision

DVR Court Terme (Rolling Buffer) : Accès à un flux d'images haute fréquence couvrant les dernières 24 à 48 heures pour permettre un diagnostic visuel rapide en cas d'anomalie.

Timelapses Journaliers : Génération automatique (batch processing nocturne) d'une vidéo accélérée résumant la journée passée.

Détection de Stade et de Type (CV/ML) : Analyse des images pour identifier automatiquement le type de plante présente et détecter ses différents stades de maturité (apparition des premières vraies feuilles, floraison, fructification). Cette détection peut déclencher automatiquement la transition d'état de la recette.

5. Machine Learning & Prédictions Logistiques

Forecasting de Consommables : Prédire l'épuisement des cuves de nutriments et de régulateurs pH pour alerter l'utilisateur avant la rupture de stock, en se basant sur l'historique des injections.

Anticipation de Dérive : Prédire la dérive naturelle du pH de l'eau pour lisser et anticiper les micro-injections d'acide, au lieu de réagir passivement à un franchissement de seuil.

6. États du Système & Résilience (Modes de Fonctionnement)

Pour garantir la survie des plantes et la cohérence des données, l'Edge (ESP32) et le Backend doivent gérer différents états :

🟢 Mode NORMAL : Fonctionnement nominal. L'Edge communique avec le Backend, applique les consignes de la recette en cours, et régule activement le pH/EC et le climat.

🟡 Mode DÉGRADÉ (Offline / Perte de Comm) : * Déclencheur : Perte de connexion Wi-Fi, indisponibilité de Kafka ou de l'API pendant plus de 5 minutes.

Action : L'ESP32 bascule sur la dernière consigne journalière connue stockée en RAM/Flash. Il continue la régulation climatique et les cycles de lumière de manière autonome jusqu'à 24h. Les données télémétriques sont mises en cache localement si possible.

Alerte : Le Backend détecte le timeout de l'Edge et lève une alerte critique à l'utilisateur.

🟠 Mode SÉCURITÉ (Sensor Fault) :

Déclencheur : Lecture d'une valeur capteur physiquement impossible ou hors tolérance extrême (ex: pH = 1, Temp Eau = 40°C, niveau d'eau critique).

Action : Verrouillage immédiat (Lockout) des pompes doseuses. Maintien des fonctions vitales uniquement (oxygénation/brassage de l'eau).

Alerte : Envoi immédiat d'une notification critique. Une intervention humaine (acquittement) est requise pour sortir de ce mode.

🔵 Mode MAINTENANCE / CALIBRATION :

Déclencheur : Action manuelle de l'utilisateur (via un bouton physique sur la serre ou via l'interface logicielle).

Action : Suspension totale de la régulation chimique (pompes doseuses OFF).

Data : Un marqueur (flag) "Maintenance" est attaché aux données télémétriques envoyées. Le pipeline de données (Spark/Postgres) ignorera ces points aberrants (ex: sonde plongée dans une solution tampon pH 4.0) pour ne pas fausser les historiques et les modèles de Machine Learning.


6. États du Système & Résilience

Mode MAINTENANCE / CALIBRATION : Suspension de la régulation. L'utilisateur suit une procédure pour ajuster les coefficients slope et intercept des sondes.

ARRÊT D'URGENCE (E-Stop) : Commande prioritaire qui coupe tous les actionneurs. Le système nécessite un acquittement manuel pour redémarrer.

SYNCHRONISATION D'ÉTAT : Pour garantir la cohérence, l'Edge renvoie l'état de tous ses relais dans chaque Ping. Le Backend utilise cette donnée pour écraser son état local en cas de divergence.

7. Fonctionnalités Avancées 

OTA Updates : Capacité de l'ESP32 à télécharger son firmware depuis MinIO ou un serveur dédié.

Auto-Flushing : Routine permettant de vider le réservoir principal et de rincer les conduits de nutriments via des électrovannes dédiées.