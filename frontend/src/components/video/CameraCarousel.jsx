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
          <Camera size={16} className="text-[#7EDEED]" />
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
          const isSelected = cam.id === activeCamera?.id;
          const isCamOffline = cam.status === 'offline';

          return (
            <button
              key={cam.id}
              onClick={() => setSelectedCameraId(cam.id)}
              style={{
                borderColor: isSelected
                  ? '#7EDEED'
                  : (isDarkMode ? 'rgba(255,255,255,0.1)' : '#E5E7EB'),
                backgroundColor: isSelected
                  ? (isDarkMode ? '#2D2D2D' : '#F5F5F5')
                  : (isDarkMode ? '#1F1F1F' : '#FFFFFF')
              }}
              className={`min-w-[170px] md:min-w-[190px] p-2.5 rounded-xl border-2 text-left transition-all relative shrink-0 hover:scale-[1.01] shadow-sm ${
                isSelected ? 'ring-2 ring-[#7EDEED]/50 font-bold' : ''
              }`}
            >
              {/* Mini-ecran previzualizare video */}
              <div
                className={`h-16 rounded-lg overflow-hidden relative flex items-center justify-center bg-gradient-to-br ${cam.previewBg || 'from-slate-900 to-black'} mb-2 border border-white/10`}
              >
                {isCamOffline ? (
                  <div className="text-center">
                    <WifiOff size={16} className="text-[#D73833] mx-auto" />
                    <span className="text-[9px] font-mono text-[#D73833] font-bold">
                      OFFLINE
                    </span>
                  </div>
                ) : (
                  <>
                    <Video size={20} className="text-slate-400 opacity-60" />
                    <span className="absolute bottom-1 right-1 text-[8px] font-mono bg-black/80 px-1 py-0.5 rounded text-white">
                      {cam.resolution?.split(' ')?.[0] || '4K'}
                    </span>
                  </>
                )}
              </div>

              {/* Informații cameră */}
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs truncate text-slate-800 dark:text-slate-200">
                  {cam.name}
                </span>
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    !isCamOffline ? 'bg-emerald-500' : 'bg-[#D73833]'
                  }`}
                />
              </div>

              <p className="text-[10px] text-slate-400 truncate mt-0.5">
                {cam.subtitle}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
