import {useState, useEffect, useMemo} from 'react';
import {Droplets, AlertOctagon, Settings} from 'lucide-react';
import {hydroApi} from './services/api';
import MaintenanceView from './components/MaintenanceView';
import ActivityMatrix from './components/ActivityMatrix';
import Header from './components/Header';
import ControlPanel from './components/ControlPanel';
import SensorCard from './components/SensorCard';
import ThermalProfileCard from './components/ThermalProfileCard'; // <-- Nouvel import !

export default function App() {
    const [systemMode, setSystemMode] = useState("AUTO");
    const [isConnected, setIsConnected] = useState(false);

    const [liveData, setLiveData] = useState({ph: 0, ec: 0, water_temp: 0, air_temp: 0, humidity: 0});
    const [telemetryHistory, setTelemetryHistory] = useState<any[]>([]);
    const [cameraUrl, setCameraUrl] = useState<string | null>(null);

    const [isPendingMode, setIsPendingMode] = useState(false);
    const [showCalibrationModal, setShowCalibrationModal] = useState(false);

    const [config] = useState({
        ph: {target: 6.0, minOk: 5.5, maxOk: 6.5, min: 4.0, max: 8.0},
        ec: {target: 1.4, minOk: 1.2, maxOk: 1.6, min: 0.0, max: 3.0},
        waterTemp: {target: 20.0, minOk: 18.0, maxOk: 24.0, min: 10.0, max: 35.0},
        airTemp: {target: 24.0, minOk: 20.0, maxOk: 28.0, min: 10.0, max: 40.0},
    });

    const [heatmapData, setHeatmapData] = useState<Record<string, number[]>>({
        "pump_ph_minus": Array(24).fill(0),
        "pump_ph_plus": Array(24).fill(0),
        "pump_nutri_1": Array(24).fill(0),
        "pump_nutri_2": Array(24).fill(0),
        "pump_nutri_3": Array(24).fill(0),
    });

    // --- REQUÊTES API ---
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [statusRes, historyRes, cameraRes, actuatorRes] = await Promise.all([
                    hydroApi.getLiveStatus().catch(() => ({data: null})),
                    hydroApi.getTelemetry(24).catch(() => ({data: null})),
                    hydroApi.getLatestCamera().catch(() => ({url: null})),
                    hydroApi.getActuatorHistory().catch(() => ({data: null}))
                ]);

                setIsConnected(true);

                if (statusRes.data) setLiveData({
                    ph: statusRes.data.ph?.value || 0,
                    ec: statusRes.data.ec?.value || 0,
                    water_temp: statusRes.data.water_temp?.value || 0,
                    air_temp: statusRes.data.air_temp?.value || 0,
                    humidity: statusRes.data.humidity?.value || 0,
                    // Ajoute ces deux lignes pour capter la tension brute lors de la maintenance :
                    ph_raw: statusRes.data.ph_calibration?.value || 0,
                    ec_raw: statusRes.data.ec_calibration?.value || 0,
                });

                if (historyRes.data) setTelemetryHistory(historyRes.data.map((d: any) => ({
                    time: new Date(d.time).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
                    metric: d.metric,
                    value: d.value
                })));

                if (actuatorRes && actuatorRes.data) {
                    const newHeatmap = {
                        "pump_ph_minus": Array(24).fill(0),
                        "pump_ph_plus": Array(24).fill(0),
                        "pump_nutri_1": Array(24).fill(0),
                        "pump_nutri_2": Array(24).fill(0),
                        "pump_nutri_3": Array(24).fill(0),
                    };

                    const tzOffsetHours = -(new Date().getTimezoneOffset() / 60);

                    actuatorRes.data.forEach((row: any) => {
                        const pumpId = row.actuator_id;
                        const utcHour = Math.floor(row.hour);
                        const localHour = (utcHour + tzOffsetHours + 24) % 24;

                        if (newHeatmap[pumpId as keyof typeof newHeatmap] !== undefined) {
                            newHeatmap[pumpId as keyof typeof newHeatmap][localHour] += parseInt(row.activations, 10);
                        }
                    });

                    setHeatmapData(newHeatmap);
                }
            } catch (error) {
                setIsConnected(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, []);

    // --- ACTIONS ---
    const handlePump = async (pumpName: string, durationMs: number) => {
        try {
            await hydroApi.sendCommand(pumpName, durationMs);
        } catch (error: any) {
            alert(`Erreur actionneur (${pumpName}) : ${error.message || "Refusé"}`);
        }
    };

    const handleEmergencyStop = async () => {
        if (isPendingMode) return;
        setIsPendingMode(true);
        try {
            await hydroApi.updateConfig({
                target_ph: config.ph.target,
                target_ec: config.ec.target,
                system_mode: "MANUAL"
            });
            setSystemMode("MANUAL");

            await hydroApi.sendCommand("ALL_STOP", 0);
            alert("🚨 ARRÊT D'URGENCE : Le système est passé en mode MANUEL, les pompes sont coupées.");
        } catch (error) {
            alert("Échec de l'arrêt d'urgence ! Vérifiez la connexion.");
        } finally {
            setIsPendingMode(false);
        }
    };

    const handleModeChange = async (newMode: string) => {
        if (newMode === systemMode || isPendingMode) return;

        setIsPendingMode(true);
        try {
            await hydroApi.updateConfig({
                target_ph: config.ph.target,
                target_ec: config.ec.target,
                system_mode: newMode
            });

            setSystemMode(newMode);

            if (newMode !== "MAINTENANCE") {
                setShowCalibrationModal(false);
            }
        } catch (e) {
            alert("Erreur réseau : Impossible de changer le mode. Vérifiez la connexion.");
        } finally {
            setIsPendingMode(false);
        }
    };

    // --- PRÉPARATION DES DONNÉES GRAPHIQUES ---
    const getMetricHistory = (metricName: string) => {
        return telemetryHistory.filter(d => d.metric === metricName);
    };

    // Fusion de l'eau et de l'air pour le graphique combiné
    const combinedTempHistory = useMemo(() => {
        const tempMap = new Map();
        telemetryHistory.forEach(d => {
            if (d.metric === 'water_temp' || d.metric === 'air_temp') {
                if (!tempMap.has(d.time)) tempMap.set(d.time, {time: d.time});
                tempMap.get(d.time)[d.metric] = d.value;
            }
        });
        return Array.from(tempMap.values());
    }, [telemetryHistory]);


    return (
        <div className="min-h-screen bg-slate-100 text-slate-900 font-sans pb-6">

            <Header
                isConnected={isConnected}
                systemMode={systemMode}
                isPendingMode={isPendingMode}
                handleModeChange={handleModeChange}
            />

            {/* BANNIÈRES */}
            {systemMode === "MAINTENANCE" && (
                <div className="bg-red-500/10 border-y border-red-500/30 px-4 py-3 flex items-center justify-between">
                    <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
                        <div className="flex items-center gap-3 text-red-400">
                            <AlertOctagon size={20} className="animate-pulse"/>
                            <p className="text-sm font-medium">
                                <strong className="text-red-300">SYSTÈME VERROUILLÉ :</strong> Régulation automatique
                                suspendue. Pompes désactivées.
                            </p>
                        </div>
                        <button onClick={() => setShowCalibrationModal(true)}
                                className="bg-red-500 hover:bg-red-600 text-white px-4 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-2">
                            <Settings size={16}/> Calibrer les sondes
                        </button>
                    </div>
                </div>
            )}

            {systemMode === "MANUAL" && (
                <div
                    className="bg-orange-500/10 border-y border-orange-500/30 px-4 py-2 text-center text-orange-600 font-medium text-xs flex items-center justify-center gap-2 tracking-wide uppercase">
                    <AlertOctagon size={14} className="animate-bounce"/>
                    Régulation automatique désactivée. Contrôle direct des relais.
                </div>
            )}

            <main className="max-w-4xl mx-auto p-4 space-y-4">
                {systemMode === "MAINTENANCE" ? (
                    <MaintenanceView liveData={liveData}/>
                ) : (
                    <>
                        {/* ROW 1 : CAPTEURS PRINCIPAUX */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <SensorCard
                                label="🧪 Potentiel HydrogèneLL"
                                value={liveData.ph}
                                config={config.ph}
                                historyData={getMetricHistory('ph')}
                                colorHex="#3b82f6"
                                gradientId="colorPh"
                            />
                            <SensorCard
                                label="🌿 Conductivité Électrique"
                                value={liveData.ec}
                                unit="mS/cm"
                                config={config.ec}
                                historyData={getMetricHistory('ec')}
                                colorHex="#10b981"
                                gradientId="colorEc"
                            />
                        </div>

                        {/* ROW 2 : TEMPERATURES & CLIMAT */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <ThermalProfileCard
                                waterTemp={liveData.water_temp}
                                airTemp={liveData.air_temp}
                                targetWaterTemp={config.waterTemp.target}
                                historyData={combinedTempHistory}
                            />

                            {/* CARTE HUMIDITÉ (Isolée pour l'instant) */}
                            <div
                                className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
                                <div className="p-4">
                                    <h3 className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2 mb-1">
                                        <Droplets size={16} className="text-teal-500"/> Hygrométrie
                                    </h3>
                                    <div className="flex items-baseline gap-2 mt-2">
                                        <span className="text-3xl font-black text-slate-800">{liveData.humidity}%</span>
                                        <span className="text-[10px] font-bold text-teal-500 uppercase tracking-wider">Humidité Air</span>
                                    </div>
                                </div>
                                <div
                                    className="h-28 w-full bg-slate-50 border-t border-slate-100 mt-2 flex items-center justify-center">
                                    <span className="text-xs text-slate-400 font-medium">En attente de données</span>
                                </div>
                            </div>
                        </div>

                        {/* ROW 3 : VISION ET ACTIONNEURS */}
                        <ControlPanel
                            cameraUrl={cameraUrl}
                            systemMode={systemMode}
                            handleEmergencyStop={handleEmergencyStop}
                            handlePump={handlePump}
                        />

                        {/* ROW 4 : MATRICE D'ACTIVITÉ */}
                        <ActivityMatrix
                            heatmapData={heatmapData}
                            liveData={liveData}
                            config={config}
                        />
                    </>
                )}
            </main>
        </div>
    );
}