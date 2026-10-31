import React from 'react';
import { AlertOctagon, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useSecurity } from '../../context/SecurityContext';

export default function BoundingBox({ box }) {
  const { showToast } = useSecurity();

  const isCritical = box.type === 'critical';
  const isWarning = box.type === 'warning';
  const isResolved = box.type === 'resolved';

  let borderColor = 'border-emerald-400';
  let bgColor = 'bg-emerald-500/15';
  let tagBg = 'bg-emerald-600 text-white';
  let pulseRing = 'ring-emerald-400/40';

  if (isCritical) {
    borderColor = 'border-red-500';
    bgColor = 'bg-red-500/20';
    tagBg = 'bg-red-600 text-white animate-pulse';
    pulseRing = 'ring-red-500/50';
  } else if (isWarning) {
    borderColor = 'border-amber-400';
    bgColor = 'bg-amber-400/20';
    tagBg = 'bg-amber-500 text-slate-900';
    pulseRing = 'ring-amber-400/40';
  }

  return (
    <div
      style={{
        top: box.coords.top,
        left: box.coords.left,
        width: box.coords.width,
        height: box.coords.height
      }}
      className={`absolute border-2 ${borderColor} ${bgColor} rounded-sm transition-all duration-300 ring-2 ${pulseRing} pointer-events-auto cursor-pointer group shadow-xl`}
      onClick={() => {
        showToast(`Obiect AI: ${box.label} [Tracking ID: ${box.trackingId}]`);
      }}
    >
      {/* Etichetă superioară AI Tracking */}
      <div
        className={`absolute -top-7 left-0 px-2 py-0.5 rounded text-[11px] font-bold tracking-wider flex items-center gap-1.5 shadow-md whitespace-nowrap ${tagBg}`}
      >
        {isCritical && <AlertOctagon size={13} className="animate-spin" />}
        {isWarning && <AlertTriangle size={13} />}
        {isResolved && <CheckCircle2 size={13} />}
        <span>{box.label}</span>
        <span className="opacity-80 text-[9px] font-mono">[{box.trackingId}]</span>
      </div>

      {/* Colțuri stil HUD Tactic */}
      <div className="absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 border-white opacity-80" />
      <div className="absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 border-white opacity-80" />
      <div className="absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 border-white opacity-80" />
      <div className="absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 border-white opacity-80" />

      {/* Tooltip la hover cu detalii detecție */}
      <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-full mb-8 left-1/2 -translate-x-1/2 w-48 p-2 rounded bg-slate-950/95 text-white text-[11px] pointer-events-none z-30 shadow-xl border border-slate-700">
        <p className="font-semibold text-slate-200">{box.label}</p>
        <p className="text-[10px] text-slate-400 mt-1">{box.details}</p>
      </div>
    </div>
  );
}
