import paho.mqtt.client as mqtt
import json
import time
import random
import threading

# Configuration
BROKER = "127.0.0.1"
PORT = 1883
DEVICE_ID = "mock_node1_brain"

# Variables d'état (Simulation physique)
state = {
    "air_temp": 24.0,
    "humidity": 60.0,
    "lux": 400.0,  # Base de lumière
    "louvers_position": 0,  # Moteur pas-à-pas: de 0% (fermé) à 100% (ouvert)
    "mode": "NORMAL",
    "relays": {
        "light_grow": "OFF",
        "fan_extractor": "OFF",
        "fan_stirring": "OFF"
    }
}


# --- CALLBACKS MQTT ---

def on_connect(client, userdata, flags, rc):
    print(f"Connecté au broker MQTT avec le code {rc}")
    client.subscribe("hydro/node1/commands")


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    action = payload.get("action")
    target = payload.get("target")
    cmd_id = payload.get("cmd_id")

    # 1. Gestion des Relais classiques (ON/OFF)
    if action == "SET_STATE" and target in state["relays"]:
        new_state = payload.get("state")
        state["relays"][target] = new_state
        print(f"⚙️ [{target}] mis sur {new_state} (Cmd ID: {cmd_id})")

        # Envoi de l'Acquittement (ACK)
        ack = {
            "cmd_id": cmd_id,
            "status": "COMPLETED",
            "actuator": target,
            "new_state": new_state
        }
        client.publish("hydro/node1/acks", json.dumps(ack))

    # 2. Gestion du Moteur Pas-à-Pas (Persiennes)
    elif action == "SET_POSITION" and target == "stepper_louvers":
        position = payload.get("position", 0)
        # Sécurité : on borne entre 0 et 100%
        state["louvers_position"] = max(0, min(100, position))
        print(f"🪟 [stepper_louvers] Persiennes ajustées à {state['louvers_position']}%")

        ack = {
            "cmd_id": cmd_id,
            "status": "COMPLETED",
            "actuator": target,
            "position": state["louvers_position"]
        }
        client.publish("hydro/node1/acks", json.dumps(ack))


# --- BOUCLES DE PUBLICATION ---

def telemetry_loop(client):
    """Envoie les valeurs de télémétrie toutes les 10 secondes"""
    while True:
        # Simulation d'une physique dynamique

        # 1. Impact de la lumière (LED + Persiennes)
        base_lux = 400.0
        led_lux = 15000.0 if state["relays"]["light_grow"] == "ON" else 0.0
        sun_lux = 30000.0 * (state["louvers_position"] / 100.0)  # Le soleil tape fort si ouvert
        state["lux"] = base_lux + led_lux + sun_lux

        # 2. Impact Thermique (Lumière chauffe, Extracteur refroidit)
        if state["relays"]["light_grow"] == "ON" or state["louvers_position"] > 50:
            state["air_temp"] += 0.05

        if state["relays"]["fan_extractor"] == "ON":
            state["air_temp"] -= 0.1 if state["air_temp"] > 22.0 else 0
            state["humidity"] -= 0.5 if state["humidity"] > 45.0 else 0
        else:
            state["humidity"] += 0.1  # La plante transpire

        # Ajout d'un bruit réaliste pour les capteurs
        temp = state["air_temp"] + random.uniform(-0.1, 0.1)
        hum = state["humidity"] + random.uniform(-0.5, 0.5)
        lux_val = state["lux"] + random.uniform(-10, 10)

        # Envoi séquentiel
        metrics = [("air_temp", temp), ("humidity", hum), ("lux", lux_val)]

        for metric, value in metrics:
            payload = {
                "device_id": DEVICE_ID,
                "metric": metric,
                "value": round(value, 2)
            }
            client.publish("hydro/node1/telemetry", json.dumps(payload))
            time.sleep(0.1)  # Évite d'inonder le broker

        time.sleep(10)


def ping_loop(client):
    """Envoie l'état complet toutes les secondes"""
    uptime = 0
    while True:
        payload = {
            "device_id": DEVICE_ID,
            "uptime_s": uptime,
            "mode": state["mode"],
            "louvers_position": state["louvers_position"],
            "relays": state["relays"]
        }
        client.publish("hydro/node1/status", json.dumps(payload))
        uptime += 1
        time.sleep(1)


# --- DÉMARRAGE ---

if __name__ == "__main__":
    client = mqtt.Client(DEVICE_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, 60)
    except ConnectionRefusedError:
        print("Erreur: Le broker MQTT n'est pas joignable.")
        exit(1)

    client.loop_start()

    t_telemetry = threading.Thread(target=telemetry_loop, args=(client,), daemon=True)
    t_ping = threading.Thread(target=ping_loop, args=(client,), daemon=True)

    t_telemetry.start()
    t_ping.start()

    print("🚀 Mock Node Climat démarré (avec gestion des persiennes Nema 17).")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt du mock.")
        client.loop_stop()
        client.disconnect()