import React from 'react';

interface ToleranceGaugeProps {
  label: string;
  value: number;
  min: number;       // Le minimum absolu affiché sur la jauge
  max: number;       // Le maximum absolu affiché sur la jauge
  minOk: number;     // Début de la zone verte
  maxOk: number;     // Fin de la zone verte
  unit?: string;
}

export default function LinearToleranceGauge({ label, value, min, max, minOk, maxOk, unit = "" }: ToleranceGaugeProps) {
  // Calcul des pourcentages pour placer les éléments en CSS (de 0% à 100%)
  const range = max - min;
  const greenStartPercent = ((minOk - min) / range) * 100;
  const greenWidthPercent = ((maxOk - minOk) / range) * 100;
  
  // Position du curseur actuel (limité entre 0 et 100 pour ne pas sortir du cadre)
  let cursorPercent = ((value - min) / range) * 100;
  cursorPercent = Math.max(0, Math.min(100, cursorPercent));

  // Détermination de la couleur du curseur (Vert si dans la zone, Rouge sinon)
  const isOk = value >= minOk && value <= maxOk;
  const cursorColor = isOk ? 'bg-green-500' : 'bg-red-500';

  return (
    <div className="flex flex-col p-5 bg-slate-50 rounded-xl border border-slate-200 shadow-sm">
      <div className="flex justify-between items-end mb-4">
        <span className="text-sm font-bold text-slate-500 uppercase tracking-wider">{label}</span>
        <div className="text-right">
          <span className={`text-3xl font-black ${isOk ? 'text-slate-800' : 'text-red-600'}`}>
            {value.toFixed(2)}
          </span>
          <span className="text-sm font-bold text-slate-400 ml-1">{unit}</span>
        </div>
      </div>

      {/* LA JAUGE GRAPHIQUE */}
      <div className="relative h-6 bg-slate-200 rounded-full overflow-hidden shadow-inner">
        
        {/* La "Zone Verte" (Optimal) */}
        <div 
          className="absolute top-0 h-full bg-green-100 border-x-2 border-green-300"
          style={{ left: `${greenStartPercent}%`, width: `${greenWidthPercent}%` }}
        />

        {/* Le Curseur de la valeur actuelle */}
        <div 
          className={`absolute top-0 h-full w-2 rounded-full shadow-md transition-all duration-700 ease-out ${cursorColor}`}
          style={{ left: `calc(${cursorPercent}% - 4px)` }}
        />
      </div>

      {/* Les étiquettes Min / Max sous la jauge */}
      <div className="flex justify-between text-xs font-medium text-slate-400 mt-2 px-1">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}