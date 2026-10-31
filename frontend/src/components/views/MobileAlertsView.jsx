import React, { useState, useEffect } from 'react';
import { Phone, Check, XCircle, Clock, ShieldAlert, AlertTriangle } from 'lucide-react';
import { useSecurity } from '../../context/SecurityContext';
import { STATUS_TOKENS } from '../../constants/theme';
import ConfidenceBadge from '../common/ConfidenceBadge';

export default function MobileAlertsView() {
  const {
    events,
    filterMode,
    setFilterMode,
    acknowledgeEvent,
    markFalsePositive
  } = useSecurity();

  const [selectedMobileEventId, setSelectedMobileEventId] = useState(events[0]?.event_id);
  const [countdown, setCountdown] = useState(28);

  const activeEvent = events.find((e) => e.event_id === selectedMobileEventId) || events[0];

  useEffect(() => {
    if (activeEvent?.status === 'open') {
      const timer = setInterval(() => {
        setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [activeEvent]);

  // Filtrare mobilă (Deschise, Critice, Toate)
  const mobileEvents = events.filter((e) => {
    if (filterMode === 'open') return e.status === 'open' || e.status === 'escalated';
    if (filterMode === 'critical') return e.severity === 'CRITICAL';
    return true;
  });

  return (
    <div className="flex-1 p-2 md:p-4 overflow-y-auto h-full flex flex-col items-center justify-start select-none">
      {/* Container simulator telefon 390px (Exact conform specificațiilor din PDF C-09) */}
      <div className="w-full max-w-[390px] bg-slate-900 border-2 border-slate-700 rounded-3xl p-3 shadow-2xl flex flex-col space-y-3 min-h-[640px] text-white">
        {/* Notch & Header Mobil */}
        <div className="flex items-center justify-between border-b border-white/10 pb-2 px-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-black text-xs uppercase tracking-wider">SafeTarmac Mobile PWA</span>
          </div>
          <span className="font-mono text-[10px] text-slate-400">390 px</span>
        </div>

        {/* Filtre Mobile: Deschise, Critice, Toate */}
        <div className="flex gap-1">
          {[
            { key: 'open', label: 'Deschise' },
            { key: 'critical', label: 'Critice' },
            { key: 'all', label: 'Toate' }
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilterMode(f.key)}
              className={`flex-1 py-1.5 text-center font-bold text-[11px] rounded-lg transition-colors ${
                filterMode === f.key ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Card Detaliu Alertă Activă */}
        {activeEvent && (
          <div className="bg-slate-800/90 rounded-2xl p-3 border border-white/10 space-y-2.5 shadow-lg">
            {/* Snapshot */}
            <div className="h-40 rounded-xl overflow-hidden relative bg-black border border-white/10">
              <img
                src={activeEvent.snapshot_url}
                alt="Cadru alertă blurată"
                className="w-full h-full object-cover"
              />
              <div className="absolute top-2 left-2 flex gap-1 items-center">
                <span
                  style={{
                    backgroundColor: STATUS_TOKENS[activeEvent.severity].bg,
                    color: STATUS_TOKENS[activeEvent.severity].text
                  }}
                  className="px-2 py-0.5 rounded text-[10px] font-black uppercase"
                >
                  {activeEvent.severity}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-black/70 text-white">
                  {activeEvent.camera_id}
                </span>
              </div>
            </div>

            {/* Titlu & Locație */}
            <div>
              <h3 className="font-bold text-sm leading-snug">{activeEvent.report?.what}</h3>
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">{activeEvent.report?.where}</p>
            </div>

            {/* Confidence Score formatat */}
            <div className="flex justify-between items-center text-xs">
              <ConfidenceBadge confidence={activeEvent.confidence} />
              <span className="font-mono text-[10px] text-slate-400">
                {new Date(activeEvent.detected_at).toLocaleTimeString('ro-RO')}
              </span>
            </div>

            {/* Numărătoare inversă până la escaladare (Countdown conform §5.5) */}
            {activeEvent.status === 'open' && (
              <div className="p-2 rounded-lg bg-red-950/70 border border-red-500/50 flex items-center justify-between text-xs">
                <span className="text-red-300 font-bold flex items-center gap-1">
                  <Clock size={13} /> Timp până la escaladare:
                </span>
                <span className="font-mono font-black text-red-400">00:{countdown.toString().padStart(2, '0')}s</span>
              </div>
            )}

            {/* BUTOANE MARI >= 44PX (Conform criteriului C-09) */}
            <div className="space-y-2 pt-1">
              {/* Buton Principal: Acknowledge (un singur clic) */}
              <button
                disabled={activeEvent.status === 'acknowledged'}
                onClick={(e) => acknowledgeEvent(activeEvent.event_id, e)}
                className={`w-full min-h-[44px] rounded-xl font-black text-sm flex items-center justify-center gap-2 shadow-lg transition-transform active:scale-95 ${
                  activeEvent.status === 'acknowledged'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white'
                }`}
              >
                <Check size={18} />
                <span>{activeEvent.status === 'acknowledged' ? 'CONFIRMAT (ACKED)' : 'ACKNOWLEDGE (CONFIRMĂ)'}</span>
              </button>

              <div className="grid grid-cols-2 gap-2">
                {/* Buton Secundar: Fals Pozitiv */}
                <button
                  disabled={activeEvent.status === 'false_positive'}
                  onClick={() => markFalsePositive(activeEvent.event_id, 'Feedback din PWA Mobil')}
                  className="min-h-[44px] rounded-xl font-bold text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 border border-white/10 flex items-center justify-center gap-1.5 active:scale-95"
                >
                  <XCircle size={15} />
                  <span>Fals Pozitiv</span>
                </button>

                {/* Buton Radio: Link tel: către numărul configurat (§5.5) */}
                <a
                  href="tel:+40700112233"
                  className="min-h-[44px] rounded-xl font-bold text-xs bg-indigo-700 hover:bg-indigo-600 text-white flex items-center justify-center gap-1.5 shadow active:scale-95 text-center"
                >
                  <Phone size={15} />
                  <span>Sună Radio</span>
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Listă orizontală de selectat alte alerte în mobil */}
        <div className="space-y-1.5 overflow-y-auto max-h-48 pr-1">
          <p className="text-[10px] uppercase font-bold text-slate-400">Alte alerte active:</p>
          {mobileEvents.map((ev) => (
            <button
              key={ev.event_id}
              onClick={() => {
                setSelectedMobileEventId(ev.event_id);
                setCountdown(28);
              }}
              className={`w-full text-left p-2 rounded-xl border text-xs flex items-center justify-between transition-colors ${
                ev.event_id === activeEvent?.event_id
                  ? 'bg-indigo-900/60 border-indigo-400 text-white'
                  : 'bg-slate-800/60 border-white/5 text-slate-300'
              }`}
            >
              <span className="truncate max-w-[210px] font-medium">{ev.report?.what}</span>
              <span
                style={{
                  backgroundColor: STATUS_TOKENS[ev.severity].bg,
                  color: STATUS_TOKENS[ev.severity].text
                }}
                className="text-[9px] font-black px-1.5 py-0.5 rounded"
              >
                {ev.severity}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
