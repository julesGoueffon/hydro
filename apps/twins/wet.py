import paho.mqtt.client as mqtt
import json
import time
import random
import threading
import os

# --- CONFIGURATION ---
BROKER = "127.0.0.1"
PORT = 1883
DEVICE_ID = "mock_node2_wet"
SIM_SPEED = float(os.getenv("SIM_SPEED", 1.0))

state = {
    "ph": 6.5,
    "ec": 1.2,
    "water_temp": 21.0,
    "target_ph_adjustment": 0.0,
    "target_ec_adjustment": 0.0,
    "mode": "AUTO",
    "relays": {
        "pump_ph_minus": "OFF", "pump_ph_plus": "OFF",
        "pump_nutri_1": "OFF", "pump_nutri_2": "OFF", "pump_nutri_3": "OFF"
    }
}


def physics_engine(speed=1.0):
    print(f"⚙️ Moteur physique démarré (Vitesse: {speed}x)")
    while True:
        if abs(state["target_ph_adjustment"]) > 0.005:
            step = state["target_ph_adjustment"] * (0.1 * speed)
            state["ph"] += step
            state["target_ph_adjustment"] -= step
        else:
            state["ph"] += random.uniform(0.002, 0.005) * speed

        if state["target_ec_adjustment"] > 0.005:
            step = state["target_ec_adjustment"] * (0.1 * speed)
            state["ec"] += step
            state["target_ec_adjustment"] -= step
        else:
            state["ec"] -= 0.002 * speed

        state["water_temp"] += random.uniform(-0.05, 0.05) * speed

        state["ph"] = round(max(3.0, min(10.0, state["ph"])), 2)
        state["ec"] = round(max(0.1, state["ec"]), 2)
        state["water_temp"] = round(max(15.0, min(32.0, state["water_temp"])), 1)

        time.sleep(0.025)


def execute_pump(cmd_id, target, duration_ms, client):
    state["relays"][target] = "ON"
    # CORRECTION : Topic dynamique
    client.publish(f"hydro/{DEVICE_ID}/acks", json.dumps({
        "cmd_id": cmd_id, "status": "STARTED", "target": target, "duration_ms": duration_ms
    }))

    print(f"💧 POMPE ACTIVÉE : {target} pour {duration_ms}ms")
    time.sleep(duration_ms / 1000.0)

    impact = (duration_ms / 1000.0) * 0.15
    if target == "pump_ph_minus":
        state["target_ph_adjustment"] -= impact
    elif target == "pump_ph_plus":
        state["target_ph_adjustment"] += impact
    elif "pump_nutri" in target:
        state["target_ec_adjustment"] += impact * 0.4

    state["relays"][target] = "OFF"
    client.publish(f"hydro/{DEVICE_ID}/acks", json.dumps({
        "cmd_id": cmd_id, "status": "COMPLETED", "target": target, "duration_ms": duration_ms
    }))
    print(f"✅ POMPE ARRÊTÉE : {target}")


def telemetry_loop(client):
    while True:
        for metric in ["ph", "ec", "water_temp"]:
            payload = {"device_id": DEVICE_ID, "metric": metric, "value": state[metric]}
            # CORRECTION : Topic dynamique
            client.publish(f"hydro/{DEVICE_ID}/telemetry", json.dumps(payload))
            time.sleep(0.05)
        time.sleep(2.0)


def ping_loop(client):
    uptime = 0
    while True:
        payload = {
            "device_id": DEVICE_ID, "uptime_s": uptime, "mode": state["mode"],
            "relays": state["relays"], "sim_speed": SIM_SPEED
        }
        # CORRECTION : Topic dynamique
        client.publish(f"hydro/{DEVICE_ID}/status", json.dumps(payload))
        uptime += 1
        time.sleep(1)


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"✅ Connecté au Broker (RC: {rc})")
    # CORRECTION : Topic dynamique
    client.subscribe(f"hydro/{DEVICE_ID}/commands")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"📥 Ordre reçu : {payload}")

        if payload.get("action") == "PULSE":
            threading.Thread(target=execute_pump, args=(
                payload.get("cmd_id"), payload.get("target"), payload.get("duration_ms", 0), client
            )).start()
    except Exception as e:
        print(f"❌ Erreur payload: {e}")


if __name__ == "__main__":
    # Initialisation compatible avec toutes les versions de Paho-MQTT
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
    except AttributeError:
        client = mqtt.Client(client_id=DEVICE_ID)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    threading.Thread(target=physics_engine, args=(SIM_SPEED,), daemon=True).start()
    threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()
    threading.Thread(target=ping_loop, args=(client,), daemon=True).start()

    print(f"🚀 Mock Node démarré (Vitesse x{SIM_SPEED})")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Arrêt du simulateur.")
        client.disconnect()