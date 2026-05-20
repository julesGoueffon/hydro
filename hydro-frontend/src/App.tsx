import { useState, useEffect } from 'react';
import { Activity, Power, Settings, Droplets, Camera, Thermometer, Wind } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, ReferenceLine } from 'recharts';
import { hydroApi } from './services/api';
import LinearToleranceGauge from './components/LinearToleranceGauge';

export default function App() {
  const [systemMode, setSystemMode] = useState("AUTO");
  const [isConnected, setIsConnected] = useState(false);
  
  const [liveData, setLiveData] = useState({ ph: 0, ec: 0, water_temp: 0, air_temp: 0, humidity: 0 });
  const [telemetryHistory, setTelemetryHistory] = useState<any[]>([]);
  const [cameraUrl, setCameraUrl] = useState<string | null>(null);
  
  const [config] = useState({
    ph: { target: 6.0, minOk: 5.5, maxOk: 6.5, min: 4.0, max: 8.0 },
    ec: { target: 1.4, minOk: 1.2, maxOk: 1.6, min: 0.0, max: 3.0 },
    waterTemp: { target: 20.0, minOk: 18.0, maxOk: 24.0, min: 10.0, max: 35.0 },
    airTemp: { target: 24.0, minOk: 20.0, maxOk: 28.0, min: 10.0, max: 40.0 },
  });

  // --- FAUSSES DONNÉES (Simulation des dérives pour voir les Halos) ---
  const hours = Array.from({length: 24}, (_, i) => i);
  
  // Simulation : Un pic acide à 15h, 16h (Halo Rouge sur le pH)
  const mockPhTrend = [6.1, 6.1, 6.1, 6.1, 6.1, 6.1, 6.1, 6.1, 6.1, 6.0, 6.1, 6.1, 6.1, 6.1, 6.1, 6.8, 6.7, 6.1, 6.1, 6.1, 6.1, 6.1, 6.1, 6.1];
  // Simulation : Une chute d'EC à 18h, 19h (Halo Violet sur l'EC)
  const mockEcTrend = [1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4, 1.1, 1.0, 1.4, 1.4, 1.4, 1.4];
  
  // Séparation en deux groupes pour aligner les halos
  const mockPhPumps = [
    { id: "ph_minus", label: "pH -", data: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,0,0,0,0,0,0,0] },
    { id: "ph_plus", label: "pH +", data: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] }
  ];
  
  const mockEcPumps = [
    { id: "nutri_a", label: "Nutri A", data: [0,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,0,0,3,4,0,0,0,0] },
    { id: "nutri_b", label: "Nutri B", data: [0,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,0,0,3,4,0,0,0,0] },
    { id: "nutri_c", label: "Nutri C", data: [0,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,0,0,3,4,0,0,0,0] }
  ];

  // --- REQUÊTES API ---
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, historyRes, cameraRes] = await Promise.all([
          hydroApi.getLiveStatus().catch(() => ({ data: null })),
          hydroApi.getTelemetry(24).catch(() => ({ data: null })), 
          hydroApi.getLatestCamera().catch(() => ({ url: null }))
        ]);
        if (statusRes.data) setLiveData({
            ph: statusRes.data.ph?.value || 0, ec: statusRes.data.ec?.value || 0,
            water_temp: statusRes.data.water_temp?.value || 0, air_temp: statusRes.data.air_temp?.value || 23.4, humidity: statusRes.data.humidity?.value || 58,
        });
        if (historyRes.data) setTelemetryHistory(historyRes.data.map((d: any) => ({
            time: new Date(d.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), metric: d.metric, value: d.value
        })));
        if (cameraRes.url) setCameraUrl(cameraRes.url);
        setIsConnected(true);
      } catch (error) { setIsConnected(false); }
    };
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handlePump = async (pumpName: string, durationMs: number) => {
    try { await hydroApi.sendCommand(pumpName, durationMs); } 
    catch (error) { alert(`Erreur actionneur : ${pumpName}`); }
  };

  const getMetricHistory = (metricName: string, fallbackVal: number) => {
    const filtered = telemetryHistory.filter(d => d.metric === metricName);
    if (filtered.length === 0) return Array.from({ length: 12 }, (_, i) => ({ time: `${i}h`, value: fallbackVal + Math.sin(i) * (fallbackVal * 0.03) }));
    return filtered;
  };

  // Fonction pour retrouver tes belles couleurs bleues
  const getSquareStyle = (count: number) => {
    if (count === 0) return "bg-slate-100/40 border-slate-200/50"; // Vide transparent (laisse passer le halo)
    if (count < 3) return "bg-blue-300 border-blue-400 shadow-sm"; 
    if (count < 6) return "bg-blue-500 border-blue-600 shadow-sm";
    return "bg-blue-700 border-blue-800 shadow-sm";
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 font-sans pb-6">
      
      {/* BANDEAU SUPERIEUR */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md shadow-sm border-b border-slate-200 px-4 py-3 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Droplets className="text-blue-600 animate-pulse" size={24} />
          <h1 className="text-lg font-black tracking-tight text-slate-800">HYDROSTACK</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-full border text-xs font-bold">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            {isConnected ? "ONLINE" : "OFFLINE"}
          </div>
          <button onClick={() => setSystemMode(prev => prev === "AUTO" ? "MAINTENANCE" : "AUTO")} className="bg-slate-800 text-white text-xs font-black px-3 py-1 rounded-full uppercase tracking-wider shadow-sm hover:bg-slate-700 transition-colors">
            {systemMode}
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-4 space-y-4">
        
        {/* ROW 1 : CAPTEURS PRINCIPAUX (pH et EC) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
            <div className="p-4 pb-0">
              <LinearToleranceGauge label="🧪 Potentiel Hydrogène" value={liveData.ph || 6.12} min={config.ph.min} max={config.ph.max} minOk={config.ph.minOk} maxOk={config.ph.maxOk} />
            </div>
            <div className="h-20 w-full bg-slate-50 border-t border-slate-100 mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={getMetricHistory('ph', 6.1)} margin={{ top: 5, right: 0, bottom: 0, left: 0 }}>
                  <defs><linearGradient id="colorPh" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient></defs>
                  <ReferenceLine y={config.ph.target} stroke="#ef4444" strokeDasharray="3 3" />
                  <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorPh)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
            <div className="p-4 pb-0">
              <LinearToleranceGauge label="🌿 Conductivité Électrique" value={liveData.ec || 1.42} min={config.ec.min} max={config.ec.max} minOk={config.ec.minOk} maxOk={config.ec.maxOk} unit="mS/cm" />
            </div>
            <div className="h-20 w-full bg-slate-50 border-t border-slate-100 mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={getMetricHistory('ec', 1.45)} margin={{ top: 5, right: 0, bottom: 0, left: 0 }}>
                  <defs><linearGradient id="colorEc" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient></defs>
                  <ReferenceLine y={config.ec.target} stroke="#ef4444" strokeDasharray="3 3" />
                  <Area type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorEc)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ROW 2 : TEMPERATURES & CLIMAT */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-3">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl"><Thermometer size={20}/></div>
            <div><p className="text-xs font-bold text-slate-400 uppercase">Eau</p><p className="text-xl font-black text-slate-800">{(liveData.water_temp || 19.5).toFixed(1)}°C</p></div>
          </div>
          <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-3">
            <div className="p-2 bg-orange-50 text-orange-500 rounded-xl"><Wind size={20}/></div>
            <div><p className="text-xs font-bold text-slate-400 uppercase">Air Ambiant</p><p className="text-xl font-black text-slate-800">{(liveData.air_temp || 24.1).toFixed(1)}°C</p></div>
          </div>
          <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-3">
            <div className="p-2 bg-teal-50 text-teal-600 rounded-xl"><Droplets size={20}/></div>
            <div><p className="text-xs font-bold text-slate-400 uppercase">Humidité</p><p className="text-xl font-black text-slate-800">{liveData.humidity || 58}%</p></div>
          </div>
        </div>

        {/* ROW 3 : VISION ET ACTIONNEURS (5 Pompes) */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between lg:col-span-1">
            <div className="flex items-center gap-2 mb-2 text-xs font-bold text-slate-500 uppercase"><Camera size={14}/> Caméra</div>
            <div className="aspect-video lg:aspect-square w-full bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center border shadow-inner">
              {cameraUrl ? <img src={cameraUrl} alt="Serre" className="object-cover w-full h-full" /> : <div className="text-[10px] text-slate-500 p-2 text-center">📷 Démo</div>}
            </div>
          </div>

          <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between lg:col-span-3 border-l-4 border-l-orange-500">
            <div className="flex justify-between items-center mb-3 border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-orange-600 uppercase"><Power size={14}/> Panneau de Forçage</div>
              <button onClick={() => handlePump("EMERGENCY_STOP", 0)} className="bg-red-50 hover:bg-red-600 hover:text-white text-red-600 font-black py-1 px-3 rounded flex items-center gap-1 text-[10px] tracking-wider uppercase transition-colors border border-red-200">
                <Power size={12} /> Arrêt d'urgence
              </button>
            </div>
            {/* Grille de 5 pompes */}
            <div className="grid grid-cols-5 gap-2 text-center">
              {[
                { id: "pump_ph_minus", label: "pH -" }, { id: "pump_ph_plus", label: "pH +" },
                { id: "pump_nutri_a", label: "Nutri A" }, { id: "pump_nutri_b", label: "Nutri B" }, { id: "pump_nutri_c", label: "Nutri C" }
              ].map((pump) => (
                <div key={pump.id} className="bg-slate-50 p-2 rounded-xl border border-slate-200 flex flex-col gap-2">
                  <span className="text-[10px] font-black text-slate-600 uppercase mb-1">{pump.label}</span>
                  <button onClick={() => handlePump(pump.id, 2000)} className="w-full bg-white hover:bg-blue-50 text-blue-700 font-bold py-1.5 rounded-lg border border-slate-300 text-[10px] shadow-sm transition-transform active:scale-95">2s</button>
                  <button onClick={() => handlePump(pump.id, 15000)} className="w-full bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-1.5 rounded-lg border border-slate-300 text-[10px] shadow-sm transition-transform active:scale-95">Purge</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ROW 4 : MATRICE D'ACTIVITÉ SÉPARÉE (Le vrai Heatmap) */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 overflow-x-auto">
          <h2 className="text-sm font-bold text-slate-700 flex items-center gap-2 uppercase tracking-wider mb-6">
            <Activity size={16} className="text-blue-500" />
            Matrice d'Activité & Dérives (24h)
          </h2>
          
          <div className="flex flex-col gap-6 min-w-[600px]">
            
            {/* GROUPE 1 : LE BLOC PH */}
            <div className="flex">
              {/* Noms à gauche */}
              <div className="flex flex-col gap-1 pr-4 border-r border-slate-100 mr-2 justify-center">
                {mockPhPumps.map(p => (
                  <span key={p.id} className="text-[10px] font-bold text-slate-500 uppercase tracking-wide w-12 text-right">{p.label}</span>
                ))}
              </div>
              {/* Grille des 24h avec Halo centré */}
              <div className="flex gap-1">
                {hours.map(h => {
                  const val = mockPhTrend[h];
                  const isHigh = val > config.ph.maxOk;
                  const isLow = val < config.ph.minOk;
                  const halo = isHigh ? "bg-red-500" : isLow ? "bg-blue-500" : "";

                  return (
                    <div key={`ph-${h}`} className="relative flex flex-col gap-1 w-4 md:w-5 group pt-4">
                      {/* L'heure qui apparaît au survol */}
                      <span className="absolute top-0 left-1/2 -translate-x-1/2 text-[8px] font-bold text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">{h}h</span>
                      
                      {/* LE HALO CENTRÉ DERRIÈRE LA COLONNE PH */}
                      {halo && <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-10 ${halo} blur-md opacity-60 z-0 rounded-full pointer-events-none`} />}
                      
                      {/* Les carrés */}
                      {mockPhPumps.map(p => (
                        <div key={p.id} className={`relative z-10 w-full aspect-square rounded-[2px] border transition-transform hover:scale-125 cursor-help ${getSquareStyle(p.data[h])}`} />
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* GROUPE 2 : LE BLOC EC */}
            <div className="flex">
              {/* Noms à gauche */}
              <div className="flex flex-col gap-1 pr-4 border-r border-slate-100 mr-2 justify-center">
                {mockEcPumps.map(p => (
                  <span key={p.id} className="text-[10px] font-bold text-slate-500 uppercase tracking-wide w-12 text-right">{p.label}</span>
                ))}
              </div>
              {/* Grille des 24h avec Halo centré */}
              <div className="flex gap-1">
                {hours.map(h => {
                  const val = mockEcTrend[h];
                  const isHigh = val > config.ec.maxOk;
                  const isLow = val < config.ec.minOk;
                  const halo = isHigh ? "bg-orange-500" : isLow ? "bg-purple-500" : "";

                  return (
                    <div key={`ec-${h}`} className="relative flex flex-col gap-1 w-4 md:w-5 group pt-4">
                      <span className="absolute top-0 left-1/2 -translate-x-1/2 text-[8px] font-bold text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">{h}h</span>
                      
                      {/* LE HALO CENTRÉ DERRIÈRE LA COLONNE EC */}
                      {halo && <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-12 ${halo} blur-md opacity-60 z-0 rounded-full pointer-events-none`} />}
                      
                      {mockEcPumps.map(p => (
                        <div key={p.id} className={`relative z-10 w-full aspect-square rounded-[2px] border transition-transform hover:scale-125 cursor-help ${getSquareStyle(p.data[h])}`} />
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        </div>

      </main>
    </div>
  );
}