import React, { useState } from 'react';
import {
  ArrowLeft,
  Check,
  XCircle,
  RotateCcw,
  RefreshCw,
  FileDown,
  Clock,
  ShieldAlert,
  Info,
  MapPin,
  Calendar,
  AlertTriangle,
  Video
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import { STATUS_TOKENS } from '../../constants/theme';
import ConfidenceBadge from '../common/ConfidenceBadge';
import { printAsPdf } from '../../utils/print';

export default function IncidentDetailView() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    selectedEvent,
    setCurrentView,
    setSelectedCameraId,
    acknowledgeEvent,
    markFalsePositive,
    reopenEvent,
    regenerateReport
  } = useSecurity();

  const [falsePositiveNote, setFalsePositiveNote] = useState('');
  const [showNoteDialog, setShowNoteDialog] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  if (!selectedEvent) {
    return (
      <div className="p-8 text-center">
        <p className="font-bold text-lg">Niciun incident selectat.</p>
        <button
          onClick={() => setCurrentView('incidents')}
          className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold"
        >
          Vezi lista de incidente
        </button>
      </div>
    );
  }

  const isAcked = selectedEvent.status === 'acknowledged';
  const isFalsePos = selectedEvent.status === 'false_positive';

  // Formatare ore în Europe/Bucharest (Regulă din PDF: API trimite UTC, conversie în UI)
  const formatTime = (isoString) => {
    if (!isoString) return 'În așteptare';
    try {
      return new Date(isoString).toLocaleTimeString('ro-RO', {
        timeZone: 'Europe/Bucharest',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return isoString;
    }
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    await regenerateReport(selectedEvent.event_id);
    setIsRegenerating(false);
  };

  return (
    <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 h-full select-none max-w-6xl mx-auto">
      {/* Bară Superioară Navigare */}
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentView('incidents')}
            style={{ backgroundColor: themeStyles.cardBg }}
            className="no-print p-2 rounded-lg border hover:bg-white/10 flex items-center gap-1.5 text-xs font-bold"
          >
            <ArrowLeft size={16} /> Incidente
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-black text-base md:text-lg uppercase tracking-tight">
                Incident: {selectedEvent.event_id}
              </h2>
              {/* Badge Severitate */}
              <span
                style={{
                  backgroundColor: STATUS_TOKENS[selectedEvent.severity].bg,
                  color: STATUS_TOKENS[selectedEvent.severity].text,
                  borderColor: STATUS_TOKENS[selectedEvent.severity].border
                }}
                className="text-[10px] font-black uppercase px-2 py-0.5 rounded border"
              >
                {selectedEvent.severity}
              </span>
              {/* Badge Stare */}
              <span
                style={{
                  backgroundColor: STATUS_TOKENS[selectedEvent.status]?.bg || '#EEEEEE',
                  color: STATUS_TOKENS[selectedEvent.status]?.text || '#222222',
                  borderColor: STATUS_TOKENS[selectedEvent.status]?.border || '#DDDDDD'
                }}
                className="text-[10px] font-bold px-2 py-0.5 rounded border"
              >
                {STATUS_TOKENS[selectedEvent.status]?.label || selectedEvent.status}
              </span>
            </div>
            <p style={{ color: themeStyles.textMuted }} className="text-xs font-mono">
              Model detecție: {selectedEvent.model} • Track ID: #{selectedEvent.track_id}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* The snapshot is the moment of the incident; this shows the same camera now. */}
          <button
            onClick={() => {
              setSelectedCameraId(selectedEvent.camera_id);
              setCurrentView('live');
            }}
            className="no-print px-3 py-2 rounded-lg bg-[#7EDEED] hover:bg-[#5ccedc] text-[#1F1F1F] text-xs font-bold flex items-center gap-1.5"
          >
            <Video size={15} /> Vezi camera acum
          </button>
          {/* Confidence Badge formatat 0.91 · 14/15 cadre */}
          <ConfidenceBadge confidence={selectedEvent.confidence} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* COLOANA STÂNGA: SNAPSHOT CU CADRUL INCIDENTULUI (HTTP, fețe blurate) */}
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="rounded-xl border p-4 shadow-lg space-y-3 flex flex-col"
        >
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="font-bold uppercase tracking-wider flex items-center gap-1.5">
              <MapPin size={14} className="text-indigo-400" />
              Camera: {selectedEvent.camera_id} ({selectedEvent.zone_id})
            </span>
            <span className="text-slate-400">Durată: {selectedEvent.duration_s}s</span>
          </div>

          <div className="flex-1 relative rounded-lg overflow-hidden bg-black border border-slate-700 min-h-[260px] flex items-center justify-center">
            {selectedEvent.snapshot_url ? (
              <img
                src={selectedEvent.snapshot_url}
                alt="Cadru incident blurat"
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="text-center text-slate-400 font-mono text-xs p-6">
                <ShieldAlert size={36} className="mx-auto text-amber-400 mb-2" />
                <span>Nicio imagine disponibilă (Flux Offline)</span>
              </div>
            )}
            <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/80 text-white font-mono text-[10px] rounded border border-white/20">
              Momentul incidentului • fețe blurate pe edge
            </div>
          </div>

          {/* CRONOLOGIE ÎN 5 PAȘI (Conform Brief-ului C) */}
          <div
            style={{ backgroundColor: themeStyles.cardBg }}
            className="p-3 rounded-lg border border-white/10 space-y-2"
          >
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1">
              <Clock size={13} /> Cronologie Eveniment (5 Pași):
            </p>
            <div className="grid grid-cols-5 gap-1.5 text-center font-mono text-[10px]">
              <div className="p-1 rounded bg-black/20">
                <span className="block opacity-60">1. Detecție</span>
                <span className="font-bold text-white">{formatTime(selectedEvent.detected_at)}</span>
              </div>
              <div className="p-1 rounded bg-black/20">
                <span className="block opacity-60">2. Primit</span>
                <span className="font-bold text-white">{formatTime(selectedEvent.received_at)}</span>
              </div>
              <div className="p-1 rounded bg-black/20">
                <span className="block opacity-60">3. Notificat</span>
                <span className="font-bold text-white">{formatTime(selectedEvent.notified_at)}</span>
              </div>
              <div className={`p-1 rounded ${selectedEvent.escalated_at ? 'bg-red-950 text-red-300' : 'bg-black/20'}`}>
                <span className="block opacity-60">4. Escaladat</span>
                <span className="font-bold">{formatTime(selectedEvent.escalated_at)}</span>
              </div>
              <div className={`p-1 rounded ${selectedEvent.acked_at ? 'bg-emerald-950 text-emerald-300' : 'bg-black/20'}`}>
                <span className="block opacity-60">5. Confirmat</span>
                <span className="font-bold">{formatTime(selectedEvent.acked_at)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* COLOANA DREAPTA: RAPORT STRUCTURAT & HUMAN-IN-THE-LOOP */}
        <div className="space-y-4 flex flex-col justify-between">
          {/* Raport Structurat în 5 Câmpuri */}
          <div
            style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
            className="rounded-xl border p-4 shadow-lg space-y-3"
          >
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
                <Info size={16} className="text-indigo-400" />
                Raport de Securitate ({selectedEvent.report?.source?.toUpperCase() || 'LLM'})
              </h3>
              <button
                onClick={handleRegenerate}
                className="no-print text-xs text-indigo-400 hover:underline flex items-center gap-1 font-semibold"
              >
                <RefreshCw size={12} className={isRegenerating ? 'animate-spin' : ''} />
                Regenerează Raportul
              </button>
            </div>

            {isRegenerating ? (
              <div className="space-y-2 py-4 animate-pulse">
                <div className="h-4 bg-white/20 rounded w-3/4" />
                <div className="h-4 bg-white/20 rounded w-1/2" />
                <div className="h-10 bg-white/20 rounded w-full" />
              </div>
            ) : (
              <div className="space-y-2.5 text-xs">
                <div>
                  <span className="font-bold text-slate-400 block text-[11px]">CE:</span>
                  <p className="font-semibold text-white">{selectedEvent.report?.what || 'necunoscut'}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 block text-[11px]">UNDE:</span>
                  <p className="font-semibold">{selectedEvent.report?.where || 'necunoscut'}</p>
                </div>
                <div>
                  <span className="font-bold text-slate-400 block text-[11px]">CÂND:</span>
                  <p className="font-semibold font-mono">{selectedEvent.report?.when || 'necunoscut'}</p>
                </div>
                <div>
                  <span className="font-bold text-red-400 block text-[11px]">SEVERITATE & RISC:</span>
                  <p className="font-semibold text-red-200">{selectedEvent.report?.severity_reason || 'necunoscut'}</p>
                </div>
                <div className="p-2.5 rounded-lg bg-amber-500/15 border border-amber-500/30">
                  <span className="font-bold text-amber-400 block text-[11px]">ACȚIUNE RECOMANDATĂ:</span>
                  <p className="font-bold text-amber-200 mt-0.5">{selectedEvent.report?.recommended_action || 'necunoscut'}</p>
                </div>
              </div>
            )}
          </div>

          {/* Decizia operatorului (acțiuni; nu apar în PDF) */}
          <div
            style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
            className="no-print rounded-xl border p-4 shadow-lg space-y-3"
          >
            <h4 className="font-bold text-xs uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <Check size={15} /> Decizia operatorului
            </h4>

            <div className="grid grid-cols-2 gap-2 text-xs">
              {/* Buton 1: Acknowledge */}
              <button
                disabled={isAcked}
                onClick={(e) => acknowledgeEvent(selectedEvent.event_id, e)}
                className={`py-2.5 px-3 rounded-lg font-bold flex items-center justify-center gap-2 shadow transition-all ${
                  isAcked
                    ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/40 cursor-not-allowed'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white hover:scale-[1.02]'
                }`}
              >
                <Check size={16} />
                <span>{isAcked ? 'Confirmat' : 'Confirmă'}</span>
              </button>

              {/* Buton 2: Fals Pozitiv */}
              <button
                disabled={isFalsePos}
                onClick={() => setShowNoteDialog(true)}
                className={`py-2.5 px-3 rounded-lg font-bold flex items-center justify-center gap-2 border border-slate-600 transition-all ${
                  isFalsePos
                    ? 'bg-slate-900 text-slate-500 cursor-not-allowed'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                }`}
              >
                <XCircle size={16} />
                <span>{isFalsePos ? 'Marcat Fals Pozitiv' : 'Fals Pozitiv'}</span>
              </button>

              {/* Buton 3: Reopen */}
              <button
                onClick={() => reopenEvent(selectedEvent.event_id)}
                className="py-2.5 px-3 rounded-lg font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 flex items-center justify-center gap-2"
              >
                <RotateCcw size={15} />
                <span>Redeschide</span>
              </button>

              {/* Buton 4: Export PDF (dialogul de tipărire al browserului) */}
              <button
                onClick={() => printAsPdf(`SafeSight_incident_${selectedEvent.event_id}`)}
                className="py-2.5 px-3 rounded-lg font-bold bg-indigo-900/60 hover:bg-indigo-900 text-indigo-200 border border-indigo-700/60 flex items-center justify-center gap-2"
              >
                <FileDown size={15} />
                <span>Export PDF</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Dialog Notă Fals Pozitiv */}
      {showNoteDialog && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div
            style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
            className="w-full max-w-md rounded-2xl border p-5 shadow-2xl space-y-4"
          >
            <h3 className="font-bold text-sm uppercase">Feedback Fals Pozitiv pentru Echipa AI</h3>
            <p style={{ color: themeStyles.textMuted }} className="text-xs">
              Explică de ce detecția a fost eronată pentru antrenarea viitoare a modelului:
            </p>
            <textarea
              value={falsePositiveNote}
              onChange={(e) => setFalsePositiveNote(e.target.value)}
              placeholder="Ex: Tehnicanul purta dopuri interne de urechi, nu căști externe..."
              className="w-full p-2.5 rounded-lg bg-black/30 border border-white/20 text-xs focus:ring-2 focus:ring-indigo-400"
              rows={3}
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowNoteDialog(false)}
                className="px-3 py-1.5 rounded-lg border border-white/20 text-xs"
              >
                Anulează
              </button>
              <button
                onClick={() => {
                  markFalsePositive(selectedEvent.event_id, falsePositiveNote);
                  setShowNoteDialog(false);
                }}
                className="px-4 py-1.5 rounded-lg bg-amber-600 text-white font-bold text-xs"
              >
                Trimite Feedback
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
