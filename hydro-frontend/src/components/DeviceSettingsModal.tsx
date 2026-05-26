import { useState, useEffect } from 'react';
import { X, Save, Cpu } from 'lucide-react';
import { hydroApi } from '../services/api';

export default function DeviceSettingsModal({ deviceId, onClose }: { deviceId: string, onClose: () => void }) {
    const [settings, setSettings] = useState({
        telemetry_interval_sec: 600,
        ph_read_interval_ms: 2000,
        ec_read_interval_ms: 2000,
        temp_read_interval_ms: 5000
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        hydroApi.getDeviceSettings(deviceId)
            .then(res => {
                setSettings(res.data);
                setIsLoading(false);
            })
            .catch(() => setIsLoading(false));
    }, [deviceId]);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await hydroApi.updateDeviceSettings({ device_id: deviceId, ...settings });
            alert("✅ Paramètres envoyés à l'ESP32");
            onClose();
        } catch (e) {
            alert("❌ Erreur lors de la sauvegarde");
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) return null;

    return (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
                <div className="bg-slate-50 px-5 py-4 border-b border-slate-200 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-200 text-slate-700 rounded-lg"><Cpu size={20} /></div>
                        <div>
                            <h2 className="font-black text-slate-800">Paramètres Matériels</h2>
                            <p className="text-xs font-bold text-slate-400 uppercase">{deviceId}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 bg-slate-100 hover:bg-slate-200 p-2 rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="p-5 space-y-5">
                    <div className="space-y-1">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Envoi Télémétrie (Secondes)</label>
                        <p className="text-[10px] text-slate-400">À quelle fréquence l'ESP32 envoie les données au serveur en mode normal (Ex: 600 = 10 min).</p>
                        <input type="number" value={settings.telemetry_interval_sec} onChange={(e) => setSettings({...settings, telemetry_interval_sec: parseInt(e.target.value)})} className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono font-bold text-slate-700 mt-2"/>
                    </div>

                    <div className="grid grid-cols-2 gap-4 border-t border-slate-100 pt-5">
                        <div className="space-y-1">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lecture pH (ms)</label>
                            <input type="number" step="100" value={settings.ph_read_interval_ms} onChange={(e) => setSettings({...settings, ph_read_interval_ms: parseInt(e.target.value)})} className="w-full border-slate-300 rounded-lg shadow-sm font-mono text-sm"/>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lecture EC (ms)</label>
                            <input type="number" step="100" value={settings.ec_read_interval_ms} onChange={(e) => setSettings({...settings, ec_read_interval_ms: parseInt(e.target.value)})} className="w-full border-slate-300 rounded-lg shadow-sm font-mono text-sm"/>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-slate-50 border-t border-slate-100">
                    <button onClick={handleSave} disabled={isSaving} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl shadow-sm flex items-center justify-center gap-2 transition-colors">
                        <Save size={18} /> {isSaving ? "Synchronisation MQTT..." : "Sauvegarder & Flasher"}
                    </button>
                </div>
            </div>
        </div>
    );
}