import {Activity, Power, Droplets, Wrench, Cpu} from 'lucide-react';

interface HeaderProps {
    isConnected: boolean;
    systemMode: string;
    isPendingMode: boolean;
    handleModeChange: (mode: string) => void;
    onOpenSettings: () => void;
}

export default function Header({ isConnected, systemMode, isPendingMode, handleModeChange, onOpenSettings }: HeaderProps) {
    return (
        <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md shadow-sm border-b border-slate-200 px-3 sm:px-4 py-2 sm:py-3 flex justify-between items-center gap-2">

            {/* LOGO & TITRE */}
            <div className="flex items-center gap-2 shrink-0">
                <Droplets className="text-blue-600 animate-pulse" size={24}/>
                <h1 className="hidden sm:block text-lg font-black tracking-tight text-slate-800">HYDROSTACK</h1>
            </div>

            {/* CONTROLES DROITE */}
            <div className="flex items-center gap-2 sm:gap-4 justify-end flex-wrap">

                {/* BOUTON CONFIG MATÉRIELLE */}
                <button
                    onClick={onOpenSettings}
                    className="flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 p-2 sm:px-3 sm:py-1.5 rounded-lg border border-slate-200 text-xs font-bold transition-colors"
                    title="Configuration ESP32"
                >
                    <Cpu size={16} />
                    <span className="hidden sm:inline">ESP32</span>
                </button>

                {/* STATUT CONNEXION */}
                <div className="flex items-center gap-1.5 bg-slate-50 p-2 sm:px-2.5 sm:py-1 rounded-full border text-xs font-bold" title={isConnected ? "ONLINE" : "OFFLINE"}>
                    <div className={`w-2.5 h-2.5 sm:w-2 sm:h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}/>
                    <span className="hidden sm:inline">{isConnected ? "ONLINE" : "OFFLINE"}</span>
                </div>

                {/* SÉLECTEUR DE MODE */}
                <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800 relative">
                    {isPendingMode && (
                        <div className="absolute inset-0 bg-slate-900/50 rounded-lg flex items-center justify-center z-10 backdrop-blur-[1px]">
                            <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                        </div>
                    )}

                    {[
                        {
                            id: "AUTO",
                            icon: <Activity size={16}/>,
                            label: "Auto",
                            activeClass: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        },
                        {
                            id: "MANUAL",
                            icon: <Power size={16}/>,
                            label: "Manuel",
                            activeClass: "bg-orange-500/20 text-orange-400 border border-orange-500/30"
                        },
                        {
                            id: "MAINTENANCE",
                            icon: <Wrench size={16}/>,
                            label: "Maint.",
                            activeClass: "bg-red-500/20 text-red-400 border border-red-500/30"
                        }
                    ].map((mode) => (
                        <button
                            key={mode.id}
                            onClick={() => handleModeChange(mode.id)}
                            disabled={isPendingMode}
                            title={mode.label}
                            className={`p-2 sm:px-4 sm:py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all 
                                ${systemMode === mode.id ? mode.activeClass : 'text-slate-500 hover:text-slate-300'}
                            `}
                        >
                            {mode.icon}
                            <span className="hidden md:inline">{mode.label}</span>
                        </button>
                    ))}
                </div>
            </div>
        </header>
    );
}