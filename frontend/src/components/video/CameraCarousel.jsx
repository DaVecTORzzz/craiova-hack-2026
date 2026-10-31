import React from 'react';
import { Camera, Video, WifiOff } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function CameraCarousel() {
  const { isDarkMode, themeStyles } = useTheme();
  const { cameras, activeCamera, setSelectedCameraId } = useSecurity();

  return (
    <div
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder
      }}
      className="rounded-xl border p-3 shadow-sm shrink-0 select-none"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Camera size={16} className="text-blue-500" />
          <span className="font-bold text-xs md:text-sm uppercase tracking-wide text-slate-800 dark:text-slate-200">
            Rețea Camere Sol ({cameras.length})
          </span>
        </div>
        <span style={{ color: themeStyles.textMuted }} className="text-[11px]">
          Comutare instantanee a fluxului video
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
                  ? '#1976D2'
                  : (isDarkMode ? 'rgba(255,255,255,0.1)' : '#E2E8F0'),
                backgroundColor: isSelected
                  ? (isDarkMode ? '#1E2433' : '#EFF6FF')
                  : (isDarkMode ? '#141A28' : '#FFFFFF')
              }}
              className={`min-w-[170px] md:min-w-[190px] p-2.5 rounded-xl border-2 text-left transition-all relative shrink-0 hover:scale-[1.01] shadow-sm ${
                isSelected ? 'ring-2 ring-blue-500/40' : ''
              }`}
            >
              {/* Mini-ecran previzualizare video */}
              <div
                className={`h-16 rounded-lg overflow-hidden relative flex items-center justify-center bg-gradient-to-br ${cam.previewBg} mb-2 border border-white/10`}
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

                {/* Indicator online/offline */}
                <span
                  className={`absolute top-1.5 left-1.5 w-2 h-2 rounded-full ${
                    isCamOffline ? 'bg-red-500' : 'bg-emerald-500 animate-pulse'
                  }`}
                />
              </div>

              {/* Detalii Cameră: Subtitlu elegant SUB denumire conform cerinței */}
              <div className="space-y-0.5">
                <p className="font-bold text-xs truncate leading-snug text-slate-900 dark:text-slate-100">
                  {cam.name}
                </p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-tight">
                  {cam.subtitle || cam.id}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
