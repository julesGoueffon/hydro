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
UPLOAD_INTERVAL = 900  # 15 minutes en secondes (mets 10 pour tester plus vite)


def send_fake_photo():
    """Simule l'envoi d'une photo JPEG par HTTP POST au backend"""
    while True:
        try:
            print("📸 Prise de vue en cours...")
            # On envoie du RAW binaire, pas un formulaire multipart !
            headers = {
                'X-Device-ID': DEVICE_ID,
                'Content-Type': 'image/jpeg'
            }

            # Utilisation de 'data=' au lieu de 'files=' pour simuler l'ESP32
            response = requests.post(API_URL, data=b'fake_jpeg_bytes_content', headers=headers)
            print(f"📤 Photo envoyée au Backend. Status: {response.status_code}")
        except Exception as e:
            # Cette erreur est normale tant que ton backend FastAPI n'est pas codé et lancé !
            print(f"⚠️ Erreur HTTP (Le backend FastAPI est-il allumé ?) : {e}")

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
    # 1. Initialisation MQTT
    client = mqtt.Client(DEVICE_ID)
    try:
        client.connect(BROKER, PORT, 60)
    except ConnectionRefusedError:
        print("Erreur: Le broker MQTT n'est pas joignable.")
        exit(1)

    client.loop_start()

    # 2. Lancement des tâches en parallèle (Threads)
    threading.Thread(target=ping_loop, args=(client,), daemon=True).start()
    threading.Thread(target=send_fake_photo, daemon=True).start()

    print(f"🚀 Mock Node Vision démarré. (Envoi d'une photo HTTP toutes les {UPLOAD_INTERVAL}s)")

    # 3. Maintien du script principal en vie
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt du mock.")
        client.loop_stop()
        client.disconnect()