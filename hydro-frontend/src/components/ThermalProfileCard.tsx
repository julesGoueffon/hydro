import { Thermometer, Wind } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, ReferenceLine } from 'recharts';

interface ThermalProfileCardProps {
    waterTemp: number;
    airTemp: number;
    targetWaterTemp: number;
    historyData: any[];
}

export default function ThermalProfileCard({ waterTemp, airTemp, targetWaterTemp, historyData }: ThermalProfileCardProps) {
    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col justify-between">
            <div className="p-4 flex justify-between items-start">
                <div>
                    <h3 className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2 mb-1">
                        <Thermometer size={16} className="text-blue-500" /> Profil Thermique
                    </h3>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-black text-slate-800">{waterTemp.toFixed(1)}°C</span>
                        <span className="text-[10px] font-bold text-blue-500 uppercase tracking-wider">Eau</span>
                    </div>
                </div>
                <div className="text-right bg-orange-50 px-3 py-1.5 rounded-lg border border-orange-100">
                    <div className="flex items-center gap-1.5 justify-end text-orange-600">
                        <Wind size={14} />
                        <span className="text-lg font-bold">{airTemp.toFixed(1)}°C</span>
                    </div>
                    <span className="text-[9px] font-black text-orange-400 uppercase tracking-wider">Air Ambiant</span>
                </div>
            </div>

            <div className="h-28 w-full bg-slate-50 border-t border-slate-100 mt-2">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData} margin={{top: 10, right: 0, bottom: 0, left: 0}}>
                        <defs>
                            <linearGradient id="colorWater" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                            </linearGradient>
                        </defs>

                        {/* Ligne cible pour l'eau */}
                        <ReferenceLine y={targetWaterTemp} stroke="#94a3b8" strokeDasharray="3 3"/>

                        {/* Courbe Air (En fond, juste une ligne orange) */}
                        <Area type="monotone" dataKey="air_temp" stroke="#f97316" strokeWidth={1.5} fillOpacity={0} />

                        {/* Courbe Eau (Au premier plan, avec remplissage bleu) */}
                        <Area type="monotone" dataKey="water_temp" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorWater)"/>
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}