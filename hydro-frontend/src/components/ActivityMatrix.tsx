import { Activity } from 'lucide-react';

// On définit ce que le composant a besoin de recevoir pour fonctionner
interface ActivityMatrixProps {
    heatmapData: Record<string, number[]>;
    liveData: { ph: number; ec: number };
    config: {
        ph: { minOk: number; maxOk: number };
        ec: { minOk: number; maxOk: number };
    };
}



export default function ActivityMatrix({ heatmapData, liveData, config }: ActivityMatrixProps) {
    // --- LOGIQUE INTERNE DÉPLACÉE DEPUIS APP.TSX ---
    const currentLocalHour = new Date().getHours();
    const rollingHours = Array.from({length: 24}, (_, i) => (currentLocalHour - 23 + i + 24) % 24);

    const phPumps = [
        {id: "pump_ph_minus", label: "pH -", data: heatmapData["pump_ph_minus"]},
        {id: "pump_ph_plus", label: "pH +", data: heatmapData["pump_ph_plus"]}
    ];

    const ecPumps = [
        {id: "pump_nutri_1", label: "Nutri A", data: heatmapData["pump_nutri_1"]},
        {id: "pump_nutri_2", label: "Nutri B", data: heatmapData["pump_nutri_2"]},
        {id: "pump_nutri_3", label: "Nutri C", data: heatmapData["pump_nutri_3"]}
    ];

    const getSquareStyle = (count: number) => {
        if (count === 0) return "bg-slate-100/40 border-slate-200/50";
        if (count < 3) return "bg-blue-300 border-blue-400 shadow-sm";
        if (count < 6) return "bg-blue-500 border-blue-600 shadow-sm";
        return "bg-blue-700 border-blue-800 shadow-sm";
    };

    return (
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 overflow-x-auto">
            <h2 className="text-sm font-bold text-slate-700 flex items-center gap-2 uppercase tracking-wider mb-6">
                <Activity size={16} className="text-blue-500"/>
                Matrice d'Activité & Dérives (24h)
            </h2>

            <div className="flex flex-col gap-6 min-w-[600px]">
                {/* SECTION pH */}
                <div className="flex">
                    <div className="flex flex-col gap-1 pr-4 border-r border-slate-100 mr-2 justify-center">
                        {phPumps.map(p => <span key={p.id} className="text-[10px] font-bold text-slate-500 uppercase tracking-wide w-12 text-right">{p.label}</span>)}
                    </div>
                    <div className="flex gap-1">
                        {rollingHours.map((h, index) => {
                            const isNow = index === 23;
                            const isMidnight = h === 0 && index !== 0;
                            const halo = liveData.ph > config.ph.maxOk ? "bg-red-500" : liveData.ph > 0 && liveData.ph < config.ph.minOk ? "bg-blue-500" : "";
                            return (
                                <div key={`ph-${h}`} className="relative flex flex-col gap-1 w-4 md:w-5 group pt-4">
                                    {isMidnight && <div className="absolute -left-[3px] top-4 bottom-0 w-px bg-slate-300 z-0" />}
                                    <span className={`absolute top-0 left-1/2 -translate-x-1/2 text-[8px] font-bold transition-opacity ${isNow ? 'text-blue-500 opacity-100' : 'text-slate-400 opacity-0 group-hover:opacity-100'}`}>
                                        {isNow ? 'NOW' : `${h}h`}
                                    </span>
                                    {halo && <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-10 ${halo} blur-md opacity-60 z-0 rounded-full pointer-events-none`}/>}
                                    {phPumps.map(p => <div key={p.id} title={`${p.label} à ${h}h : ${p.data[h]} pulses`} className={`relative z-10 w-full aspect-square rounded-[2px] border transition-transform hover:scale-125 cursor-help ${getSquareStyle(p.data[h])}`}/>)}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* SECTION EC */}
                <div className="flex">
                    <div className="flex flex-col gap-1 pr-4 border-r border-slate-100 mr-2 justify-center">
                        {ecPumps.map(p => <span key={p.id} className="text-[10px] font-bold text-slate-500 uppercase tracking-wide w-12 text-right">{p.label}</span>)}
                    </div>
                    <div className="flex gap-1">
                        {rollingHours.map((h, index) => {
                            const isNow = index === 23;
                            const isMidnight = h === 0 && index !== 0;
                            const halo = liveData.ec > config.ec.maxOk ? "bg-orange-500" : liveData.ec > 0 && liveData.ec < config.ec.minOk ? "bg-purple-500" : "";
                            return (
                                <div key={`ec-${h}`} className="relative flex flex-col gap-1 w-4 md:w-5 group pt-4">
                                    {isMidnight && <div className="absolute -left-[3px] top-4 bottom-0 w-px bg-slate-300 z-0" />}
                                    <span className={`absolute top-0 left-1/2 -translate-x-1/2 text-[8px] font-bold transition-opacity ${isNow ? 'text-blue-500 opacity-100' : 'text-slate-400 opacity-0 group-hover:opacity-100'}`}>
                                        {isNow ? 'NOW' : `${h}h`}
                                    </span>
                                    {halo && <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-12 ${halo} blur-md opacity-60 z-0 rounded-full pointer-events-none`}/>}
                                    {ecPumps.map(p => <div key={p.id} title={`${p.label} à ${h}h : ${p.data[h]} pulses`} className={`relative z-10 w-full aspect-square rounded-[2px] border transition-transform hover:scale-125 cursor-help ${getSquareStyle(p.data[h])}`}/>)}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}