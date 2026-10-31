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
        backgroundColor: themeStyles.cardBg,
        borderColor: isCritical
          ? 'rgba(239, 68, 68, 0.45)'
          : isWarning
          ? 'rgba(245, 158, 11, 0.45)'
          : 'rgba(16, 185, 129, 0.45)'
      }}
      className="rounded-xl border p-3 shadow-sm space-y-2.5 transition-all hover:scale-[1.01] hover:shadow-md relative overflow-hidden"
    >
      {/* Header Card: Severitate + Titlu + Comutator Cameră */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5">
            {isCritical && (
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            )}
            <span
              className={`text-[10px] font-black uppercase px-2 py-0.5 rounded tracking-wider ${
                isCritical
                  ? 'bg-red-600 text-white'
                  : isWarning
                  ? 'bg-amber-500 text-slate-900'
                  : 'bg-emerald-600 text-white'
              }`}
            >
              {isCritical
                ? 'PERICOL IMINENT'
                : isWarning
                ? 'AVERTISMENT'
                : 'REMEDIAT / CONFORM'}
            </span>
            <span className="text-[10px] font-mono opacity-70">
              {incident.id}
            </span>
          </div>
          <h3 className="font-bold text-xs md:text-sm mt-1 leading-tight">
            {incident.title}
          </h3>
        </div>

        {/* Buton să comute camera la camera acestui incident */}
        <button
          onClick={() => setSelectedCameraId(incident.cameraId)}
          style={{
            backgroundColor:
              activeCamera.id === incident.cameraId
                ? themeStyles.accentColor
                : 'transparent'
          }}
          className="p-1 rounded text-[10px] font-mono flex items-center gap-1 border border-white/10 hover:bg-white/10 shrink-0"
          title={`Comută vizualizarea pe ${incident.cameraId}`}
        >
          <Eye size={12} />
          <span>{incident.cameraId}</span>
        </button>
      </div>

      {/* Locație & Timestamp */}
      <div
        style={{ color: themeStyles.textMuted }}
        className="flex items-center justify-between text-[10px] font-mono"
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
            ? 'rgba(0, 0, 0, 0.3)'
            : 'rgba(255, 255, 255, 0.7)'
        }}
        className="p-2.5 rounded-lg border border-white/5 space-y-1 text-xs"
      >
        <div className="flex items-center gap-1 text-[11px] font-bold text-indigo-400">
          <Info size={12} />
          <span>AI Reasoning & Cauză:</span>
        </div>
        <p style={{ color: themeStyles.textMuted }} className="text-[11px] leading-relaxed">
          {incident.reasoning}
        </p>
        <div className="pt-1 text-[10px] text-amber-400 font-medium">
          <span className="font-bold">Măsură sugerată:</span> {incident.actionSuggested}
        </div>
      </div>

      {/* Acțiuni: Vizualizare Captură & Acknowledge */}
      <div className="pt-1 flex items-center justify-between gap-2">
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
          className="text-[10px] font-semibold text-slate-300 hover:text-white flex items-center gap-1 underline"
        >
          <Camera size={12} /> Vezi Captura Auto
        </button>

        <button
          onClick={(e) => acknowledgeIncident(incident.id, e)}
          style={{
            backgroundColor: isDarkMode ? '#4034AD' : '#70ED6E',
            color: isDarkMode ? '#FFFFFF' : '#0F172A'
          }}
          className="px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1.5 hover:opacity-90 transition-opacity shadow-sm"
        >
          <Check size={14} />
          <span>Marchează Rezolvat</span>
        </button>
      </div>
    </div>
  );
}
