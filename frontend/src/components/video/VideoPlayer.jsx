import React, { useState, useEffect } from 'react';
import { Camera, Maximize2, WifiOff, RefreshCw, Clock, Plane, Video } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import BoundingBox from './BoundingBox';

export default function VideoPlayer({ camera, onMaximize }) {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    activeCamera,
    setSelectedCameraId,
    takeManualSnapshot,
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

  return (
    <div
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder
      }}
      className="rounded-xl border p-3 flex flex-col shadow-lg flex-1 min-h-[360px] md:min-h-[440px] relative overflow-hidden"
    >
      {/* Header-ul Player-ului Video */}
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2">
          <span
            className={`w-3 h-3 rounded-full ${
              !isOffline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
            }`}
          />
          <span className="font-bold text-sm tracking-wide">
            {currentCam.id} - {currentCam.name}
          </span>
          <span
            style={{ backgroundColor: themeStyles.cardBg }}
            className="text-[10px] font-mono px-2 py-0.5 rounded border border-white/10 hidden sm:inline"
          >
            {currentCam.zone}
          </span>
        </div>

        {/* Butoane Acțiuni */}
        <div className="flex items-center gap-2">
          {!isOffline && (
            <button
              onClick={takeManualSnapshot}
              style={{ backgroundColor: themeStyles.accentColor }}
              className={`px-2.5 py-1 rounded text-xs font-bold flex items-center gap-1 shadow hover:scale-105 transition-transform ${
                isDarkMode ? 'text-white' : 'text-slate-950'
              }`}
              title="Realizează captură manuală instantanee"
            >
              <Camera size={14} />
              <span className="hidden md:inline">Captură</span>
            </button>
          )}

          {onMaximize && (
            <button
              onClick={onMaximize}
              style={{ backgroundColor: themeStyles.cardBg }}
              className="p-1.5 rounded hover:bg-white/10 border border-white/10 text-xs transition-colors"
              title="Deschide în modul Full-Screen"
            >
              <Maximize2 size={15} />
            </button>
          )}
        </div>
      </div>

      {/* Ecranul Video Propriu-Zis */}
      <div className="flex-1 relative rounded-lg overflow-hidden bg-black border border-slate-700 flex items-center justify-center select-none shadow-inner min-h-[280px]">
        {/* CAZUL 1: CAMERA OFFLINE -> SEMNAL PIERDUT */}
        {isOffline ? (
          <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center bg-zinc-950 text-white relative">
            <div
              className="absolute inset-0 opacity-20 pointer-events-none"
              style={{
                backgroundImage:
                  'repeating-linear-gradient(0deg, rgba(255,255,255,0.05), rgba(255,255,255,0.05) 1px, transparent 1px, transparent 2px)'
              }}
            />

            <div className="w-16 h-16 rounded-full bg-red-950/80 border-2 border-red-500/50 flex items-center justify-center mb-3 animate-pulse">
              <WifiOff size={32} className="text-red-500" />
            </div>

            <h2 className="text-2xl md:text-3xl font-black text-red-500 tracking-widest font-mono">
              SEMNAL PIERDUT
            </h2>
            <p className="text-xs text-slate-400 font-mono mt-1 max-w-sm">
              Fluxul video RTSP/WebRTC nu răspunde. Conexiunea cu nodul de cameră{' '}
              <span className="text-white font-bold">{currentCam.id}</span> a fost întreruptă.
            </p>

            <div className="mt-4 flex items-center gap-2">
              <button
                onClick={() => showToast(`Reîncercare conexiune RTSP pentru ${currentCam.id}...`)}
                className="px-3 py-1.5 rounded bg-red-600 hover:bg-red-700 text-white font-mono text-xs font-bold flex items-center gap-1.5 shadow"
              >
                <RefreshCw size={13} /> Reîncearcă Conexiunea
              </button>
              <button
                onClick={() => setSelectedCameraId('CAM-04')}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs font-bold"
              >
                Comută pe CAM-04 (Online)
              </button>
            </div>
          </div>
        ) : (
          // CAZUL 2: CAMERA ONLINE -> SIMULARE FEED + BOUNDING BOXES
          <div
            className={`w-full h-full bg-gradient-to-br ${currentCam.previewBg} relative overflow-hidden flex items-center justify-center`}
          >
            {/* Grilă de fundal */}
            <div
              className="absolute inset-0 opacity-15 pointer-events-none"
              style={{
                backgroundImage:
                  'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                backgroundSize: '32px 32px'
              }}
            />

            {/* Icon & Scenă de fundal */}
            <div className="relative text-center opacity-40 select-none">
              <Plane size={80} className="mx-auto text-slate-400 mb-2" />
              <p className="font-mono font-black text-white text-base md:text-lg tracking-wider">
                {currentCam.name.toUpperCase()}
              </p>
              <p className="font-mono text-xs text-slate-300">
                AI COMPUTER VISION ACTIVE • LIVE TRACKING {currentCam.fps} FPS
              </p>
            </div>

            {/* Bounding Boxes */}
            {currentCam.boxes && currentCam.boxes.map((box) => (
              <BoundingBox key={box.id} box={box} />
            ))}

            {/* HUD Video Superior */}
            <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/75 backdrop-blur-sm px-2.5 py-1 rounded text-[11px] font-mono text-white border border-white/10 shadow">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
              <span className="font-bold">REC</span>
              <span>|</span>
              <span>{currentCam.resolution}</span>
              <span>|</span>
              <span>{currentCam.fps} FPS</span>
            </div>

            {/* HUD Video Inferior: Live Clock */}
            <div className="absolute bottom-3 right-3 bg-black/75 backdrop-blur-sm px-2.5 py-1 rounded text-[11px] font-mono text-white border border-white/10 shadow flex items-center gap-2">
              <Clock size={12} className="text-indigo-400" />
              <span>LIVE: {currentTime}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
