import React from 'react';
import { Video, AlertOctagon, Check } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import BoundingBox from '../video/BoundingBox';

export default function SplitFeedView() {
  const { themeStyles } = useTheme();
  const { activeCamera, filteredIncidents, acknowledgeIncident } = useSecurity();

  const isOffline = activeCamera.status === 'offline';

  return (
    <div className="flex-1 flex flex-col p-4 overflow-y-auto space-y-4 h-full select-none">
      {/* Secțiunea Superioară: Feed-ul Camerei (50%) */}
      <div
        style={{
          backgroundColor: themeStyles.panelBg,
          borderColor: themeStyles.panelBorder
        }}
        className="h-[48%] rounded-xl border p-3 flex flex-col shadow-lg shrink-0"
      >
        <div className="flex items-center justify-between mb-2 shrink-0">
          <span className="text-xs font-bold font-mono uppercase tracking-wider flex items-center gap-2">
            <Video size={16} className="text-indigo-400" />
            Feed Supraveghere Split: {activeCamera.id} - {activeCamera.name}
          </span>
          <span className="text-[11px] font-mono opacity-75">
            Rezoluție: {activeCamera.resolution}
          </span>
        </div>

        <div className="flex-1 relative rounded-lg overflow-hidden bg-black border border-slate-700 min-h-[160px]">
          {isOffline ? (
            <div className="w-full h-full flex items-center justify-center text-red-500 font-mono font-bold text-xl">
              SEMNAL PIERDUT (CAMERA OFFLINE)
            </div>
          ) : (
            <div
              className={`w-full h-full bg-gradient-to-br ${activeCamera.previewBg} relative flex items-center justify-center`}
            >
              <p className="text-white/40 font-mono text-sm uppercase">
                Feed Live Activ: {activeCamera.name}
              </p>
              {activeCamera.boxes && activeCamera.boxes.map((box) => (
                <BoundingBox key={box.id} box={box} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Secțiunea Inferioară: Probleme și Telemetrie AI (50%) */}
      <div
        style={{
          backgroundColor: themeStyles.panelBg,
          borderColor: themeStyles.panelBorder
        }}
        className="flex-1 rounded-xl border p-4 shadow-lg overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-3 shrink-0">
          <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
            <AlertOctagon size={18} className="text-red-400" />
            Probleme & Incidente Identificate pe Sector (Split View)
          </h3>
          <span className="text-xs font-mono opacity-80">
            {filteredIncidents.length} Alerte Înregistrate
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredIncidents.map((inc) => (
            <div
              key={inc.id}
              style={{
                backgroundColor: themeStyles.cardBg,
                borderColor: themeStyles.panelBorder
              }}
              className="p-3 rounded-lg border shadow-sm space-y-2 hover:border-indigo-400 transition-colors text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs truncate mr-2">{inc.title}</span>
                <span
                  className={`text-[9px] font-bold px-2 py-0.5 rounded shrink-0 ${
                    inc.severity === 'critical'
                      ? 'bg-red-600 text-white'
                      : inc.severity === 'warning'
                      ? 'bg-amber-500 text-slate-900'
                      : 'bg-emerald-600 text-white'
                  }`}
                >
                  {inc.severity.toUpperCase()}
                </span>
              </div>
              <p style={{ color: themeStyles.textMuted }} className="text-[11px] line-clamp-2">
                {inc.reasoning}
              </p>
              <div className="flex items-center justify-between pt-1 border-t border-white/10 text-[10px] font-mono">
                <span>{inc.detectedAt}</span>
                <button
                  onClick={(e) => acknowledgeIncident(inc.id, e)}
                  className="text-emerald-400 hover:underline font-bold flex items-center gap-1"
                >
                  <Check size={12} /> Rezolvă
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
