import { Activity, Power, Droplets, Wrench } from 'lucide-react';

interface HeaderProps {
    isConnected: boolean;
    systemMode: string;
    isPendingMode: boolean;
    handleModeChange: (mode: string) => void;
}

export default function Header({ isConnected, systemMode, isPendingMode, handleModeChange }: HeaderProps) {
    return (
        <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md shadow-sm border-b border-slate-200 px-4 py-3 flex justify-between items-center">
            <div className="flex items-center gap-2">
                <Droplets className="text-blue-600 animate-pulse" size={24}/>
                <h1 className="text-lg font-black tracking-tight text-slate-800">HYDROSTACK</h1>
            </div>
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-full border text-xs font-bold">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}/>
                    {isConnected ? "ONLINE" : "OFFLINE"}
                </div>
                {/* --- LE SÉLECTEUR DE MODE --- */}
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
                            label: "Maintenance",
                            activeClass: "bg-red-500/20 text-red-400 border border-red-500/30"
                        }
                    ].map((mode) => (
                        <button
                            key={mode.id}
                            onClick={() => handleModeChange(mode.id)}
                            disabled={isPendingMode}
                            className={`px-4 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 transition-all 
            ${systemMode === mode.id ? mode.activeClass : 'text-slate-500 hover:text-slate-300'}
        `}
                        >
                            {mode.icon} {mode.label}
                        </button>
                    ))}
                </div>
            </div>
        </header>
    );
}