import { Camera, Power } from 'lucide-react';

interface ControlPanelProps {
    cameraUrl: string | null;
    systemMode: string;
    handleEmergencyStop: () => void;
    handlePump: (pumpId: string, durationMs: number) => void;
}

export default function ControlPanel({ cameraUrl, systemMode, handleEmergencyStop, handlePump }: ControlPanelProps) {
    const pumps = [
        { id: "pump_ph_minus", label: "pH -" },
        { id: "pump_ph_plus", label: "pH +" },
        { id: "pump_nutri_1", label: "Nutri A" },
        { id: "pump_nutri_2", label: "Nutri B" },
        { id: "pump_nutri_3", label: "Nutri C" }
    ];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* CAMÉRA */}
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between lg:col-span-1">
                <div className="flex items-center gap-2 mb-2 text-xs font-bold text-slate-500 uppercase">
                    <Camera size={14}/> Caméra
                </div>
                <div className="aspect-video lg:aspect-square w-full bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center border shadow-inner">
                    <img
                        src={cameraUrl || "http://127.0.0.1:8000/api/camera/latest"}
                        alt="Serre"
                        className="object-cover w-full h-full"
                        key={Math.floor(Date.now() / 10000)}
                    />
                </div>
            </div>

            {/* PANNEAU DE FORÇAGE */}
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between lg:col-span-3 border-l-4 border-l-orange-500">
                <div className="flex justify-between items-center mb-3 border-b border-slate-100 pb-2">
                    <div className="flex items-center gap-2 text-xs font-bold text-orange-600 uppercase">
                        <Power size={14}/> Panneau de Forçage
                    </div>
                    <button
                        onClick={handleEmergencyStop}
                        className="bg-red-50 hover:bg-red-600 hover:text-white text-red-600 font-black py-1 px-3 rounded flex items-center gap-1 text-[10px] tracking-wider uppercase transition-colors border border-red-200"
                    >
                        <Power size={12}/> Arrêt d'urgence
                    </button>
                </div>
                <div className="grid grid-cols-5 gap-2 text-center">
                    {pumps.map((pump) => (
                        <div key={pump.id} className="bg-slate-50 p-2 rounded-xl border border-slate-200 flex flex-col gap-2">
                            <span className="text-[10px] font-black text-slate-600 uppercase mb-1">{pump.label}</span>
                            <button
                                onClick={() => handlePump(pump.id, 2000)}
                                className="w-full bg-white hover:bg-blue-50 text-blue-700 font-bold py-1.5 rounded-lg border border-slate-300 text-[10px] shadow-sm transition-transform active:scale-95"
                            >
                                2s
                            </button>
                            {/* Le bouton de purge n'apparaît qu'en manuel ou maintenance */}
                            {systemMode !== "AUTO" && (
                                <button
                                    onClick={() => handlePump(pump.id, 15000)}
                                    className="w-full bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-1.5 rounded-lg border border-slate-300 text-[10px] shadow-sm transition-transform active:scale-95"
                                >
                                    Purge
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}