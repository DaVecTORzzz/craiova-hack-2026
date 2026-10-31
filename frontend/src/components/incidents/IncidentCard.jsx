import React from 'react';
import { Eye, Info, Camera, Check } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import ConfidenceBar from './ConfidenceBar';

export default function IncidentCard({ incident }) {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    activeCamera,
    setSelectedCameraId,
    acknowledgeIncident,
    setActiveSnapshot,
    setShowSnapshotModal
  } = useSecurity();

  const isCritical = incident.severity === 'critical';
  const isWarning = incident.severity === 'warning';

  return (
    <div
      style={{
        backgroundColor: themeStyles.cardBg || (isDarkMode ? '#2D2D2D' : '#FFFFFF'),
        borderColor: isCritical
          ? 'rgba(215, 56, 51, 0.50)'
          : isWarning
          ? 'rgba(255, 235, 51, 0.50)'
          : 'rgba(56, 142, 60, 0.50)'
      }}
      className="rounded-xl border p-3 shadow-sm space-y-2.5 transition-all hover:scale-[1.01] hover:shadow-md relative overflow-hidden"
    >
      {/* Header Card: Severitate + Titlu + Comutator Cameră */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5">
            {isCritical && (
              <span className="w-2 h-2 rounded-full bg-[#D73833] animate-ping" />
            )}
            <span
              className={`text-[10px] font-black uppercase px-2 py-0.5 rounded tracking-wider ${
                isCritical
                  ? 'bg-[#D73833] text-white'
                  : isWarning
                  ? 'bg-[#FFEB33] text-[#1F1F1F] font-bold'
                  : 'bg-emerald-600 text-white'
              }`}
            >
              {isCritical
                ? 'CRITICAL / PERICOL'
                : isWarning
                ? 'WARNING / ATENȚIE'
                : 'CONDIȚIE SIGURĂ'}
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {incident.id}
            </span>
          </div>
          <h3 className="font-bold text-xs md:text-sm mt-1 leading-tight text-slate-900 dark:text-slate-100">
            {incident.title}
          </h3>
        </div>

        {/* Buton să comute camera la camera acestui incident */}
        <button
          onClick={() => setSelectedCameraId(incident.cameraId)}
          className={`p-1 rounded-lg text-[10px] font-mono flex items-center gap-1 border transition-colors shrink-0 ${
            activeCamera?.id === incident.cameraId
              ? 'bg-[#7EDEED] text-[#1F1F1F] border-[#7EDEED] font-bold'
              : 'border-white/10 hover:bg-white/5 text-slate-300'
          }`}
          title={`Comută vizualizarea pe ${incident.cameraId}`}
        >
          <Eye size={12} />
          <span>{incident.cameraId}</span>
        </button>
      </div>

      {/* Locație & Timestamp */}
      <div
        className="flex items-center justify-between text-[10px] font-mono text-slate-400"
      >
        <span>{incident.cameraName}</span>
        <span>{incident.detectedAt}</span>
      </div>

      {/* Confidence Score cu Gradient */}
      <ConfidenceBar score={incident.confidence} />

      {/* Explainable AI (XAI) Reasoning Block */}
      <div
        style={{
          backgroundColor: isDarkMode
            ? 'rgba(0, 0, 0, 0.35)'
            : 'rgba(241, 245, 249, 0.7)'
        }}
        className="p-2.5 rounded-lg border border-white/10 space-y-1 text-xs"
      >
        <div className="flex items-center gap-1 text-[11px] font-bold text-[#7EDEED]">
          <Info size={12} />
          <span>AI Reasoning & Cauză:</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-300">
          {incident.reasoning}
        </p>
        <div className="pt-1 text-[10px] text-[#FFEB33] font-medium">
          <span className="font-bold">Măsură sugerată:</span> {incident.actionSuggested}
        </div>
      </div>

      {/* Acțiuni: Vizualizare Captură & Acknowledge */}
      <div className="pt-1 flex items-center justify-between gap-2 border-t border-white/10">
        <button
          onClick={() => {
            setActiveSnapshot({
              id: incident.snapshotId,
              title: incident.title,
              camera: incident.cameraName,
              time: incident.detectedAt,
              reasoning: incident.reasoning
            });
            setShowSnapshotModal(true);
          }}
          className="text-[10px] font-semibold text-[#7EDEED] hover:underline flex items-center gap-1"
        >
          <Camera size={12} /> Vezi Captura Auto
        </button>

        <button
          onClick={(e) => acknowledgeIncident(incident.id, e)}
          className="px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors"
          title="Confirmare remediere / verificare completă"
        >
          <Check size={14} />
          <span>Confirmă (Rezolvat)</span>
        </button>
      </div>
    </div>
  );
}
