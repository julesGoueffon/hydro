import time
import json
import threading
import paho.mqtt.client as mqtt
from confluent_kafka import Producer, Consumer, KafkaError
from common.config import AppConfig

# --- CONFIGURATION MQTT ---
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883

# --- INITIALISATION KAFKA PRODUCER (Flux Ascendant) ---
producer_conf = {
    'bootstrap.servers': AppConfig.KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'mqtt-bridge-producer'
}
producer = Producer(producer_conf)


def delivery_report(err, msg):
    """Callback de confirmation d'envoi Kafka"""
    if err is not None:
        print(f"❌ Échec de l'envoi Kafka: {err}")


# --- CALLBACKS MQTT (MQTT -> KAFKA) ---
def on_connect(client, userdata, flags, rc):
    print(f"✅ Connecté à Mosquitto MQTT (Code {rc})")
    # On s'abonne à tous les topics de télémétrie et d'acquittement
    client.subscribe("hydro/+/telemetry")
    client.subscribe("hydro/+/acks")


def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode('utf-8')

    try:
        if "telemetry" in topic:
            producer.produce('telemetry_stream', payload_str.encode('utf-8'), callback=delivery_report)
        elif "acks" in topic:
            producer.produce('actuator_stream', payload_str.encode('utf-8'), callback=delivery_report)
        producer.poll(0)
    except Exception as e:
        print(f"⚠️ Erreur lors du pontage vers Kafka : {e}")


# --- WORKER KAFKA -> MQTT (Flux Descendant) ---
def kafka_to_mqtt_worker(mqtt_client):
    """Consomme Kafka et publie vers MQTT"""
    print("🌉 Bridge Descendant démarré (Kafka -> MQTT)")

    consumer_conf = {
        'bootstrap.servers': AppConfig.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'mqtt_gateway_group',
        'auto.offset.reset': 'latest'  # On ne veut que les nouveaux ordres
    }
    consumer = Consumer(consumer_conf)
    consumer.subscribe(["command_stream"])

    while True:
        msg = consumer.poll(1.0)  # Attend un message pendant 1 seconde
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"❌ Erreur Consumer Kafka : {msg.error()}")
                break

        try:
            # Traitement du message reçu depuis Kafka
            payload = json.loads(msg.value().decode('utf-8'))
            device_id = payload.get("device_id")

            if device_id:
                # Extraction "mock_node2_wet" -> "node2"
                node_id = device_id.split('_')[1]
                topic = f"hydro/{node_id}/commands"

                cmd_payload = {
                    "action": payload.get("action"),
                    "cmd_id": payload.get("cmd_id"),
                    "target": payload.get("target"),
                    "duration_ms": payload.get("duration_ms")
                }

                mqtt_client.publish(topic, json.dumps(cmd_payload))
                print(f"📩 BRIDGE FORWARD : Commande envoyée sur MQTT ({topic})")
        except Exception as e:
            print(f"⚠️ Erreur lors du pontage vers MQTT : {e}")


# --- DÉMARRAGE ---
if __name__ == "__main__":
    print("🚀 Démarrage du Bridge Bidirectionnel (MQTT <-> Kafka)...")

    # Initialisation du client MQTT global
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="bridge_service")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    # Boucle de connexion à Mosquitto
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except ConnectionRefusedError:
            print("⏳ En attente de Mosquitto...")
            time.sleep(2)

    # Lancement du flux descendant dans un thread séparé
    threading.Thread(target=kafka_to_mqtt_worker, args=(mqtt_client,), daemon=True).start()

    try:
        # Lancement du flux ascendant (bloquant)
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("🛑 Arrêt du Bridge.")
        producer.flush()
        mqtt_client.disconnect()