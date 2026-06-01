import {useState, useEffect, useMemo} from 'react';
import {Droplets, AlertOctagon, Settings} from 'lucide-react';
import {hydroApi} from './services/api';
import MaintenanceView from './components/MaintenanceView';
import ActivityMatrix from './components/ActivityMatrix';
import Header from './components/Header';
import ControlPanel from './components/ControlPanel';
import SensorCard from './components/SensorCard';
import ThermalProfileCard from './components/ThermalProfileCard';
import DeviceSettingsModal from "./components/DeviceSettingsModal.tsx";
import WaterLevelGauge from './components/WaterLevelGauge';

export default function App() {
    const [systemMode, setSystemMode] = useState("AUTO");
    const [isConnected, setIsConnected] = useState(false);

    // Ajout de air_temp_source_meteo
    const [liveData, setLiveData] = useState({
        ph: 0, ec: 0, water_temp: 0, air_temp: 0, air_temp_source_meteo: 0, humidity: 0, water_level: 0
    });
    const [telemetryHistory, setTelemetryHistory] = useState<any[]>([]);
    const [cameraUrl, setCameraUrl] = useState<string | null>(null);

    const [timeRange, setTimeRange] = useState<number>(24);

    const [isPendingMode, setIsPendingMode] = useState(false);
    const [showCalibrationModal, setShowCalibrationModal] = useState(false);
    const [showSettings, setShowSettings] = useState(false);

    const [config, setConfig] = useState({
        ph: {target: 6.0, minOk: 5.5, maxOk: 6.5, min: 4.0, max: 8.0},
        ec: {target: 1.4, minOk: 1.2, maxOk: 1.6, min: 0.0, max: 3.0},
        waterLevel: {target: 12, refill: 7, max: 13, critical: 6, min: 0, maxBound: Math.round(13 * 1.07 + 1)},
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
                const [statusRes, historyRes, cameraRes, actuatorRes, configRes] = await Promise.all([
                    hydroApi.getLiveStatus().catch(() => ({data: null})),
                    hydroApi.getTelemetry(timeRange).catch(() => ({data: null})),
                    hydroApi.getLatestCamera().catch(() => ({url: null})),
                    hydroApi.getActuatorHistory().catch(() => ({data: null})),
                    hydroApi.getConfig().catch(() => ({data: null}))
                ]);

                setIsConnected(true);

                if (statusRes.data) setLiveData({
                    ph: statusRes.data.ph?.value || 0,
                    ec: statusRes.data.ec?.value || 0,
                    water_temp: statusRes.data.water_temp?.value || 0,
                    air_temp: statusRes.data.air_temp?.value || 0,
                    air_temp_source_meteo: statusRes.data.air_temp_source_meteo?.value || 0, // Ajout
                    humidity: statusRes.data.humidity?.value || 0,
                    water_level: statusRes.data.water_level?.value || 0,
                });

                if (configRes && configRes.data) {
                    const dbConfig = configRes.data;
                    setConfig(prev => ({
                        ...prev,
                        ph: {...prev.ph, target: dbConfig.target_ph},
                        ec: {...prev.ec, target: dbConfig.target_ec},
                        waterLevel: {
                            ...prev.waterLevel,
                            target: dbConfig.target_water_level,
                            refill: dbConfig.refill_water_level,
                            max: dbConfig.max_water_level,
                            critical: dbConfig.critical_water_level,
                            maxBound: Math.round(dbConfig.max_water_level * 1.07 + 1)
                        }
                    }));
                    if (dbConfig.system_mode) {
                        setSystemMode(dbConfig.system_mode);
                    }
                }

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
    }, [timeRange]);

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
                target_water_level: config.waterLevel.target,
                refill_water_level: config.waterLevel.refill,
                max_water_level: config.waterLevel.max,
                critical_water_level: config.waterLevel.critical,
                system_mode: "MANUAL"
            });

            await hydroApi.sendCommand("ALL_STOP", 0);
            setSystemMode("MANUAL");
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
                target_water_level: config.waterLevel.target,
                refill_water_level: config.waterLevel.refill,
                max_water_level: config.waterLevel.max,
                critical_water_level: config.waterLevel.critical,
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

    const getMetricHistory = (metricName: string) => {
        return telemetryHistory.filter(d => d.metric === metricName);
    };

    // Agrégation de l'historique Eau + Air (Sonde) + Air (Météo)
    const combinedTempHistory = useMemo(() => {
        const tempMap = new Map();
        telemetryHistory.forEach(d => {
            if (d.metric === 'water_temp' || d.metric === 'air_temp' || d.metric === 'air_temp_source_meteo') {
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
                onOpenSettings={() => setShowSettings(true)}
            />

            {systemMode === "MAINTENANCE" && (
                <div className="bg-red-500/10 border-y border-red-500/30 px-4 py-3 flex items-center justify-between">
                    <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
                        <div className="flex items-center gap-3 text-red-400">
                            <AlertOctagon size={20} className="animate-pulse"/>
                            <p className="text-sm font-medium">
                                <strong className="text-red-300">SYSTÈME VERROUILLÉ :</strong> Régulation automatique suspendue. Pompes désactivées.
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
                <div className="bg-orange-500/10 border-y border-orange-500/30 px-4 py-2 text-center text-orange-600 font-medium text-xs flex items-center justify-center gap-2 tracking-wide uppercase">
                    <AlertOctagon size={14} className="animate-bounce"/>
                    Régulation automatique désactivée. Contrôle direct des relais.
                </div>
            )}

            <main className="max-w-4xl mx-auto p-4 space-y-4">
                {systemMode === "MAINTENANCE" ? (
                    <MaintenanceView liveData={liveData}/>
                ) : (
                    <>
                        <div className="flex justify-between items-center mb-2 mt-4">
                            <h2 className="text-sm font-black text-slate-700 uppercase tracking-tight">Capteurs Principaux</h2>
                            <div className="flex bg-white rounded-lg p-1 border border-slate-200 shadow-sm">
                                {[
                                    {label: "1H", value: 1},
                                    {label: "24H", value: 24},
                                    {label: "7J", value: 168}
                                ].map((range) => (
                                    <button
                                        key={range.value}
                                        onClick={() => setTimeRange(range.value)}
                                        className={`px-3 py-1 text-xs font-bold rounded-md transition-colors ${
                                            timeRange === range.value
                                                ? "bg-blue-50 text-blue-600 border border-blue-200 shadow-sm"
                                                : "text-slate-500 hover:bg-slate-50"
                                        }`}
                                    >
                                        {range.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* ROW 1 : CAPTEURS PRINCIPAUX */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <SensorCard
                                label="Potentiel Hydrogène"
                                shortLabel="pH"
                                value={liveData.ph}
                                config={config.ph}
                                lastUpdate={getMetricHistory('ph').slice(-1)[0]?.time || "--:--"}
                                historyData={getMetricHistory('ph')}
                                colorHex="#3b82f6"
                                gradientId="colorPh"
                            />
                            <SensorCard
                                label="Conductivité Électrique"
                                shortLabel="EC"
                                value={liveData.ec}
                                unit="mS/cm"
                                config={config.ec}
                                lastUpdate={getMetricHistory('ec').slice(-1)[0]?.time || "--:--"}
                                historyData={getMetricHistory('ec')}
                                colorHex="#10b981"
                                gradientId="colorEc"
                            />
                        </div>

                        {/* ROW 2 : TEMPERATURES & CLIMAT */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                            {/* Le composant ThermalProfileCard avec les deux sources Air */}
                            <ThermalProfileCard
                                waterTemp={liveData.water_temp}
                                airTempSensor={liveData.air_temp}
                                airTempMeteo={liveData.air_temp_source_meteo}
                                config={config.waterTemp}
                                lastUpdate={combinedTempHistory.length > 0 ? combinedTempHistory[combinedTempHistory.length - 1].time : "--:--"}
                                historyData={combinedTempHistory}
                            />

                            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
                                <div className="p-4">
                                    <h3 className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2 mb-1">
                                        <Droplets size={16} className="text-teal-500"/> Hygrométrie
                                    </h3>
                                    <div className="flex items-baseline gap-2 mt-2">
                                        <span className="text-3xl font-black text-slate-800">{liveData.humidity}%</span>
                                        <span className="text-[10px] font-bold text-teal-500 uppercase tracking-wider">Humidité Air</span>
                                    </div>
                                </div>
                                <div className="h-28 w-full bg-slate-50 border-t border-slate-100 mt-2 flex items-center justify-center">
                                    <span className="text-xs text-slate-400 font-medium">En attente de données</span>
                                </div>
                            </div>

                            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col">
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Niveau d'eau</h3>
                                    <div className="text-right">
                                        <span className="text-2xl font-black text-slate-800">
                                            {(liveData.water_level || 0).toFixed(1)}
                                        </span>
                                        <span className="text-sm font-bold text-slate-400 ml-1">cm</span>
                                    </div>
                                </div>
                                <WaterLevelGauge
                                    value={liveData.water_level}
                                    config={{
                                        target: config.waterLevel.target,
                                        refill: config.waterLevel.refill,
                                        max: config.waterLevel.max,
                                        critical: config.waterLevel.critical,
                                        min: 0,
                                        maxBound: config.waterLevel.maxBound
                                    }}
                                />
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
            {showSettings && (
                <DeviceSettingsModal
                    deviceId="mock_node2_wet"
                    onClose={() => setShowSettings(false)}
                />
            )}
        </div>
    );
}