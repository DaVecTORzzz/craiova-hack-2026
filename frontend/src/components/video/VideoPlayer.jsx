import React, { useState, useEffect } from 'react';
import { Camera, Maximize2, WifiOff, RefreshCw, Clock, Video } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import BoundingBox from './BoundingBox';

export default function VideoPlayer({ camera, onMaximize }) {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    activeCamera,
    showToast
  } = useSecurity();

  const currentCam = camera || activeCamera;
  const isOffline = currentCam.status === 'offline';
  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString('ro-RO'));

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString('ro-RO'));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleCapture = () => {
    showToast(`Captură automată realizată pentru ${currentCam.id}. Salvat în arhiva de audit.`);
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
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-500/15 shrink-0">
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                !isOffline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
              }`}
            />
            <span className="font-bold text-sm tracking-wide text-slate-900 dark:text-slate-100">
              {currentCam.name}
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold border border-blue-500/20 hidden sm:inline">
              {currentCam.category || 'Apron'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 pl-4.5 font-normal mt-0.5">
            {currentCam.subtitle}
          </p>
        </div>

        {/* Butoane Acțiuni */}
        <div className="flex items-center gap-2">
          {!isOffline && (
            <button
              onClick={handleCapture}
              className="px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 shadow-sm bg-blue-600 hover:bg-blue-700 text-white transition-colors"
              title="Realizează captură manuală instantanee"
            >
              <Camera size={13} />
              <span className="hidden md:inline">Captură</span>
            </button>
          )}

          {onMaximize && (
            <button
              onClick={onMaximize}
              className="p-1.5 rounded-lg bg-slate-500/10 hover:bg-slate-500/20 border border-slate-500/20 text-slate-700 dark:text-slate-300 text-xs transition-colors"
              title="Deschide în modul Full-Screen"
            >
              <Maximize2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Ecranul Video (Restrâns ergonomic la max 320px) */}
      <div className="flex-1 relative rounded-xl overflow-hidden bg-black border border-slate-700 flex items-center justify-center select-none shadow-inner h-60 md:h-68 lg:h-72 max-h-[320px]">
        {/* CAMERA OFFLINE */}
        {isOffline ? (
          <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-zinc-950 text-white relative">
            <div className="w-14 h-14 rounded-full bg-red-950/80 border-2 border-red-500/50 flex items-center justify-center mb-2 animate-pulse">
              <WifiOff size={28} className="text-red-500" />
            </div>

            <h2 className="text-xl md:text-2xl font-black text-red-500 tracking-widest font-mono">
              SEMNAL PIERDUT
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              Camera {currentCam.id} nu transmite date. Se reîncearcă reconectarea la 5s.
            </p>
          </div>
        ) : (
          /* CAMERA ONLINE */
          <div
            className={`w-full h-full bg-gradient-to-br ${currentCam.previewBg} relative flex items-center justify-center`}
          >
            <div className="text-center opacity-30 select-none">
              <Video size={56} className="mx-auto mb-1 text-slate-300" />
              <p className="font-mono font-bold text-white text-base tracking-wide">
                {currentCam.name.toUpperCase()}
              </p>
              <p className="font-mono text-xs text-slate-300">
                AI ANNOTATION ACTIVE • {currentCam.fps} FPS
              </p>
            </div>

            {/* Bounding Boxes */}
            {currentCam.boxes &&
              currentCam.boxes.map((box) => <BoundingBox key={box.id} box={box} />)}

            {/* HUD Overlay */}
            <div className="absolute top-2.5 left-2.5 flex items-center gap-2 bg-black/80 px-2 py-1 rounded text-[10px] font-mono text-white border border-white/10 shadow">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
              <span className="font-bold text-red-400">LIVE REC</span>
              <span className="text-slate-400">|</span>
              <span>{currentTime}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
