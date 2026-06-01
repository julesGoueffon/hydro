import { ResponsiveContainer, AreaChart, Area, ReferenceLine, XAxis, YAxis, Tooltip } from 'recharts';
import { Clock } from 'lucide-react';

export interface SensorCardProps {
    label: string;
    shortLabel?: string;
    value: number;
    unit?: string;
    lastUpdate?: string;
    config: {
        target: number;
        min: number;
        max: number;
        minOk: number;
        maxOk: number;
    };
    historyData: any[];
    colorHex: string;
    gradientId: string;
}

// ─── Composant Jauge Horizontale Épaisse et Explicite ─────────────────────────
const AestheticGauge = ({ value, min, max, minOk, maxOk, target }: any) => {
    // Sécurisation et calcul des pourcentages
    const safeValue = isFinite(value) ? value : 0;
    const range = max - min || 1;
    const getPct = (v: number) => Math.max(0, Math.min(100, ((v - min) / range) * 100));

    const okStart = getPct(minOk);
    const okEnd = getPct(maxOk);
    const okWidth = okEnd - okStart;
    const targetPct = getPct(target);
    const valPct = getPct(safeValue);

    // Détection précise du côté de l'alerte
    const isLowWarning = safeValue < minOk;
    const isHighWarning = safeValue > maxOk;
    const isWarning = isLowWarning || isHighWarning;

    return (
        <div className="w-full flex flex-col gap-1">
            <div className="relative w-full">
                {/* Barre de la jauge (plus épaisse : h-4) */}
                <div className="flex h-4 w-full overflow-hidden rounded-full shadow-inner border border-slate-200/50 bg-slate-100">
                    {/* Zone Basse (S'allume en rouge vif si alerte basse) */}
                    <div
                        className={`h-full transition-colors duration-500 ${isLowWarning ? 'bg-red-500' : 'bg-red-200/60'}`}
                        style={{ width: `${okStart}%` }}
                    />

                    {/* Zone Verte (OK) */}
                    <div className="h-full bg-emerald-400" style={{ width: `${okWidth}%` }} />

                    {/* Zone Haute (S'allume en rouge vif si alerte haute) */}
                    <div
                        className={`h-full transition-colors duration-500 ${isHighWarning ? 'bg-red-500' : 'bg-red-200/60'}`}
                        style={{ width: `${100 - okEnd}%` }}
                    />
                </div>

                {/* Ligne Cible (Target) */}
                <div
                    className="absolute top-[-3px] bottom-[-3px] w-[2px] bg-slate-600 rounded z-10"
                    style={{ left: `${targetPct}%`, transform: 'translateX(-50%)' }}
                />

                {/* Curseur de Valeur Actuelle (plus gros) */}
                <div
                    className={`absolute top-1/2 w-[18px] h-[18px] rounded-full border-[2.5px] border-white shadow-md z-20 ${
                        isWarning ? 'bg-red-600 scale-110' : 'bg-slate-800'
                    }`}
                    style={{ left: `${valPct}%`, transform: 'translate(-50%, -50%)', transition: 'left 0.4s ease-out, background-color 0.3s' }}
                >
                    {/* Effet clignotant si hors des clous */}
                    {isWarning && <span className="absolute inset-0 rounded-full bg-red-400 opacity-75 animate-ping" />}
                </div>
            </div>

            {/* Micro-labels resserrés sous la jauge */}
            <div className="flex justify-between text-[8px] font-bold text-slate-400 px-1 font-mono uppercase tracking-tighter">
                <span>{min}</span>
                <span className="text-emerald-600/80">{target}</span>
                <span>{max}</span>
            </div>
        </div>
    );
};

// ─── Infobulle du Graphique ────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-slate-900/95 text-white text-xs p-2.5 rounded-lg shadow-xl border border-slate-700 z-50 pointer-events-none">
                <p className="font-bold text-slate-400 mb-1">{label}</p>
                <p className="font-mono text-sm" style={{ color: payload[0].stroke }}>
                    {Number(payload[0].value).toFixed(2)}
                </p>
            </div>
        );
    }
    return null;
};

// ─── Composant Principal ───────────────────────────────────────────────────────
export default function SensorCard({
    label, shortLabel, value, unit, lastUpdate, config, historyData, colorHex, gradientId
}: SensorCardProps) {

    // Calcul de l'échelle dynamique pour le graphique
    const safeHistoryData = Array.isArray(historyData) ? historyData : [];
    const dataMin = safeHistoryData.length > 0 ? Math.min(...safeHistoryData.map(d => d.value)) : config.min;
    const dataMax = safeHistoryData.length > 0 ? Math.max(...safeHistoryData.map(d => d.value)) : config.max;

    // Marge de 10% en haut et en bas pour que la courbe ne touche pas les bords
    const yRange = (dataMax - dataMin) || 1;
    const yMin = Math.max(config.min, dataMin - (yRange * 0.1));
    const yMax = Math.min(config.max, dataMax + (yRange * 0.1));

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col p-3 pb-1">

            {/* ── EN-TÊTE ULTRA COMPACT : Valeur (Gauche) + Jauge (Droite) ── */}
            <div className="flex items-center justify-between gap-2 mb-1">

                {/* BLOC GAUCHE : Valeur et Infos empilées */}
                <div className="flex flex-col justify-center">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none mb-1.5">
                        {shortLabel || label}
                    </span>

                    <div className="flex items-baseline gap-1 mb-1.5">
                        <span className="text-2xl font-black text-slate-900 tracking-tight leading-none">
                            {isFinite(value) ? value.toFixed(2) : "0.00"}
                        </span>
                        {unit && <span className="text-[10px] font-bold text-slate-400 leading-none">{unit}</span>}
                    </div>

                    {lastUpdate && (
                        <div className="flex items-center gap-1 text-[8px] font-bold text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100 leading-none w-fit">
                            <Clock size={8} strokeWidth={2.5} /> {lastUpdate}
                        </div>
                    )}
                </div>

                {/* BLOC DROIT : La Jauge Épaisse */}
                <div className="flex-1 max-w-[160px] pt-1">
                    <AestheticGauge
                        value={value}
                        min={config.min} max={config.max}
                        minOk={config.minOk} maxOk={config.maxOk}
                        target={config.target}
                    />
                </div>
            </div>

            {/* ── GRAPHIQUE RECHARTS COMPACTÉ (h-28) ── */}
            <div className="h-28 w-full mt-1 relative z-0">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={safeHistoryData} margin={{ top: 5, right: 0, bottom: 0, left: -20 }}>
                        <defs>
                            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={colorHex} stopOpacity={0.25} />
                                <stop offset="95%" stopColor={colorHex} stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <XAxis
                            dataKey="time"
                            tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 600 }}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={20}
                        />

                        <YAxis
                            domain={[yMin, yMax]}
                            tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 600 }}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => val.toFixed(1)}
                        />

                        <Tooltip
                            content={<CustomTooltip />}
                            cursor={{ stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '4 4' }}
                        />

                        <ReferenceLine
                            y={config.target}
                            stroke="#ef4444"
                            strokeDasharray="3 3"
                            strokeOpacity={0.5}
                        />

                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke={colorHex}
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill={`url(#${gradientId})`}
                            isAnimationActive={false}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

        </div>
    );
}