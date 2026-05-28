interface WaterLevelGaugeProps {
    value: number;
    config: {
        target: number;
        refill: number;
        max: number;
        critical: number;
        min: number;
        maxBound: number;
    };
}

export default function WaterLevelGauge({ value, config }: WaterLevelGaugeProps) {
    const safeValue = Math.max(0, Math.min(value, config.maxBound));
    const percentage = (safeValue / config.maxBound) * 100;

    const isDanger = value <= config.critical || value >= config.max;
    const waterColor = isDanger
        ? "bg-gradient-to-t from-red-600 to-red-400 animate-pulse"
        : "bg-gradient-to-t from-blue-600 to-blue-400";

    // ==========================================
    // NOUVEL ALGO : "RELAXATION BIDIRECTIONNELLE"
    // ==========================================
    const minGap = 8; // 8% correspond à la hauteur exacte d'une ligne de texte (environ 14px)

    let labels = [
        { id: 'max', val: config.max, text: `MAX (${config.max})`, color: 'text-red-500', lineCls: 'border-red-400 border-dashed' },
        { id: 'target', val: config.target, text: `CIBLE (${config.target})`, color: 'text-blue-500', lineCls: 'border-blue-400 border-dashed' },
        { id: 'refill', val: config.refill, text: `REFILL (${config.refill})`, color: 'text-amber-500', lineCls: 'border-amber-500 border-dashed' },
        { id: 'critical', val: config.critical, text: `CRIT. (${config.critical})`, color: 'text-red-600', lineCls: 'border-red-600' }
    ].map(l => {
        const pct = (l.val / config.maxBound) * 100;
        return { ...l, linePct: pct, textPct: pct };
    }).sort((a, b) => b.val - a.val);

    // On lisse les collisions en douceur (le haut monte, le bas descend)
    for(let iter = 0; iter < 3; iter++) { // 3 passes suffisent pour équilibrer
        for (let i = 0; i < labels.length - 1; i++) {
            let diff = labels[i].textPct - labels[i+1].textPct;
            if (diff < minGap) {
                let overlap = minGap - diff;
                labels[i].textPct += overlap / 2;     // Pousse vers le haut
                labels[i+1].textPct -= overlap / 2;   // Pousse vers le bas
            }
        }
    }

    return (
        <div className="flex gap-4 h-[180px] w-full mt-4 relative">

            {/* LE RÉSERVOIR */}
            <div className="relative w-16 h-full bg-slate-50 rounded-[2rem] border border-slate-200 overflow-hidden shadow-inner flex-shrink-0 z-10">
                <div
                    className={`absolute bottom-0 w-full transition-all duration-1000 ease-in-out ${waterColor}`}
                    style={{ height: `${percentage}%` }}
                >
                    <div className="absolute top-0 left-0 w-full h-1.5 bg-white/30"></div>
                </div>
            </div>

            {/* L'ÉCHELLE ET LES LABELS */}
            <div className="relative flex-1 h-full">

                {/* LIGNES (Ne bougent jamais) */}
                {labels.map(l => (
                    <div
                        key={`line-${l.id}`}
                        className={`absolute w-6 border-b ${l.lineCls}`}
                        style={{ bottom: `${l.linePct}%`, transform: 'translateY(50%)' }}
                    ></div>
                ))}

                {/* TEXTES (Légèrement décalés pour s'empiler proprement) */}
                {labels.map(l => (
                    <div
                        key={`text-${l.id}`}
                        className={`absolute left-8 flex items-center ${l.color} transition-all duration-300`}
                        style={{ bottom: `${l.textPct}%`, transform: 'translateY(50%)' }}
                    >
                        <span className="text-[10px] font-black uppercase tracking-wider bg-white px-1 rounded leading-none py-0.5">
                            {l.text}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}