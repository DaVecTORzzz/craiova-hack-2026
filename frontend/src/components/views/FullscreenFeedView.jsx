import React from 'react';
import { Minimize2, WifiOff, Camera, Video } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import BoundingBox from '../video/BoundingBox';

export default function FullscreenFeedView() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    activeCamera,
    cameras,
    setSelectedCameraId,
    setCurrentView,
    takeManualSnapshot
  } = useSecurity();

  const isOffline = activeCamera.status === 'offline';

  return (
    <div className="flex-1 flex flex-col p-4 overflow-y-auto h-full select-none">
      {/* Bară Superioară Full-Screen */}
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded bg-red-600 text-white font-bold text-xs uppercase flex items-center gap-1.5 shadow">
            <span className="w-2 h-2 rounded-full bg-white animate-ping" />
            PERETE VIDEO IMERSIV (FULL-SCREEN STREAM)
          </span>
          <span className="font-mono text-sm font-bold">
            {activeCamera.id} • {activeCamera.name}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {!isOffline && (
            <button
              onClick={takeManualSnapshot}
              style={{ backgroundColor: themeStyles.cardBg }}
              className="px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 hover:bg-white/10"
            >
              <Camera size={14} /> Captură
            </button>
          )}

          <button
            onClick={() => setCurrentView('dashboard')}
            style={{ backgroundColor: themeStyles.accentColor }}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 shadow ${
              isDarkMode ? 'text-white' : 'text-slate-950'
            }`}
          >
            <Minimize2 size={15} />
            Ieșire din Full-Screen
          </button>
        </div>
      </div>

      {/* Ecran Video Mare */}
      <div className="flex-1 relative rounded-xl overflow-hidden shadow-2xl bg-black border border-slate-700 min-h-[460px]">
        {isOffline ? (
          <div className="w-full h-full flex flex-col items-center justify-center p-8 bg-zinc-950 text-white">
            <WifiOff size={64} className="text-red-500 animate-bounce mb-4" />
            <h2 className="text-3xl font-black text-red-500 tracking-widest font-mono">
              SEMNAL PIERDUT
            </h2>
            <p className="text-sm text-slate-400 mt-2 font-mono">
              RTSP STREAM OFFLINE • CAMERA: {activeCamera.id}
            </p>
          </div>
        ) : (
          <>
            <div
              className={`w-full h-full bg-gradient-to-br ${activeCamera.previewBg} flex items-center justify-center relative overflow-hidden`}
            >
              {/* Grilă tactică */}
              <div
                className="absolute inset-0 opacity-15"
                style={{
                  backgroundImage:
                    'linear-gradient(rgba(255,255,255,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.15) 1px, transparent 1px)',
                  backgroundSize: '40px 40px'
                }}
              />

              <div className="relative text-center select-none opacity-40">
                <Video size={100} className="mx-auto text-slate-400 mb-3" />
                <p className="font-mono text-xl font-bold tracking-widest text-white">
                  {activeCamera.name.toUpperCase()}
                </p>
                <p className="text-xs text-slate-300 font-mono">
                  AI REAL-TIME VISION INFERENCE • {activeCamera.fps} FPS • DETECTING ANOMALIES
                </p>
              </div>

              {/* Bounding Boxes */}
              {activeCamera.boxes && activeCamera.boxes.map((box) => (
                <BoundingBox key={box.id} box={box} />
              ))}
            </div>

            {/* HUD Overlay */}
            <div className="absolute top-4 left-4 flex items-center gap-3 bg-black/80 px-3 py-1.5 rounded-lg border border-white/20 text-white text-xs font-mono shadow">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
              <span>REC: LIVE</span>
              <span>|</span>
              <span>{activeCamera.resolution}</span>
              <span>|</span>
              <span>FPS: {activeCamera.fps}</span>
            </div>

            {/* Selector flotant rapid de camere */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 bg-black/80 backdrop-blur-md p-1.5 rounded-xl border border-white/20 shadow-2xl">
              {cameras.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedCameraId(c.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-bold transition-all ${
                    c.id === activeCamera.id
                      ? 'bg-indigo-600 text-white shadow'
                      : 'text-slate-400 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {c.id}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
