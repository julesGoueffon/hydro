import paho.mqtt.client as mqtt
import json
import time
import random
import threading

# Configuration
BROKER = "127.0.0.1"
PORT = 1883
DEVICE_ID = "mock_node2_wet"

# Variables d'état (Simulation physique)
state = {
    "ph": 6.8,
    "ec": 0.8,  # EC de départ (eau claire)
    "water_temp": 22.0,
    "mode": "NORMAL",
    "relays": {
        "pump_ph_minus": "OFF",
        "pump_ph_plus": "OFF",
        "pump_nutri_1": "OFF",
        "pump_nutri_2": "OFF",
        "pump_nutri_3": "OFF"
    }
}


def execute_pump(cmd_id, target, duration_ms, client):
    start_time = time.time()
    print(f"[{target}] Démarrage pour {duration_ms}ms (Cmd ID: {cmd_id})")
    state["relays"][target] = "ON"

    # 1. Envoi de l'événement de DÉBUT
    start_event = {
        "cmd_id": cmd_id,
        "status": "STARTED",
        "actuator": target,
        "expected_duration_ms": duration_ms
    }
    client.publish("hydro/node2/acks", json.dumps(start_event))

    # Pause non-bloquante pour le thread courant
    time.sleep(duration_ms / 1000.0)

    state["relays"][target] = "OFF"

    # Calcul du temps réel passé (pour vérifier que le sleep a été précis)
    actual_duration_ms = int((time.time() - start_time) * 1000)
    print(f"[{target}] Arrêt. Temps réel écoulé: {actual_duration_ms}ms")

    # Simulation Physique
    seconds = duration_ms / 1000.0
    if target == "pump_ph_minus":
        state["ph"] -= seconds * 0.1
        print(f"🧪 Le pH a chuté (Nouveau pH: {state['ph']:.2f})")
    elif target == "pump_ph_plus":
        state["ph"] += seconds * 0.1
        print(f"🧪 Le pH a monté (Nouveau pH: {state['ph']:.2f})")
    elif "pump_nutri" in target:
        # L'ajout d'engrais fait monter l'Electroconductivité (EC)
        state["ec"] += seconds * 0.05
        print(f"🌿 L'EC a augmenté (Nouvelle EC: {state['ec']:.2f} mS/cm)")

    # 2. Envoi de l'événement de FIN (Acquittement final)
    end_event = {
        "cmd_id": cmd_id,
        "status": "COMPLETED",
        "actuator": target,
        "actual_duration_ms": actual_duration_ms
    }
    client.publish("hydro/node2/acks", json.dumps(end_event))


def on_connect(client, userdata, flags, rc):
    client.subscribe("hydro/node2/commands")


def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    if payload.get("action") == "PULSE":
        threading.Thread(target=execute_pump, args=(
            payload.get("cmd_id"),
            payload.get("target"),
            payload.get("duration_ms", 0),
            client
        )).start()


def telemetry_loop(client):
    while True:
        # Dérive naturelle : l'EC baisse quand la plante mange, le pH monte
        state["ph"] += random.uniform(0.001, 0.003)
        state["ec"] -= random.uniform(0.001, 0.002) if state["ec"] > 0.4 else 0

        metrics = [("ph", state["ph"]), ("ec", state["ec"]), ("water_temp", state["water_temp"])]
        for metric, value in metrics:
            payload = {"device_id": DEVICE_ID, "metric": metric, "value": round(value, 2)}
            client.publish("hydro/node2/telemetry", json.dumps(payload))
            time.sleep(0.1)
        time.sleep(10)


def ping_loop(client):
    uptime = 0
    while True:
        payload = {"device_id": DEVICE_ID, "uptime_s": uptime, "mode": state["mode"], "relays": state["relays"]}
        client.publish("hydro/node2/status", json.dumps(payload))
        uptime += 1
        time.sleep(1)


if __name__ == "__main__":
    client = mqtt.Client(DEVICE_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()
    threading.Thread(target=ping_loop, args=(client,), daemon=True).start()

    print("🚀 Mock Node Eau (Tri-Part) démarré.")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()