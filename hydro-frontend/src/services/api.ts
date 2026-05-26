// src/services/api.ts

// En développement, ton API FastAPI tourne sur le port 8000
const API_BASE_URL = "http://localhost:8000/api";

export const hydroApi = {
    // --- SUPERVISION ---
    getLiveStatus: async () => {
        const res = await fetch(`${API_BASE_URL}/status/live`);
        if (!res.ok) throw new Error("Erreur serveur");
        return res.json();
    },

    getTelemetry: async (hours: number = 24) => {
        const res = await fetch(`${API_BASE_URL}/telemetry?hours=${hours}`);
        if (!res.ok) throw new Error("Erreur serveur");
        return res.json();
    },

    getLatestCamera: async () => {
        const res = await fetch(`${API_BASE_URL}/camera/latest`);
        if (!res.ok) throw new Error("Erreur serveur");
        return res.json();
    },

    // --- Configuration & Mode Système ---
    getConfig: async () => {
        // Optionnel : Il faudrait une route GET /api/config côté FastAPI pour lire l'état au démarrage
        const response = await fetch(`${API_BASE_URL}/config`);
        return response.json();
    },

    updateConfig: async (config: { target_ph: number, target_ec: number, system_mode: string }) => {
        const response = await fetch(`${API_BASE_URL}/config`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        return response.json();
    },

    // --- CONTRÔLE-COMMANDE ---
    sendCommand: async (target: string, duration_ms: number, device_id: string = "mock_node2_wet") => {
        const res = await fetch(`${API_BASE_URL}/command/override`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            // On respecte exactement le Pydantic Model `CommandOverride` de ton backend
            body: JSON.stringify({target, duration_ms, device_id}),
        });
        if (!res.ok) throw new Error("Erreur d'envoi de la commande");
        return res.json();
    },


    getActuatorHistory: async () => {
        const response = await fetch(`${API_BASE_URL}/actuators/history`);
        if (!response.ok) throw new Error("Erreur réseau");
        return response.json();
    },


    overridePump: async (target: string, duration_ms: number, device_id: string = "mock_node2_wet") => {
        const response = await fetch(`${API_BASE_URL}/command/override`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({target, duration_ms, device_id})
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Action refusée par le système de sécurité");
        }

        return response.json();
    },

    getDeviceSettings: async (deviceId: string) => {
        const response = await fetch(`${API_BASE_URL}/api/device/${deviceId}/settings`);
        if (!response.ok) throw new Error("Erreur lecture settings");
        return response.json();
    },
    updateDeviceSettings: async (settings: any) => {
        const response = await fetch(`${API_BASE_URL}/api/device/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        if (!response.ok) throw new Error("Erreur sauvegarde settings");
        return response.json();
    },

    triggerAcquisition: async (sensorType: string) => {
        const response = await fetch(`${API_BASE_URL}/api/command/acquire`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: "mock_node2_wet",
                sensor_type: sensorType,
                duration_ms: 2000
            })
        });
        if (!response.ok) throw new Error("Échec du lancement de l'acquisition");
        return response.json();
    }
};


