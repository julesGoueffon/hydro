import { useState, useEffect } from 'react';
import { Camera, Power } from 'lucide-react';

// --- NOUVEAU COMPOSANT : Caméra Anti-Flash ---
function SmoothCamera({ intervalMs = 10000 }) {
    const [currentImg, setCurrentImg] = useState(`/api/camera/latest?t=${Date.now()}`);
    const [nextImg, setNextImg] = useState<string | null>(null);

    useEffect(() => {
        const timer = setInterval(() => {
            // On lance le chargement de la prochaine image
            setNextImg(`/api/camera/latest?t=${Date.now()}`);
        }, intervalMs);
        return () => clearInterval(timer);
    }, [intervalMs]);

    return (
        <div className="relative w-full h-full bg-slate-900">
            {/* 1. L'image visible actuellement */}
            <img
                src={currentImg}
                alt="Serre"
                className="absolute inset-0 w-full h-full object-cover transition-opacity duration-500"
            />

            {/* 2. L'image invisible qui charge en arrière-plan */}
            {nextImg && (
                <img
                    src={nextImg}
                    alt="Loading"
                    className="absolute inset-0 w-full h-full object-cover opacity-0"
                    onLoad={() => {
                        // 3. Dès que le téléchargement est fini, on bascule !
                        setCurrentImg(nextImg);
                        setNextImg(null);
                    }}
                />
            )}
        </div>
    );
}
// ---------------------------------------------

interface ControlPanelProps {
    cameraUrl: string | null;
    systemMode: string;
    handleEmergencyStop: () => void;
    handlePump: (pumpId: string, durationMs: number) => void;
}

export default function ControlPanel({ systemMode, handleEmergencyStop, handlePump }: ControlPanelProps) {
    const pumps = [
        { id: "pump_ph_minus", label: "pH -" },
        { id: "pump_ph_plus", label: "pH +" },
        { id: "pump_nutri_1", label: "Nutri A" },
        { id: "pump_nutri_2", label: "Nutri B" },
        { id: "pump_nutri_3", label: "Nutri C" }
    ];

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

            {/* CAMÉRA */}
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 flex flex-col justify-between lg:col-span-2">
                <div className="flex items-center gap-2 mb-2 text-xs font-bold text-slate-500 uppercase">
                    <Camera size={14}/> Caméra
                </div>
                <div className="aspect-video w-full rounded-xl overflow-hidden flex items-center justify-center border shadow-inner">

                    {/* On utilise notre nouvelle caméra robuste ici ! */}
                    <SmoothCamera intervalMs={10000} />

                </div>
            </div>

            {/* PANNEAU DE FORÇAGE (inchangé, on garde la version ultra-compacte) */}
            <div className="bg-white p-3 rounded-2xl shadow-sm border border-slate-200 flex flex-col lg:col-span-1 border-t-4 lg:border-t-0 lg:border-l-4 border-orange-500">
                <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-orange-600 uppercase">
                        <Power size={12}/> Panneau de Forçage
                    </div>
                </div>

                <button
                    onClick={handleEmergencyStop}
                    className="w-full mb-2 bg-red-50 hover:bg-red-600 hover:text-white text-red-600 font-black py-2 px-2 rounded-lg flex items-center justify-center gap-1.5 text-[11px] tracking-wider uppercase transition-colors border border-red-200 shadow-sm"
                >
                    <Power size={14}/> Arrêt d'urgence
                </button>

                <div className="flex flex-col gap-1.5 flex-1 justify-center">
                    {pumps.map((pump) => (
                        <div key={pump.id} className="bg-slate-50 p-1.5 px-2.5 rounded-lg border border-slate-200 flex items-center justify-between">
                            <span className="text-[10px] font-black text-slate-600 uppercase w-14 flex-shrink-0 leading-tight">
                                {pump.label}
                            </span>

                            <div className="flex gap-1.5">
                                <button
                                    onClick={() => handlePump(pump.id, 2000)}
                                    className="bg-white hover:bg-blue-50 text-blue-700 font-bold py-1 px-3 rounded border border-slate-300 text-[10px] shadow-sm transition-transform active:scale-95"
                                >
                                    2s
                                </button>

                                {systemMode !== "AUTO" && (
                                    <button
                                        onClick={() => handlePump(pump.id, 15000)}
                                        className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-1 px-3 rounded border border-slate-300 text-[10px] shadow-sm transition-transform active:scale-95"
                                    >
                                        Purge
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

        </div>
    );
}