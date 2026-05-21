import paho.mqtt.client as mqtt
import json
import time
import threading
import requests

# Configuration
BROKER = "127.0.0.1"
PORT = 1883
DEVICE_ID = "mock_node3_vision"
API_URL = "http://127.0.0.1:8000/api/v1/camera/upload"

# Passe à 10 secondes le temps de faire tes tests !
UPLOAD_INTERVAL = 10


def send_fake_photo():
    """Simule l'envoi d'une vraie photo JPEG par HTTP POST au backend"""
    while True:
        try:
            print("📸 Prise de vue en cours...")

            # 1. On génère une vraie image aléatoire (simule le capteur de la caméra)
            # Le timestamp force le serveur à nous donner une image différente à chaque fois
            dummy_image_url = f"https://picsum.photos/600/400?random={int(time.time())}"
            img_response = requests.get(dummy_image_url, timeout=5)

            if img_response.status_code == 200:
                jpeg_bytes = img_response.content

                # 2. On pousse les octets bruts vers ton API FastAPI
                headers = {
                    'X-Device-ID': DEVICE_ID,
                    'Content-Type': 'image/jpeg'
                }

                response = requests.post(API_URL, data=jpeg_bytes, headers=headers)
                print(f"📤 Photo envoyée au Backend. Status: {response.status_code}")
            else:
                print("⚠️ Impossible de simuler l'image.")

        except Exception as e:
            print(f"⚠️ Erreur HTTP : {e}")

        time.sleep(UPLOAD_INTERVAL)


def ping_loop(client):
    """Envoie le signal de vie (Heartbeat) toutes les secondes via MQTT"""
    uptime = 0
    while True:
        payload = {
            "device_id": DEVICE_ID,
            "uptime_s": uptime,
            "status": "READY"
        }
        client.publish("hydro/node3/status", json.dumps(payload))
        uptime += 1
        time.sleep(1)


if __name__ == "__main__":
    # Initialisation compatible Paho-MQTT v2
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
    except AttributeError:
        client = mqtt.Client(client_id=DEVICE_ID)

    try:
        client.connect(BROKER, PORT, 60)
    except ConnectionRefusedError:
        print("Erreur: Le broker MQTT n'est pas joignable.")
        exit(1)

    client.loop_start()

    threading.Thread(target=ping_loop, args=(client,), daemon=True).start()
    threading.Thread(target=send_fake_photo, daemon=True).start()

    print(f"🚀 Mock Node Vision démarré. (Envoi d'une photo HTTP toutes les {UPLOAD_INTERVAL}s)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt du mock.")
        client.loop_stop()
        client.disconnect()