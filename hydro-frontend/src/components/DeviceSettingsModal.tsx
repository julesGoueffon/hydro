import { useState, useEffect } from 'react';
import { X, Save, Cpu, AlertTriangle, Droplets } from 'lucide-react';
import { hydroApi } from '../services/api';

export default function DeviceSettingsModal({ deviceId, onClose }: { deviceId: string, onClose: () => void }) {
    const [settings, setSettings] = useState({
        // Paramètres matériels (device_settings)
        telemetry_interval_sec: 600,
        ph_read_interval_ms: 2000,
        ec_read_interval_ms: 2000,
        temp_read_interval_ms: 5000,

        // Consignes agronomiques (system_config)
        max_water_level: 13,
        target_water_level: 12,
        refill_water_level: 7,
        critical_water_level: 6,

        // On garde ça en mémoire pour ne pas les écraser lors de la sauvegarde
        target_ph: 6.0,
        target_ec: 1.4,
        system_mode: 'AUTO'
    });

    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    // ==========================================
    // 1. LECTURE (On interroge les DEUX tables)
    // ==========================================
    useEffect(() => {
        Promise.all([
            hydroApi.getDeviceSettings(deviceId).catch(() => ({ data: null })),
            hydroApi.getConfig().catch(() => ({ data: null }))
        ]).then(([deviceRes, configRes]) => {
            setSettings(prev => ({
                ...prev,
                // On injecte les données matérielles
                ...(deviceRes.data || {}),

                // On injecte les données agronomiques
                ...(configRes.data ? {
                    max_water_level: configRes.data.max_water_level,
                    target_water_level: configRes.data.target_water_level,
                    refill_water_level: configRes.data.refill_water_level,
                    critical_water_level: configRes.data.critical_water_level,
                    target_ph: configRes.data.target_ph,
                    target_ec: configRes.data.target_ec,
                    system_mode: configRes.data.system_mode
                } : {})
            }));
            setIsLoading(false);
        });
    }, [deviceId]);

    const isWaterLevelValid =
        settings.critical_water_level < settings.refill_water_level &&
        settings.refill_water_level < settings.target_water_level &&
        settings.target_water_level < settings.max_water_level;

    // ==========================================
    // 2. ÉCRITURE (On sauvegarde dans les DEUX tables)
    // ==========================================
    const handleSave = async () => {
        if (!isWaterLevelValid) return;

        setIsSaving(true);
        try {
            // A. Sauvegarde du matériel (ESP32)
            await hydroApi.updateDeviceSettings({
                device_id: deviceId,
                telemetry_interval_sec: settings.telemetry_interval_sec,
                ph_read_interval_ms: settings.ph_read_interval_ms,
                ec_read_interval_ms: settings.ec_read_interval_ms,
                temp_read_interval_ms: settings.temp_read_interval_ms
            });

            // B. Sauvegarde des consignes agronomiques (Niveau d'eau)
            await hydroApi.updateConfig({
                target_ph: settings.target_ph,
                target_ec: settings.target_ec,
                system_mode: settings.system_mode,
                target_water_level: settings.target_water_level,
                refill_water_level: settings.refill_water_level,
                max_water_level: settings.max_water_level,
                critical_water_level: settings.critical_water_level
            });

            alert("✅ Paramètres et Seuils sauvegardés avec succès");
            onClose();
        } catch (e) {
            alert("❌ Erreur lors de la sauvegarde (Vérifiez l'API)");
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) return null;

    const waterLevelsConfig = [
        { label: "MAX (Débordement)", key: "max_water_level", color: "text-red-600", bg: "bg-red-50", border: "border-red-200" },
        { label: "CIBLE (Arrêt pompe)", key: "target_water_level", color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-200" },
        { label: "REFILL (Déclenchement)", key: "refill_water_level", color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-200" },
        { label: "CRITIQUE (Pompe à vide)", key: "critical_water_level", color: "text-red-600", bg: "bg-red-50", border: "border-red-200" }
    ];

    return (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col max-h-[90vh]">

                {/* HEADER */}
                <div className="bg-slate-50 px-5 py-4 border-b border-slate-200 flex justify-between items-center flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-200 text-slate-700 rounded-lg"><Cpu size={20} /></div>
                        <div>
                            <h2 className="font-black text-slate-800">Paramètres Système</h2>
                            <p className="text-xs font-bold text-slate-400 uppercase">{deviceId}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 bg-slate-100 hover:bg-slate-200 p-2 rounded-full transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* CONTENU DÉROULANT */}
                <div className="p-5 space-y-6 overflow-y-auto">

                    {/* SECTION 1 : TÉLÉMÉTRIE */}
                    <div className="space-y-1">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Envoi Télémétrie (Secondes)</label>
                        <p className="text-[10px] text-slate-400">Fréquence d'envoi global des données au serveur.</p>
                        <input
                            type="number"
                            value={settings.telemetry_interval_sec}
                            onChange={(e) => setSettings({ ...settings, telemetry_interval_sec: parseInt(e.target.value) || 0 })}
                            className="w-full border-slate-300 rounded-lg shadow-sm focus:border-blue-500 focus:ring-blue-500 font-mono font-bold text-slate-700 mt-2"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Lecture pH (ms)</label>
                            <input type="number" step="100" value={settings.ph_read_interval_ms} onChange={(e) => setSettings({ ...settings, ph_read_interval_ms: parseInt(e.target.value) || 0 })} className="w-full border-slate-300 rounded-lg shadow-sm font-mono text-sm" />
                        </div>
                        <div className="space-y-1">
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Lecture EC (ms)</label>
                            <input type="number" step="100" value={settings.ec_read_interval_ms} onChange={(e) => setSettings({ ...settings, ec_read_interval_ms: parseInt(e.target.value) || 0 })} className="w-full border-slate-300 rounded-lg shadow-sm font-mono text-sm" />
                        </div>
                    </div>

                    {/* SECTION 2 : SEUILS D'EAU */}
                    <div className="space-y-4 border-t border-slate-100 pt-5">
                        <div>
                            <h3 className="text-xs font-black text-slate-800 uppercase flex items-center gap-2">
                                <Droplets size={16} className="text-blue-500" /> Seuils Niveau d'Eau
                            </h3>
                            <p className="text-[10px] text-slate-400 mt-1">
                                L'ordre logique (Critique &lt; Refill &lt; Cible &lt; Max) doit être respecté.
                            </p>
                        </div>

                        {/* LISTE ORDONNÉE DES SEUILS */}
                        <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-2">
                            {waterLevelsConfig.map((item) => (
                                <div key={item.key} className={`flex justify-between items-center p-2 rounded-lg border ${item.bg} ${item.border}`}>
                                    <label className={`text-[11px] font-black uppercase ${item.color}`}>{item.label}</label>
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="number"
                                            value={settings[item.key as keyof typeof settings] || ''}
                                            onChange={(e) => setSettings({ ...settings, [item.key]: parseFloat(e.target.value) || 0 })}
                                            className="w-16 border-slate-300 rounded shadow-sm text-sm font-mono text-center py-1"
                                        />
                                        <span className="text-[10px] font-bold text-slate-400 w-4">cm</span>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* ALERTE DE VALIDATION */}
                        {!isWaterLevelValid && (
                            <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-lg border border-red-200 text-[11px] font-bold animate-in slide-in-from-top-2">
                                <AlertTriangle size={16} className="flex-shrink-0" />
                                Valeurs incohérentes. Les seuils doivent se suivre du plus petit au plus grand.
                            </div>
                        )}
                    </div>
                </div>

                {/* FOOTER & SAUVEGARDE */}
                <div className="p-4 bg-slate-50 border-t border-slate-100 flex-shrink-0">
                    <button
                        onClick={handleSave}
                        disabled={isSaving || !isWaterLevelValid}
                        className={`w-full font-bold py-3 rounded-xl shadow-sm flex items-center justify-center gap-2 transition-colors ${
                            !isWaterLevelValid 
                                ? "bg-slate-300 text-slate-500 cursor-not-allowed" 
                                : "bg-blue-600 hover:bg-blue-700 text-white"
                        }`}
                    >
                        <Save size={18} /> {isSaving ? "Synchronisation MQTT..." : "Sauvegarder & Flasher"}
                    </button>
                </div>

            </div>
        </div>
    );
}