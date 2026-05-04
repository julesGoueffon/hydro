🔌 Architecture Matérielle (Réseau d'ESP32)

Pour des raisons de fiabilité, de sécurité (séparation eau/électricité) et de limites matérielles (GPIO utilisables), le système est divisé en 3 Nœuds indépendants.

🛰️ Nœud 1 : "Brain & Climate" (Le Maître du Climat)

Rôle : Gérer l'environnement sec (Air) et la puissance électrique. C'est l'ESP principal. Il est placé loin de l'eau.
Matériel : ESP32 standard (ex: NodeMCU 32S).

Capteurs :

Température/Humidité Air (DHT22 ou BME280 via I2C).

Luminosité (BH1750 via I2C).

Actionneurs (Relais 220V / 12V Haute Puissance) :

Éclairage (LEDs de croissance).

Extracteur d'air.

Ventilateurs de brassage (Air).

💧 Nœud 2 : "Wet Node" (Le Maître de l'Eau)

Rôle : Acquisition des données physico-chimiques et gestion du pompage. Placé au plus près des cuves (dans un boîtier étanche IP65).
Matériel : ESP32 standard.
Note cruciale : L'ADC de l'ESP32 étant mauvais avec le Wi-Fi activé, un module externe ADS1115 (I2C) est obligatoire pour lire les sondes pH et EC proprement.

Capteurs :

Température Eau (DS18B20 - 1-Wire).

Module de conversion I2C vers Analogique (ADS1115) qui lit :

Sonde pH.

Sonde EC.

Niveau d'eau Cuve Principale (Flotteur digital basique ou Ultrasons).

Actionneurs (Relais 12V Basse Puissance) :

Pompe principale de circulation.

Pompe pH-.

Pompe pH+.

Pompes Nutriments (Tri 1, 2, 3).

Pompe de brassage interne.

👁️ Nœud 3 : "Vision Node"

Rôle : Observation visuelle.
Matériel : ESP32-CAM.

Périphérique : Caméra OV2640 (intégrée).

Actionneur : Flash LED (si nécessaire pour prise de vue nocturne).