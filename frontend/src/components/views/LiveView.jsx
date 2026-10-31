import React from 'react';
import {
  ShieldAlert,
  HardHat,
  Clock,
  AlertTriangle,
  Power,
  Eye,
  Check,
  Video,
  WifiOff,
  Maximize2
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import { STATUS_TOKENS } from '../../constants/theme';
import ConfidenceBadge from '../common/ConfidenceBadge';
import BoundingBox from '../video/BoundingBox';

export default function LiveView() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    kpis,
    cameras,
    activeCamera,
    selectedCameraId,
    setSelectedCameraId,
    toggleEngine,
    filteredEvents,
    filterMode,
    setFilterMode,
    acknowledgeEvent,
    setSelectedEventId,
    setCurrentView
  } = useSecurity();

  const isOffline = activeCamera.status === 'offline';

  return (
    <div className="flex-1 flex flex-col p-3 md:p-4 overflow-y-auto space-y-3 h-full select-none">
      {/* 1. Cele 4 KPI din Live (Conform Brief-ului C) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 shrink-0">
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-3 rounded-xl border shadow-sm flex items-center justify-between"
        >
          <div>
            <p style={{ color: themeStyles.textMuted }} className="text-[11px] font-semibold">
              Conformitate PPE
            </p>
            <p className="text-xl md:text-2xl font-black font-mono text-emerald-400">
              {kpis.ppe_compliance_pct}%
            </p>
          </div>
          <HardHat size={26} className="text-emerald-400 opacity-80" />
        </div>

        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-3 rounded-xl border shadow-sm flex items-center justify-between"
        >
          <div>
            <p style={{ color: themeStyles.textMuted }} className="text-[11px] font-semibold">
              Incidente Deschise
            </p>
            <p className="text-xl md:text-2xl font-black font-mono text-amber-400">
              {kpis.open_incidents_count}
            </p>
          </div>
          <AlertTriangle size={26} className="text-amber-400 opacity-80" />
        </div>

        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-3 rounded-xl border shadow-sm flex items-center justify-between"
        >
          <div>
            <p style={{ color: themeStyles.textMuted }} className="text-[11px] font-semibold">
              Detecție → Alertă
            </p>
            <p className="text-xl md:text-2xl font-black font-mono text-indigo-400">
              {kpis.detection_to_alert_latency_s}s
            </p>
          </div>
          <Clock size={26} className="text-indigo-400 opacity-80" />
        </div>

        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-3 rounded-xl border shadow-sm flex items-center justify-between"
        >
          <div>
            <p style={{ color: themeStyles.textMuted }} className="text-[11px] font-semibold">
              Escaladate
            </p>
            <p className="text-xl md:text-2xl font-black font-mono text-red-500">
              {kpis.escalated_incidents_count}
            </p>
          </div>
          <ShieldAlert size={26} className="text-red-500 opacity-80 animate-pulse" />
        </div>
      </div>

      {/* 2. Corp Principal Live: Video Adnotat Stânga + Feed Evenimente Dreapta */}
      <div className="flex-1 flex flex-col lg:flex-row gap-3 min-h-[460px] overflow-hidden">
        {/* ZONA VIDEO & CONTROALE CAMERA */}
        <div className="flex-1 flex flex-col space-y-2.5 min-w-0">
          {/* Bară Selector Cameră + Engine Switch */}
          <div
            style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
            className="p-2.5 rounded-xl border shadow-sm flex items-center justify-between gap-2 shrink-0 flex-wrap"
          >
            {/* Selector Cameră */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
              {cameras.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedCameraId(c.id)}
                  style={{
                    backgroundColor: c.id === selectedCameraId ? themeStyles.accentColor : 'transparent',
                    color: c.id === selectedCameraId ? '#FFFFFF' : themeStyles.textColor
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold border border-white/10 shrink-0 transition-colors ${
                    c.status === 'offline' ? 'opacity-60' : ''
                  }`}
                >
                  <span
                    className={`inline-block w-2 h-2 rounded-full mr-1.5 ${
                      c.status === 'offline' ? 'bg-red-500' : 'bg-emerald-400'
                    }`}
                  />
                  {c.id}
                </button>
              ))}
            </div>

            {/* Buton Engine ON / OFF Switch (Conform Regulii N11) */}
            <button
              onClick={() => toggleEngine(activeCamera.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-2 shadow transition-all ${
                activeCamera.engine_on
                  ? 'bg-amber-500 text-slate-950 animate-pulse'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              title="Comută starea motorului aeronavei pentru acest stand"
            >
              <Power size={14} />
              <span>ENGINE: {activeCamera.engine_on ? 'ON (Pornit)' : 'OFF (Oprit)'}</span>
            </button>
          </div>

          {/* Player-ul Video Adnotat */}
          <div className="flex-1 relative rounded-xl overflow-hidden bg-black border border-slate-700 flex items-center justify-center min-h-[300px] shadow-lg">
            {isOffline ? (
              <div className="text-center p-6 text-red-500 font-mono">
                <WifiOff size={48} className="mx-auto mb-2 animate-bounce" />
                <h3 className="text-2xl font-black tracking-widest">SEMNAL PIERDUT</h3>
                <p className="text-xs text-slate-400 mt-1">CAMERA {activeCamera.id} ESTE MOMENTAN OFFLINE</p>
              </div>
            ) : (
              <div
                className={`w-full h-full bg-gradient-to-br ${activeCamera.previewBg} relative flex items-center justify-center`}
              >
                <div className="text-center opacity-30 select-none">
                  <Video size={70} className="mx-auto mb-2 text-slate-300" />
                  <p className="font-mono font-bold text-white text-base">{activeCamera.name.toUpperCase()}</p>
                  <p className="font-mono text-xs text-slate-300">LIVE ANNOTATED STREAM • {activeCamera.fps} FPS</p>
                </div>

                {/* Bounding Boxes */}
                {activeCamera.boxes && activeCamera.boxes.map((box) => (
                  <BoundingBox key={box.id} box={box} />
                ))}

                {/* HUD Overlay */}
                <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/80 px-2.5 py-1 rounded text-[11px] font-mono text-white border border-white/10">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                  <span>REC: LIVE</span>
                  <span>|</span>
                  <span>{activeCamera.resolution}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* FEED EVENIMENTE DREAPTA (Deschise, Doar critice, Toate azi) */}
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="w-full lg:w-96 rounded-xl border p-3 flex flex-col shadow-lg shrink-0 overflow-hidden"
        >
          <div className="flex items-center justify-between pb-2 border-b border-white/10 shrink-0">
            <h2 className="font-bold text-sm uppercase tracking-wider flex items-center gap-1.5">
              <ShieldAlert size={16} className="text-red-400" />
              Feed Evenimente
            </h2>
            <span
              style={{ backgroundColor: themeStyles.accentColor }}
              className="text-xs font-mono font-bold px-2 py-0.5 rounded-full text-white"
            >
              {filteredEvents.length}
            </span>
          </div>

          {/* Filtre: Deschise, Doar critice, Toate azi */}
          <div className="flex gap-1 my-2 shrink-0">
            {[
              { key: 'open', label: 'Deschise' },
              { key: 'critical', label: 'Doar critice' },
              { key: 'all', label: 'Toate azi' }
            ].map((f) => (
              <button
                key={f.key}
                onClick={() => setFilterMode(f.key)}
                style={{
                  backgroundColor: filterMode === f.key ? themeStyles.accentColor : themeStyles.cardBg,
                  color: filterMode === f.key ? '#FFFFFF' : themeStyles.textColor
                }}
                className="flex-1 py-1 text-[11px] font-bold rounded transition-colors text-center"
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Listă Carduri Evenimente */}
          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 scrollbar-thin">
            {filteredEvents.length === 0 ? (
              <div style={{ backgroundColor: themeStyles.cardBg }} className="p-5 rounded-xl text-center space-y-2 mt-4 text-xs">
                <p className="font-bold">Niciun incident în această categorie.</p>
              </div>
            ) : (
              filteredEvents.map((ev) => {
                const isCrit = ev.severity === 'CRITICAL';
                const isEscalated = ev.status === 'escalated';
                const isAcked = ev.status === 'acknowledged';

                return (
                  <div
                    key={ev.event_id}
                    onClick={() => {
                      setSelectedEventId(ev.event_id);
                      setCurrentView('incident_detail');
                    }}
                    style={{ backgroundColor: themeStyles.cardBg }}
                    className={`p-3 rounded-xl border transition-all hover:scale-[1.01] cursor-pointer space-y-2 shadow-sm ${
                      isEscalated
                        ? 'border-red-500 ring-2 ring-red-500/50 animate-pulse'
                        : isCrit
                        ? 'border-red-500/40 hover:border-red-500'
                        : 'border-amber-400/40 hover:border-amber-400'
                    }`}
                  >
                    {/* Header Card: Severitate + Status separat */}
                    <div className="flex items-center justify-between gap-1">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {/* Badge Severitate: doar CRITICAL sau WARNING */}
                        <span
                          style={{
                            backgroundColor: STATUS_TOKENS[ev.severity].bg,
                            color: STATUS_TOKENS[ev.severity].text,
                            borderColor: STATUS_TOKENS[ev.severity].border
                          }}
                          className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded border"
                        >
                          {ev.severity}
                        </span>

                        {/* Badge Status separat */}
                        <span
                          style={{
                            backgroundColor: STATUS_TOKENS[ev.status]?.bg || '#EEEEEE',
                            color: STATUS_TOKENS[ev.status]?.text || '#222222',
                            borderColor: STATUS_TOKENS[ev.status]?.border || '#DDDDDD'
                          }}
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${
                            isEscalated ? 'animate-bounce' : ''
                          }`}
                        >
                          {STATUS_TOKENS[ev.status]?.label || ev.status}
                        </span>
                      </div>

                      <span className="font-mono text-[10px] opacity-70">
                        {ev.event_id.slice(-6)}
                      </span>
                    </div>

                    {/* Titlu & Locație */}
                    <div>
                      <p className="font-bold text-xs leading-tight">{ev.report?.what}</p>
                      <p style={{ color: themeStyles.textMuted }} className="text-[10px] font-mono mt-0.5">
                        {ev.camera_id} • {ev.report?.where}
                      </p>
                    </div>

                    {/* Confidence: strict 0.91 · 14/15 cadre */}
                    <div className="flex items-center justify-between text-[11px]">
                      <ConfidenceBadge confidence={ev.confidence} />
                      <span className="font-mono text-[10px] opacity-70">
                        {new Date(ev.detected_at).toLocaleTimeString('ro-RO')}
                      </span>
                    </div>

                    {/* Buton Acknowledge din Feed */}
                    <div className="pt-1 flex items-center justify-between border-t border-white/10">
                      <span className="text-[10px] text-indigo-400 font-semibold hover:underline flex items-center gap-1">
                        <Eye size={12} /> Detalii Incident
                      </span>

                      {!isAcked && (
                        <button
                          onClick={(e) => acknowledgeEvent(ev.event_id, e)}
                          style={{ backgroundColor: themeStyles.accentColor }}
                          className="px-2.5 py-1 rounded text-[11px] font-bold text-white flex items-center gap-1 shadow hover:opacity-90"
                        >
                          <Check size={12} /> Ack
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
