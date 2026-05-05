import paho.mqtt.client as mqtt
import json
import time
import random
import threading

# --- CONFIGURATION ---
BROKER = "127.0.0.1"
PORT = 1883
DEVICE_ID = "mock_node2_wet"
SIM_SPEED = 0.5 # <--- 1.0 = normal, 5.0 = rapide, 10.0 = extrême

state = {
    "ph": 6.5,
    "ec": 1.2,
    "water_temp": 21.0,
    "target_ph_adjustment": 0.0,
    "target_ec_adjustment": 0.0,
    "mode": "default",
    "relays": {
        "pump_ph_minus": "OFF", "pump_ph_plus": "OFF",
        "pump_nutri_1": "OFF", "pump_nutri_2": "OFF", "pump_nutri_3": "OFF"
    }
}


def physics_engine(speed=1.0):
    """
    Simule l'évolution des constantes.
    Plus 'speed' est élevé, plus les variations sont violentes.
    """
    print(f"⚙️ Moteur physique démarré (Vitesse: {speed}x)")
    while True:
        # 1. PH : Rétroaction progressive + Dérive naturelle
        # L'inertie (le mélange) est aussi accélérée par la vitesse
        if abs(state["target_ph_adjustment"]) > 0.005:
            step = state["target_ph_adjustment"] * (0.1 * speed)
            state["ph"] += step
            state["target_ph_adjustment"] -= step
        else:
            # Dérive naturelle du pH (monte de 0.01 à 0.02 par cycle de base)
            state["ph"] += random.uniform(0.005, 0.015) * speed

        # 2. EC : Chute de l'EC (consommation) + Ajout nutriments
        if state["target_ec_adjustment"] > 0.005:
            step = state["target_ec_adjustment"] * (0.1 * speed)
            state["ec"] += step
            state["target_ec_adjustment"] -= step
        else:
            # Chute constante de l'EC
            state["ec"] -= 0.002 * speed

        # 3. Température : Variation instable
        state["water_temp"] += random.uniform(-0.05, 0.05) * speed

        # --- BORNES ET ARRONDIS ---
        state["ph"] = round(max(3.0, min(10.0, state["ph"])), 2)
        state["ec"] = round(max(0.1, state["ec"]), 2)
        state["water_temp"] = round(max(15.0, min(32.0, state["water_temp"])), 1)

        time.sleep(0.1)  # Fréquence fixe pour la fluidité


def execute_pump(cmd_id, target, duration_ms, client):
    state["relays"][target] = "ON"
    client.publish("hydro/node2/acks", json.dumps({"cmd_id": cmd_id, "status": "STARTED"}))

    time.sleep(duration_ms / 1000.0)

    # L'impact des pompes est constant, c'est la vitesse de mélange qui change dans physics_engine
    impact = (duration_ms / 1000.0) * 0.15
    if target == "pump_ph_minus":
        state["target_ph_adjustment"] -= impact
    elif target == "pump_ph_plus":
        state["target_ph_adjustment"] += impact
    elif "pump_nutri" in target:
        state["target_ec_adjustment"] += impact * 0.4

    state["relays"][target] = "OFF"
    client.publish("hydro/node2/acks", json.dumps({"cmd_id": cmd_id, "status": "COMPLETED"}))


# --- LOGIQUE MQTT ET BOUCLES ---

def telemetry_loop(client):
    while True:
        for metric in ["ph", "ec", "water_temp"]:
            payload = {"device_id": DEVICE_ID, "metric": metric, "value": state[metric]}
            client.publish("hydro/node2/telemetry", json.dumps(payload))
            time.sleep(0.05)
        time.sleep(2.0)  # Un envoi toutes les 2s pour garder le dashboard lisible


def ping_loop(client):
    uptime = 0
    while True:
        payload = {
            "device_id": DEVICE_ID,
            "uptime_s": uptime,
            "mode": state["mode"],
            "relays": state["relays"],
            "sim_speed": SIM_SPEED  # Utile pour savoir dans quel mode on est
        }
        client.publish("hydro/node2/status", json.dumps(payload))
        uptime += 1
        time.sleep(1)


def on_connect(client, userdata, flags, rc):
    print(f"✅ Connecté au Broker (RC: {rc})")
    client.subscribe("hydro/node2/commands")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("action") == "PULSE":
            threading.Thread(target=execute_pump, args=(
                payload.get("cmd_id"),
                payload.get("target"),
                payload.get("duration_ms", 0),
                client
            )).start()
    except Exception as e:
        print(f"❌ Erreur payload: {e}")


if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=DEVICE_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    # Démarrage des Threads de simulation
    threading.Thread(target=physics_engine, args=(SIM_SPEED,), daemon=True).start()
    threading.Thread(target=telemetry_loop, args=(client,), daemon=True).start()
    threading.Thread(target=ping_loop, args=(client,), daemon=True).start()

    print(f"🚀 Mock Node démarré (Vitesse x{SIM_SPEED})")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Arrêt du simulateur.")
        client.disconnect()