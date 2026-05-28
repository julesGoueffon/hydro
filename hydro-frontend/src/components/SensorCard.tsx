import { ResponsiveContainer, AreaChart, Area, ReferenceLine, XAxis, YAxis, Tooltip } from 'recharts';
import LinearToleranceGauge from './LinearToleranceGauge';
import { Clock } from 'lucide-react'; // Ajout de l'icône horloge

interface SensorCardProps {
    label: string;
    value: number;
    unit?: string;
    lastUpdate?: string; // <-- Nouvelle prop pour l'heure de la prise
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

// Composant pour customiser l'infobulle au survol du graphique
const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-slate-900/90 text-white text-xs p-2 rounded-lg shadow-lg border border-slate-700 backdrop-blur-sm">
                <p className="font-bold text-slate-300 mb-1">{label}</p>
                <p className="font-mono text-sm" style={{ color: payload[0].stroke }}>
                    {payload[0].value.toFixed(2)}
                </p>
            </div>
        );
    }
    return null;
};

export default function SensorCard({
    label, value, unit, lastUpdate, config, historyData, colorHex, gradientId
}: SensorCardProps) {

    // Calcul de l'échelle dynamique (Min et Max du graphique) pour ne pas écraser la courbe
    const dataMin = historyData.length > 0 ? Math.min(...historyData.map(d => d.value)) : config.min;
    const dataMax = historyData.length > 0 ? Math.max(...historyData.map(d => d.value)) : config.max;
    // On ajoute une petite marge (10%) en haut et en bas
    const yMin = Math.max(config.min, dataMin - (dataMin * 0.1));
    const yMax = Math.min(config.max, dataMax + (dataMax * 0.1));

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
            <div className="p-4 pb-2 relative">
                {/* Affichage de la dernière mise à jour en tout petit en haut à droite */}
                {lastUpdate && (
                    <div className="absolute top-4 right-4 flex items-center gap-1 text-[10px] font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded-full border border-slate-100">
                        <Clock size={10} /> {lastUpdate}
                    </div>
                )}

                <LinearToleranceGauge
                    label={label} value={value}
                    min={config.min} max={config.max}
                    minOk={config.minOk} maxOk={config.maxOk} unit={unit}
                />
            </div>

            {/* On a augmenté la hauteur (h-36 au lieu de h-20) pour faire de la place aux axes */}
            <div className="h-40 w-full bg-slate-50 border-t border-slate-100 mt-2 p-2">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData} margin={{top: 10, right: 10, bottom: 0, left: -20}}>
                        <defs>
                            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={colorHex} stopOpacity={0.2}/>
                                <stop offset="95%" stopColor={colorHex} stopOpacity={0}/>
                            </linearGradient>
                        </defs>

                        {/* Axe X (Temps) */}
                        <XAxis
                            dataKey="time"
                            tick={{fontSize: 9, fill: '#94a3b8', fontWeight: 600}}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={20}
                        />

                        {/* Axe Y (Valeurs) */}
                        <YAxis
                            domain={[yMin, yMax]}
                            tick={{fontSize: 9, fill: '#94a3b8', fontWeight: 600}}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => val.toFixed(1)}
                        />

                        {/* Le Tooltip qui apparaît au survol */}
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#cbd5e1', strokeWidth: 1, strokeDasharray: '4 4' }} />

                        <ReferenceLine y={config.target} stroke="#ef4444" strokeDasharray="3 3" />
                        <Area type="monotone" dataKey="value" stroke={colorHex} strokeWidth={2} fillOpacity={1} fill={`url(#${gradientId})`}/>
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}