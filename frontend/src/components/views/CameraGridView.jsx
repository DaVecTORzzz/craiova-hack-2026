import React from 'react';
import { useSecurity } from '../../context/SecurityContext';
import { useTheme } from '../../context/ThemeContext';
import BoundingBox from '../video/BoundingBox';
import { WifiOff, Maximize2 } from 'lucide-react';

export default function CameraGridView() {
  const { themeStyles } = useTheme();
  const { cameras, setSelectedCameraId, setCurrentView } = useSecurity();

  // Selectează primele 4 camere pentru matricea 2x2
  const gridCameras = cameras.slice(0, 4);

  return (
    <div className="flex-1 p-4 overflow-y-auto h-full flex flex-col select-none">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div>
          <h2 className="text-base md:text-lg font-black uppercase tracking-tight">
            Matrice Video Multi-Cameră (Quad View 2x2)
          </h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-mono">
            Monitorizare sincronă fluxuri critice aeroport
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 min-h-[500px]">
        {gridCameras.map((cam) => {
          const isOffline = cam.status === 'offline';

          return (
            <div
              key={cam.id}
              style={{
                backgroundColor: themeStyles.panelBg,
                borderColor: themeStyles.panelBorder
              }}
              className="rounded-xl border p-2 flex flex-col shadow-md relative overflow-hidden"
            >
              <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-white/10 text-xs">
                <span className="font-bold font-mono flex items-center gap-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      !isOffline ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
                    }`}
                  />
                  {cam.id} • {cam.name}
                </span>

                <button
                  onClick={() => {
                    setSelectedCameraId(cam.id);
                    setCurrentView('fullscreen');
                  }}
                  className="p-1 rounded hover:bg-white/10 opacity-70 hover:opacity-100"
                  title="Extinde în mod Full-Screen"
                >
                  <Maximize2 size={13} />
                </button>
              </div>

              <div className="flex-1 relative rounded-lg overflow-hidden bg-black border border-slate-700 flex items-center justify-center min-h-[180px]">
                {isOffline ? (
                  <div className="text-center p-4 text-red-500 font-mono">
                    <WifiOff size={24} className="mx-auto mb-1 animate-pulse" />
                    <span className="text-xs font-bold">SEMNAL PIERDUT</span>
                  </div>
                ) : (
                  <div
                    className={`w-full h-full bg-gradient-to-br ${cam.previewBg} relative flex items-center justify-center`}
                  >
                    <span className="text-white/30 font-mono text-xs uppercase">
                      {cam.name}
                    </span>
                    {cam.boxes && cam.boxes.map((b) => (
                      <BoundingBox key={b.id} box={b} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
