import React from 'react';
import { Camera, Video, WifiOff } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function CameraCarousel() {
  const { themeStyles } = useTheme();
  const { cameras, activeCamera, setSelectedCameraId } = useSecurity();

  return (
    <div
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder
      }}
      className="rounded-xl border p-3 shadow-md shrink-0"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Camera size={16} className="text-indigo-400" />
          <span className="font-bold text-xs md:text-sm uppercase tracking-wide">
            Rețeaua de Camere CCTV ({cameras.length})
          </span>
        </div>
        <span style={{ color: themeStyles.textMuted }} className="text-[11px]">
          Click pe o miniatură pentru comutare feed
        </span>
      </div>

      {/* Lista orizontală de miniaturi */}
      <div className="flex gap-2.5 overflow-x-auto pb-1 pt-1 scrollbar-thin">
        {cameras.map((cam) => {
          const isSelected = cam.id === activeCamera.id;
          const isCamOffline = cam.status === 'offline';

          return (
            <button
              key={cam.id}
              onClick={() => setSelectedCameraId(cam.id)}
              style={{
                borderColor: isSelected
                  ? themeStyles.accentColor
                  : themeStyles.panelBorder,
                backgroundColor: isSelected
                  ? themeStyles.cardBg
                  : 'rgba(0,0,0,0.15)'
              }}
              className={`min-w-[150px] md:min-w-[170px] p-2 rounded-lg border-2 text-left transition-all relative shrink-0 hover:scale-[1.02] shadow-sm ${
                isSelected ? 'ring-2 ring-indigo-400/50' : ''
              }`}
            >
              {/* Mini-ecran previzualizare video */}
              <div
                className={`h-16 rounded overflow-hidden relative flex items-center justify-center bg-gradient-to-br ${cam.previewBg} mb-1.5 border border-white/10`}
              >
                {isCamOffline ? (
                  <div className="text-center">
                    <WifiOff size={16} className="text-red-500 mx-auto" />
                    <span className="text-[9px] font-mono text-red-400 font-bold">
                      OFFLINE
                    </span>
                  </div>
                ) : (
                  <div className="text-center opacity-60">
                    <Video size={18} className="mx-auto text-slate-300" />
                    <span className="text-[9px] font-mono text-slate-200">
                      {cam.fps} FPS
                    </span>
                  </div>
                )}

                {/* Badge alerte active */}
                {cam.incidentsCount > 0 && !isCamOffline && (
                  <span className="absolute top-1 right-1 bg-red-600 text-white text-[9px] font-bold px-1.5 rounded-full shadow">
                    {cam.incidentsCount}
                  </span>
                )}

                {/* Indicator online/offline */}
                <span
                  className={`absolute top-1 left-1 w-2 h-2 rounded-full ${
                    isCamOffline ? 'bg-red-500' : 'bg-emerald-400 animate-pulse'
                  }`}
                />
              </div>

              {/* Detalii Cameră */}
              <p className="font-bold text-xs truncate leading-tight">{cam.name}</p>
              <p
                style={{ color: themeStyles.textMuted }}
                className="text-[10px] font-mono truncate"
              >
                {cam.id} • {cam.status.toUpperCase()}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
