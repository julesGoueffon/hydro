import paho.mqtt.client as mqtt
from confluent_kafka import Producer
import json
import time

# --- CONFIGURATION ---
MQTT_PORT = 1883

MQTT_BROKER = "mosquitto"
KAFKA_BROKER = "redpanda:9092"

# --- INITIALISATION KAFKA PRODUCER ---
kafka_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'client.id': 'mqtt-bridge'
}
producer = Producer(kafka_conf)


def delivery_report(err, msg):
    """Callback de confirmation d'envoi Kafka"""
    if err is not None:
        print(f"❌ Échec de l'envoi Kafka: {err}")


# --- CALLBACKS MQTT ---
def on_connect(client, userdata, flags, rc):
    print(f"✅ Connecté à Mosquitto MQTT (Code {rc})")
    # On s'abonne à tous les topics de télémétrie et d'acquittement de tous les nœuds
    client.subscribe("hydro/+/telemetry")
    client.subscribe("hydro/+/acks")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode('utf-8')

    print(f"📥 Message MQTT Reçu sur {topic} : {payload_str}")

    # Routage intelligent : selon le topic MQTT, on envoie dans le bon topic Kafka
    try:
        if "telemetry" in topic:
            producer.produce('telemetry_stream', payload_str.encode('utf-8'), callback=delivery_report)
        elif "acks" in topic:
            producer.produce('actuator_stream', payload_str.encode('utf-8'), callback=delivery_report)

        # On force l'envoi vers Kafka
        producer.poll(0)
    except Exception as e:
        print(f"⚠️ Erreur lors du pontage vers Kafka : {e}")


# --- DÉMARRAGE ---
if __name__ == "__main__":
    print("🌉 Démarrage du Bridge MQTT -> Kafka...")

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="bridge_service")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except ConnectionRefusedError:
            print("⏳ En attente de Mosquitto...")
            time.sleep(2)

    try:
        # Boucle infinie pour écouter MQTT
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("🛑 Arrêt du Bridge.")
        producer.flush()  # S'assure que les derniers messages sont bien envoyés à Kafka
        mqtt_client.disconnect()