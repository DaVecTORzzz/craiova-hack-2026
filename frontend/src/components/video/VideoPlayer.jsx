import React, { useState } from 'react';
import { Camera, Maximize2, AlertTriangle, Video, WifiOff } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import BoundingBox from './BoundingBox';

export default function VideoPlayer({ camera, onMaximize }) {
  const { isDarkMode, themeStyles } = useTheme();
  const { activeCamera, captureReferenceFrame, showToast } = useSecurity();
  const [streamError, setStreamError] = useState(false);

  const currentCam = camera || activeCamera;
  const isOffline = currentCam.status === 'offline';
  const showLiveStream = Boolean(currentCam.stream_url && !streamError && !isOffline);

  const handleCapture = () => {
    captureReferenceFrame(currentCam.id);
  };

  return (
    <div
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder
      }}
      className="rounded-xl border p-3 flex flex-col shadow-sm flex-1 relative overflow-hidden"
    >
      {/* Header-ul Player-ului Video: Nume și Subtitlu dedesubt conform cerinței */}
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10 shrink-0">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                !isOffline ? 'bg-emerald-500 animate-pulse' : 'bg-[#D73833]'
              }`}
            />
            <span className="font-bold text-sm tracking-wide text-slate-900 dark:text-slate-100">
              {currentCam.name}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#7EDEED]/10 text-[#7EDEED] font-bold border border-[#7EDEED]/20 hidden sm:inline">
              {currentCam.category || 'Apron'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 pl-4.5 font-normal mt-0.5">
            {currentCam.subtitle}
          </p>
        </div>

        {/* Butoane Acțiuni */}
        <div className="flex items-center gap-2">
          {!isOffline && (
            <button
              onClick={handleCapture}
              className="px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 shadow-sm bg-[#7EDEED] hover:bg-[#5ccedc] text-[#1F1F1F] transition-colors"
              title="Realizează captură manuală instantanee"
            >
              <Camera size={13} />
              <span className="hidden md:inline">Captură</span>
            </button>
          )}

          {onMaximize && (
            <button
              onClick={onMaximize}
              className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 text-xs transition-colors"
              title="Deschide în modul Full-Screen"
            >
              <Maximize2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Ecranul Video Principal (16:9 proporțional) */}
      <div className="w-full aspect-video rounded-xl overflow-hidden relative bg-black border border-slate-800 flex items-center justify-center shadow-inner">
        {isOffline ? (
          <div className="text-center p-6 text-[#D73833] font-mono">
            <WifiOff size={44} className="mx-auto mb-2 animate-bounce" />
            <h3 className="text-lg font-bold">SEMNAL CAMERA PIERDUT</h3>
            <p className="text-xs text-slate-400 mt-1">Camera este momentan offline</p>
          </div>
        ) : (
          <div className={`w-full h-full bg-gradient-to-br ${currentCam.previewBg || 'from-slate-900 to-black'} relative flex items-center justify-center overflow-hidden`}>
            {showLiveStream ? (
              <img
                src={currentCam.stream_url}
                alt={`Flux ${currentCam.id}`}
                className="w-full h-full object-cover"
                onError={() => setStreamError(true)}
              />
            ) : (
              <div className="text-center opacity-30 select-none">
                <Video size={48} className="mx-auto mb-2 text-slate-300" />
                <p className="font-mono text-xs font-bold text-white uppercase">{currentCam.name}</p>
                <p className="font-mono text-[10px] text-slate-400">
                  {streamError ? 'STREAM INDISPONIBIL • MOD TACTIC' : 'LIVE ANNOTATED STREAM'}
                </p>
              </div>
            )}

            {/* Bounding Boxes */}
            {currentCam.boxes?.map((box) => (
              <BoundingBox key={box.id} box={box} />
            ))}

            {/* Indicator LIVE */}
            <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 bg-black/80 px-2 py-0.5 rounded text-[10px] font-mono text-white border border-white/10">
              <span className="w-2 h-2 rounded-full bg-[#D73833] animate-ping" />
              <span className="font-bold text-red-400">LIVE REC</span>
              <span className="text-slate-400">|</span>
              <span>{currentCam.resolution || '4K'}</span>
            </div>

            {/* Overlay jos */}
            <div className="absolute bottom-2 left-2.5 right-2.5 flex items-center justify-between text-[11px] font-mono bg-black/70 backdrop-blur px-2.5 py-1 rounded text-white border border-white/10">
              <span className="truncate">{currentCam.name}</span>
              <span className="text-slate-300 text-[10px]">
                {currentCam.fps ? `${currentCam.fps} FPS` : '— FPS'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
