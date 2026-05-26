import { useState, useEffect, useRef } from 'react';
import { Wrench, Droplets, Activity, Thermometer, Trash2, PlusCircle, CheckCircle, RefreshCw, ArrowRight } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceDot } from 'recharts';
import { hydroApi } from '../services/api';

// --- FONCTION MATHÉMATIQUE : RÉGRESSION LINÉAIRE ---
function calculateLinearRegression(points: { volt: number, value: number }[]) {
    if (points.length < 2) return null;
    const n = points.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

    points.forEach(p => {
        sumX += p.volt;
        sumY += p.value;
        sumXY += p.volt * p.value;
        sumXX += p.volt * p.volt;
    });

    const denominator = (n * sumXX - sumX * sumX);
    if (denominator === 0) return null;

    const a = (n * sumXY - sumX * sumY) / denominator;
    const b = (sumY - a * sumX) / n;

    return { a, b };
}

// --- SOUS-COMPOSANT : MODULE DE CALIBRATION ---
interface CalibrationModuleProps {
    type: 'ph' | 'ec';
    label: string;
    unit: string;
    icon: React.ReactNode;
    liveValue: number;      // Valeur calculée actuelle (ex: 6.5 pH)
    liveValueRaw: number;   // Tension brute actuelle (ex: 2.15 V)
    waterTemp: number;
    oldA: number;
    oldB: number;
}

const CalibrationModule = ({ type, label, unit, icon, waterTemp, oldA, oldB, liveValueRaw }: CalibrationModuleProps) => {
    const [points, setPoints] = useState<{ id: string, volt: number, value: number }[]>([]);
    const [isAcquiring, setIsAcquiring] = useState(false);
    const [pendingVolt, setPendingVolt] = useState<number | null>(null);
    const [bufferInput, setBufferInput] = useState<string>(type === 'ph' ? "7.0" : "1.4");
    const [isSaving, setIsSaving] = useState(false);

    const quickBuffers = type === 'ph' ? [4.0, 7.0, 10.0] : [1.4, 2.8];

    // Astuce React : On garde toujours un oeil sur la TOUTE DERNIÈRE tension brute
    // pour éviter le problème des "stale closures" dans le setTimeout
    const latestRawVolt = useRef(liveValueRaw);
    useEffect(() => {
        latestRawVolt.current = liveValueRaw;
    }, [liveValueRaw]);

    // Lancement de l'acquisition (Demande à l'ESP32)
    const handleAcquire = async () => {
        setIsAcquiring(true);
        try {
            // 1. On ordonne à l'ESP32 de lire cette sonde spécifiquement
            await hydroApi.triggerAcquisition(type);

            // 2. On attend 2.5s (le temps que l'ESP32 lisse et que la BDD mette à jour le front)
            setTimeout(() => {
                // 3. On fige la toute dernière valeur reçue
                setPendingVolt(parseFloat(latestRawVolt.current.toFixed(3)));
                setIsAcquiring(false);
            }, 2500);

        } catch (error) {
            alert(`Erreur de communication avec la sonde ${type.toUpperCase()}.`);
            setIsAcquiring(false);
        }
    };

    // Validation d'un point
    const handleAddPoint = () => {
        if (pendingVolt === null) return;
        const numericValue = parseFloat(bufferInput);
        if (isNaN(numericValue)) return alert("Valeur tampon invalide.");

        setPoints([...points, { id: Date.now().toString(), volt: pendingVolt, value: numericValue }]);
        setPendingVolt(null);
    };

    const removePoint = (id: string) => {
        setPoints(points.filter(p => p.id !== id));
    };

    // Envoi de la calibration finale à FastAPI
    const handleFinalizeCalibration = async (newA: number, newB: number) => {
        setIsSaving(true);
        try {
            const sensorId = `mock_node2_wet_${type}`;
            await hydroApi.saveCalibration(sensorId, newA, newB);

            alert(`✅ Sonde ${type.toUpperCase()} calibrée avec succès.\nNouvelle équation : y = ${newA.toFixed(3)}x + ${newB.toFixed(3)}`);
            setPoints([]);
        } catch (error) {
            alert("Erreur lors de la sauvegarde de la calibration.");
        } finally {
            setIsSaving(false);
        }
    };

    const newModel = calculateLinearRegression(points);

    // Génération des courbes pour Recharts
    const chartData = [];
    for (let i = 0; i <= 3.3; i += 0.3) {
        const v = parseFloat(i.toFixed(2));
        chartData.push({
            volt: v,
            oldY: parseFloat((oldA * v + oldB).toFixed(2)),
            newY: newModel ? parseFloat((newModel.a * v + newModel.b).toFixed(2)) : null
        });
    }

    return (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col h-full overflow-hidden">
            {/* EN-TÊTE */}
            <div className="bg-slate-50 px-5 py-4 border-b border-slate-100 flex justify-between items-center">
                <div className="flex items-center gap-3 text-slate-800 font-bold">
                    <div className={`p-2 rounded-lg ${type === 'ph' ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'}`}>
                        {icon}
                    </div>
                    {label}
                </div>
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 bg-white px-3 py-1.5 rounded-full border border-slate-200 shadow-sm">
                    <Thermometer size={14} className="text-orange-500"/>
                    {waterTemp.toFixed(1)}°C
                </div>
            </div>

            <div className="p-5 flex-grow flex flex-col space-y-6">
                {/* ZONE 1 : INSTRUCTIONS & ACQUISITION */}
                <div className="space-y-4">
                    <p className="text-xs text-slate-500 font-medium">
                        1. Plongez la sonde et le thermomètre dans la solution tampon.<br/>
                        2. Attendez la stabilisation, puis lancez une acquisition isolée.
                    </p>

                    {pendingVolt === null ? (
                        <button
                            onClick={handleAcquire}
                            disabled={isAcquiring}
                            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-100 disabled:text-slate-400 text-white font-bold py-3.5 rounded-xl transition-all shadow-sm flex items-center justify-center gap-2 text-sm"
                        >
                            {isAcquiring ? (
                                <><RefreshCw size={18} className="animate-spin" /> Lecture matérielle isolée en cours...</>
                            ) : (
                                "Demander une acquisition à la sonde"
                            )}
                        </button>
                    ) : (
                        <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl space-y-4 animate-in zoom-in-95 duration-200">
                            <div className="flex justify-between items-center">
                                <span className="text-xs font-bold text-blue-800 uppercase tracking-wider">Tension Acquise</span>
                                <span className="text-xl font-mono font-black text-blue-700">{pendingVolt} V</span>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">Quelle est la valeur de cette solution ?</label>
                                <div className="flex gap-2">
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={bufferInput}
                                        onChange={(e) => setBufferInput(e.target.value)}
                                        className="w-24 bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-800 font-mono font-bold focus:outline-none focus:border-blue-500 text-sm shadow-sm"
                                    />
                                    <div className="flex gap-1 flex-grow">
                                        {quickBuffers.map(val => (
                                            <button
                                                key={val}
                                                onClick={() => setBufferInput(val.toFixed(1))}
                                                className="flex-1 bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 rounded-lg text-xs font-mono font-bold transition-colors shadow-sm"
                                            >
                                                {val.toFixed(1)} {unit}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-2 pt-2">
                                <button onClick={() => setPendingVolt(null)} className="flex-1 bg-white border border-slate-300 text-slate-600 font-bold py-2 rounded-lg text-xs">Annuler</button>
                                <button onClick={handleAddPoint} className="flex-[2] bg-blue-600 text-white font-bold py-2 rounded-lg text-xs shadow-sm flex items-center justify-center gap-2">
                                    <PlusCircle size={16}/> Valider ce point
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* ZONE 2 : GRAPHIQUE */}
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-xl">
                    <div className="h-48 w-full text-xs">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 10, right: 10, bottom: 10, left: -20 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="volt" stroke="#64748b" type="number" domain={[0, 3.3]} label={{ value: 'Tension (V)', position: 'insideBottomRight', offset: -5 }} />
                                <YAxis stroke="#64748b" domain={type === 'ph' ? [0, 14] : [0, 4]} label={{ value: unit, angle: -90, position: 'insideLeft' }} />
                                <Tooltip />
                                <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: '11px' }} />

                                <Line type="monotone" dataKey="oldY" name="Courbe actuelle" stroke="#94a3b8" strokeDasharray="4 4" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                                {newModel && (
                                    <Line type="monotone" dataKey="newY" name="Nouvelle calibration" stroke="#2563eb" strokeWidth={2} dot={false} isAnimationActive={false} />
                                )}
                                {points.map((p) => (
                                    <ReferenceDot key={p.id} x={p.volt} y={p.value} r={6} fill="#f59e0b" stroke="#fff" strokeWidth={2} />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* ZONE 3 : LISTE DES POINTS */}
                <div className="space-y-2 flex-grow">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Points d'étalonnage ({points.length})</span>
                    {points.length === 0 ? (
                        <div className="text-center py-4 border border-dashed border-slate-200 rounded-lg text-slate-400 text-xs font-medium">
                            Aucun point enregistré.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {points.map((p, i) => (
                                <div key={p.id} className="flex justify-between items-center bg-white border border-slate-200 p-2.5 rounded-lg shadow-sm font-mono text-sm">
                                    <span className="text-slate-500 font-bold">P{i+1}</span>
                                    <span className="text-slate-800">{p.volt.toFixed(3)} V</span>
                                    <ArrowRight size={14} className="text-slate-300"/>
                                    <span className="text-blue-600 font-bold">{p.value.toFixed(2)} {unit}</span>
                                    <button onClick={() => removePoint(p.id)} className="text-red-400 hover:text-red-600 hover:bg-red-50 p-1.5 rounded transition-colors">
                                        <Trash2 size={16}/>
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ZONE 4 : EXTENSION DE VALIDATION */}
            {newModel && (
                <div className="bg-emerald-50 border-t border-emerald-100 p-5 animate-in slide-in-from-bottom-4 duration-300">
                    <div className="flex flex-col items-center text-center space-y-3">
                        <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Modèle Mathématique Calculé</span>
                        <code className="text-sm font-mono font-black text-emerald-700 bg-white px-4 py-2 rounded-lg border border-emerald-200 shadow-sm w-full">
                            a = {newModel.a.toFixed(3)} ; b = {newModel.b.toFixed(3)}
                        </code>
                        <button
                            onClick={() => handleFinalizeCalibration(newModel.a, newModel.b)}
                            disabled={isSaving}
                            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 rounded-xl shadow-md flex items-center justify-center gap-2 transition-transform active:scale-95"
                        >
                            {isSaving ? "Sauvegarde..." : `Calibrer la sonde avec a=${newModel.a.toFixed(2)} et b=${newModel.b.toFixed(2)}`}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

// --- VUE PRINCIPALE ---
export default function MaintenanceView({ liveData }: { liveData: any }) {
    return (
        <div className="space-y-4 max-w-7xl mx-auto">
            <div className="bg-white border border-red-200 rounded-2xl p-5 shadow-sm flex items-start gap-4 border-l-4 border-l-red-500">
                <Wrench size={28} className="text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                    <h2 className="text-slate-800 font-black text-base tracking-tight uppercase">Atelier d'Étalonnage Multipoints</h2>
                    <p className="text-slate-500 text-xs mt-1 leading-relaxed">
                        Le système nécessite au minimum <strong>2 points de mesure</strong> pour calculer la pente (<code className="bg-slate-100 px-1 rounded">a</code>) et l'ordonnée à l'origine (<code className="bg-slate-100 px-1 rounded">b</code>) de l'équation de la sonde.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
                <CalibrationModule
                    type="ph"
                    label="Étalonnage Sonde pH"
                    unit="pH"
                    icon={<Droplets size={20} />}
                    liveValue={liveData.ph}
                    liveValueRaw={liveData.ph_raw || 0}
                    waterTemp={liveData.water_temp}
                    oldA={-3.140}
                    oldB={14.200}
                />

                <CalibrationModule
                    type="ec"
                    label="Étalonnage Sonde EC"
                    unit="mS/cm"
                    icon={<Activity size={20} />}
                    liveValue={liveData.ec}
                    liveValueRaw={liveData.ec_raw || 0}
                    waterTemp={liveData.water_temp}
                    oldA={1.050}
                    oldB={0.020}
                />
            </div>
        </div>
    );
}