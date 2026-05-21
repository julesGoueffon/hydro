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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return response.json();
    },

  // --- CONTRÔLE-COMMANDE ---
  sendCommand: async (target: string, duration_ms: number, device_id: string = "node2") => {
    const res = await fetch(`${API_BASE_URL}/command/override`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // On respecte exactement le Pydantic Model `CommandOverride` de ton backend
      body: JSON.stringify({ target, duration_ms, device_id }),
    });
    if (!res.ok) throw new Error("Erreur d'envoi de la commande");
    return res.json();
  },
};