import { ResponsiveContainer, AreaChart, Area, ReferenceLine } from 'recharts';
import LinearToleranceGauge from './LinearToleranceGauge';

interface SensorCardProps {
    label: string;
    value: number;
    unit?: string;
    config: {
        target: number;
        min: number;
        max: number;
        minOk: number;
        maxOk: number;
    };
    historyData: any[];
    colorHex: string; // Ex: "#3b82f6" (bleu) ou "#10b981" (vert)
    gradientId: string; // Ex: "colorPh" ou "colorEc" (doit être unique)
}

export default function SensorCard({
    label,
    value,
    unit,
    config,
    historyData,
    colorHex,
    gradientId
}: SensorCardProps) {
    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
            <div className="p-4 pb-0">
                <LinearToleranceGauge
                    label={label}
                    value={value}
                    min={config.min}
                    max={config.max}
                    minOk={config.minOk}
                    maxOk={config.maxOk}
                    unit={unit}
                />
            </div>
            <div className="h-20 w-full bg-slate-50 border-t border-slate-100 mt-2">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData} margin={{top: 5, right: 0, bottom: 0, left: 0}}>
                        <defs>
                            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={colorHex} stopOpacity={0.2}/>
                                <stop offset="95%" stopColor={colorHex} stopOpacity={0}/>
                            </linearGradient>
                        </defs>
                        <ReferenceLine y={config.target} stroke="#ef4444" strokeDasharray="3 3"/>
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke={colorHex}
                            strokeWidth={2}
                            fillOpacity={1}
                            fill={`url(#${gradientId})`}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}