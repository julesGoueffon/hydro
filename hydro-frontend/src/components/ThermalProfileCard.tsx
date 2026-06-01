import { ResponsiveContainer, AreaChart, Area, ReferenceLine, XAxis, YAxis, Tooltip } from 'recharts';
import { Clock, CloudSun, Droplets, Home } from 'lucide-react';

export interface ThermalProfileCardProps {
    waterTemp: number;
    airTempSensor: number; // Sonde locale
    airTempMeteo: number;  // API Météo Auxerre
    lastUpdate?: string;
    config?: {
        target: number;
        min: number;
        max: number;
        minOk: number;
        maxOk: number;
    };
    historyData: any[];
}

// ─── Composant Jauge Horizontale Épaisse ─────────────────────────
const AestheticGauge = ({ value, min, max, minOk, maxOk, target }: any) => {
    const safeValue = isFinite(value) ? value : 0;
    const range = max - min || 1;
    const getPct = (v: number) => Math.max(0, Math.min(100, ((v - min) / range) * 100));

    const okStart = getPct(minOk);
    const okEnd = getPct(maxOk);
    const okWidth = okEnd - okStart;
    const targetPct = getPct(target);
    const valPct = getPct(safeValue);

    const isLowWarning = safeValue < minOk;
    const isHighWarning = safeValue > maxOk;
    const isWarning = isLowWarning || isHighWarning;

    return (
        <div className="w-full flex flex-col gap-1">
            <div className="relative w-full">
                <div className="flex h-3.5 w-full overflow-hidden rounded-full shadow-inner border border-slate-200/50 bg-slate-100">
                    <div
                        className={`h-full transition-colors duration-500 ${isLowWarning ? 'bg-red-500' : 'bg-red-200/60'}`}
                        style={{ width: `${okStart}%` }}
                    />
                    <div className="h-full bg-emerald-400" style={{ width: `${okWidth}%` }} />
                    <div
                        className={`h-full transition-colors duration-500 ${isHighWarning ? 'bg-red-500' : 'bg-red-200/60'}`}
                        style={{ width: `${100 - okEnd}%` }}
                    />
                </div>

                <div
                    className="absolute top-[-3px] bottom-[-3px] w-[2px] bg-slate-600 rounded z-10"
                    style={{ left: `${targetPct}%`, transform: 'translateX(-50%)' }}
                />

                <div
                    className={`absolute top-1/2 w-[16px] h-[16px] rounded-full border-[2.5px] border-white shadow-md z-20 ${
                        isWarning ? 'bg-red-600 scale-110' : 'bg-blue-600'
                    }`}
                    style={{ left: `${valPct}%`, transform: 'translate(-50%, -50%)', transition: 'left 0.4s ease-out, background-color 0.3s' }}
                >
                    {isWarning && <span className="absolute inset-0 rounded-full bg-red-400 opacity-75 animate-ping" />}
                </div>
            </div>

            <div className="flex justify-between text-[8px] font-bold text-slate-400 px-1 font-mono uppercase tracking-tighter">
                <span>{min}°</span>
                <span className="text-emerald-600/80">{target}°</span>
                <span>{max}°</span>
            </div>
        </div>
    );
};

// ─── Infobulle du Graphique (Triple Valeur) ────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-slate-900/95 text-white text-xs p-2.5 rounded-lg shadow-xl border border-slate-700 z-50 pointer-events-none min-w-[130px]">
                <p className="font-bold text-slate-400 mb-2 border-b border-slate-700 pb-1">{label}</p>
                <div className="flex flex-col gap-1.5">
                    {payload.map((entry: any, index: number) => {
                        let icon = <Droplets size={12}/>;
                        let name = 'Eau';
                        if (entry.dataKey === 'air_temp') { icon = <Home size={12}/>; name = 'Serre'; }
                        if (entry.dataKey === 'air_temp_source_meteo') { icon = <CloudSun size={12}/>; name = 'Auxerre'; }

                        return (
                            <div key={index} className="flex items-center justify-between gap-3 font-mono text-sm" style={{ color: entry.stroke }}>
                                <span className="flex items-center gap-1 text-xs">{icon} {name}</span>
                                <span className="font-bold">{Number(entry.value).toFixed(1)}°</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }
    return null;
};

// ─── Composant Principal ───────────────────────────────────────────────────────
export default function ThermalProfileCard({
    waterTemp, airTempSensor, airTempMeteo, lastUpdate, config, historyData
}: ThermalProfileCardProps) {

    const safeHistoryData = Array.isArray(historyData) ? historyData : [];
    const safeConfig = config || { target: 20, min: 10, max: 35, minOk: 18, maxOk: 24 };

    // Calcul de l'échelle dynamique pour englober toutes les températures
    const allValues = safeHistoryData.flatMap(d => [d.water_temp, d.air_temp, d.air_temp_source_meteo]).filter(v => v != null);
    const dataMin = allValues.length > 0 ? Math.min(...allValues, safeConfig.min) : safeConfig.min;
    const dataMax = allValues.length > 0 ? Math.max(...allValues, safeConfig.max) : safeConfig.max;

    const yRange = (dataMax - dataMin) || 1;
    const yMin = Math.max(0, dataMin - (yRange * 0.1));
    const yMax = dataMax + (yRange * 0.1);

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">

            {/* ── EN-TÊTE ULTRA COMPACT (Padding interne préservé ici) ── */}
            <div className="flex items-center justify-between gap-4 p-3 pb-2 z-10 bg-white">

                {/* BLOC GAUCHE : Valeurs Eau, Air (Sonde) & Air (Météo) */}
                <div className="flex flex-col">
                    <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none">
                            T° EAU & AIR
                        </span>
                        {lastUpdate && (
                            <div className="flex items-center gap-1 text-[9px] font-bold text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100 leading-none">
                                <Clock size={9} strokeWidth={2.5} /> {lastUpdate}
                            </div>
                        )}
                    </div>

                    <div className="flex items-end gap-3 mt-0.5">
                        {/* Eau */}
                        <div className="flex items-baseline gap-0.5">
                            <span className="text-3xl font-black text-slate-900 tracking-tight leading-none">
                                {isFinite(waterTemp) ? waterTemp.toFixed(1) : "--"}
                            </span>
                            <span className="text-xs font-bold text-slate-400 leading-none mb-0.5">°C</span>
                        </div>

                        {/* Sonde Serre */}
                        <div className="flex flex-col border-l border-slate-200 pl-2">
                            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest leading-none mb-[3px] flex items-center gap-1">
                                <Home size={8} /> Serre
                            </span>
                            <span className="text-sm font-black text-slate-700 leading-none">
                                {isFinite(airTempSensor) ? airTempSensor.toFixed(1) : "--"}°C
                            </span>
                        </div>

                        {/* Météo Auxerre */}
                        <div className="flex flex-col border-l border-slate-200 pl-2">
                            <span className="text-[8px] font-black text-amber-500 uppercase tracking-widest leading-none mb-[3px] flex items-center gap-1">
                                <CloudSun size={8} /> Auxerre
                            </span>
                            <span className="text-sm font-black text-amber-600 leading-none">
                                {isFinite(airTempMeteo) ? airTempMeteo.toFixed(1) : "--"}°C
                            </span>
                        </div>
                    </div>
                </div>

                {/* BLOC DROIT : La Jauge */}
                <div className="flex-1 max-w-[140px]">
                    <AestheticGauge
                        value={waterTemp}
                        min={safeConfig.min} max={safeConfig.max}
                        minOk={safeConfig.minOk} maxOk={safeConfig.maxOk}
                        target={safeConfig.target}
                    />
                </div>
            </div>

            {/* ── GRAPHIQUE BORDERLESS (Il touche les bords du conteneur) ── */}
            <div className="h-28 w-full relative z-0 bg-slate-50/30">
                <ResponsiveContainer width="100%" height="100%">
                    {/* Le secret est ici : left -25 cache l'axe Y, right 0 et bottom 0 collent le graph aux parois */}
                    <AreaChart data={safeHistoryData} margin={{ top: 5, right: 0, bottom: 0, left: -25 }}>
                        <defs>
                            <linearGradient id="gradientWater" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.25} />
                                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="gradientAirMeteo" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.15} />
                                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <XAxis
                            dataKey="time"
                            tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 600 }}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={20}
                            height={15} // Réduit drastiquement l'espace vide en bas
                        />

                        <YAxis
                            domain={[yMin, yMax]}
                            tick={false} // On masque les textes de l'axe Y pour gagner toute la place
                            tickLine={false}
                            axisLine={false}
                        />

                        <Tooltip
                            content={<CustomTooltip />}
                            cursor={{ stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '4 4' }}
                        />

                        <ReferenceLine
                            y={safeConfig.target}
                            stroke="#ef4444"
                            strokeDasharray="3 3"
                            strokeOpacity={0.5}
                        />

                        {/* 1. Météo Auxerre (Orange, au fond) */}
                        <Area
                            type="monotone"
                            dataKey="air_temp_source_meteo"
                            stroke="#f59e0b"
                            strokeWidth={1.5}
                            strokeDasharray="3 3" // En pointillés pour montrer que c'est distant
                            fillOpacity={1}
                            fill="url(#gradientAirMeteo)"
                            isAnimationActive={false}
                        />

                        {/* 2. Sonde Air Locale (Gris-Violet, milieu) */}
                        <Area
                            type="monotone"
                            dataKey="air_temp"
                            stroke="#8b5cf6"
                            strokeWidth={2}
                            fillOpacity={0} // Juste la ligne pour ne pas surcharger
                            isAnimationActive={false}
                        />

                        {/* 3. Eau (Bleue, devant) */}
                        <Area
                            type="monotone"
                            dataKey="water_temp"
                            stroke="#2563eb"
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill="url(#gradientWater)"
                            isAnimationActive={false}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

        </div>
    );
}