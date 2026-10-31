import React from 'react';
import { Camera, X, Download, ShieldCheck } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function SnapshotModal() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    showSnapshotModal,
    setShowSnapshotModal,
    capturedScreenshots,
    activeSnapshot,
    setActiveSnapshot,
    showToast
  } = useSecurity();

  if (!showSnapshotModal) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in select-none">
      <div
        style={{
          backgroundColor: themeStyles.panelBg,
          borderColor: themeStyles.panelBorder,
          color: themeStyles.textColor
        }}
        className="w-full max-w-2xl rounded-2xl border p-5 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto"
      >
        {/* Header Modal */}
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <Camera size={22} className="text-indigo-400" />
            <div>
              <h3 className="font-bold text-base uppercase">
                Jurnal Capturi Automate AI (Evidence Archive)
              </h3>
              <p style={{ color: themeStyles.textMuted }} className="text-xs">
                Imagini capturate automat la detecția fiecărei anomalii cu timestamp și hash SHA-256
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              setShowSnapshotModal(false);
              setActiveSnapshot(null);
            }}
            className="p-1 rounded hover:bg-white/10 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Snapshot Selectat în Detaliu (dacă există) */}
        {activeSnapshot && (
          <div
            style={{ backgroundColor: themeStyles.cardBg }}
            className="p-4 rounded-xl border border-indigo-500/40 space-y-2.5"
          >
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-red-400 flex items-center gap-1.5">
                <ShieldCheck size={16} /> Detaliu Probă: {activeSnapshot.id}
              </span>
              <span className="font-mono text-[10px] opacity-75">{activeSnapshot.time}</span>
            </div>
            <p className="font-semibold text-xs">{activeSnapshot.title}</p>
            <p style={{ color: themeStyles.textMuted }} className="text-[11px]">
              {activeSnapshot.reasoning}
            </p>
            <div className="flex justify-end pt-1">
              <button
                onClick={() => showToast(`Fișierul ${activeSnapshot.id} a fost descărcat local.`)}
                className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1 shadow"
              >
                <Download size={13} /> Descarcă Raportul
              </button>
            </div>
          </div>
        )}

        {/* Grila de Capturi */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider opacity-80">
            Capturi Recente Salvate pe Server ({capturedScreenshots.length}):
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {capturedScreenshots.map((snap) => (
              <div
                key={snap.id}
                style={{ backgroundColor: themeStyles.cardBg }}
                className="p-3 rounded-xl border border-white/10 space-y-2 hover:border-indigo-400/50 transition-all"
              >
                <div className="h-28 rounded bg-gradient-to-br from-slate-900 to-indigo-950 flex flex-col items-center justify-center relative overflow-hidden border border-white/10">
                  <Camera size={30} className="text-white/40 mb-1" />
                  <span className="text-[10px] font-mono text-red-400 font-bold px-2 py-0.5 rounded bg-black/60 shadow">
                    {snap.title}
                  </span>
                  <span className="absolute bottom-1 right-2 text-[9px] font-mono text-slate-400">
                    {snap.time}
                  </span>
                </div>
                <div className="text-xs">
                  <p className="font-bold truncate">{snap.title}</p>
                  <p style={{ color: themeStyles.textMuted }} className="text-[10px] font-mono truncate">
                    {snap.camera}
                  </p>
                  <p className="text-[9px] font-mono text-slate-400 mt-1 truncate">
                    SHA-256: {snap.hash}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex justify-end pt-2 border-t border-white/10">
          <button
            onClick={() => {
              setShowSnapshotModal(false);
              setActiveSnapshot(null);
            }}
            style={{ backgroundColor: themeStyles.accentColor }}
            className={`px-4 py-2 rounded-lg text-xs font-bold shadow ${
              isDarkMode ? 'text-white' : 'text-slate-950'
            }`}
          >
            Închide Fereastra
          </button>
        </div>
      </div>
    </div>
  );
}
