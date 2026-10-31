import React from 'react';
import { Settings, ShieldCheck, HardDrive, Lock, MessageSquare, Terminal } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function SettingsView() {
  const { themeStyles } = useTheme();
  const { cameras } = useSecurity();

  // Date de audit & securitate conform Deciziei N23
  const auditLogs = [
    { time: '10:42:14', actor: 'System (AI Edge)', action: 'RESTRICTED_ZONE event generated for stand12 (track #17)' },
    { time: '10:42:15', actor: 'Webhook Relay', action: 'Slack incoming notification sent to #safety-ops-airside' },
    { time: '10:32:05', actor: 'Operator: Ariana', action: 'Acknowledge event evt_stand12_1730283921004_12' },
    { time: '10:25:43', actor: 'Escalation Engine', action: 'Escalated unattended luggage evt_checkin_1730283120011_99' },
    { time: '10:15:05', actor: 'Health Daemon', action: 'CAMERA_OFFLINE trigger on baggage_south (5s missing frames)' }
  ];

  return (
    <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-5 h-full select-none max-w-5xl mx-auto">
      <div>
        <h2 className="font-black text-lg uppercase tracking-tight flex items-center gap-2">
          <Settings size={20} className="text-indigo-400" />
          Configurație Edge & Politici de Securitate (Read-Only)
        </h2>
        <p style={{ color: themeStyles.textMuted }} className="text-xs font-mono">
          Securitate Date Aeroport • Arhitectură Edge-Native & Jurnal de Audit ICAO
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1: Starea Nodului Edge */}
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-4 rounded-xl border shadow-sm space-y-3 text-xs"
        >
          <h3 className="font-bold text-sm uppercase flex items-center gap-1.5 text-emerald-400">
            <ShieldCheck size={16} /> Stare Nod Edge Aeroport
          </h3>
          <div className="space-y-1.5 font-mono">
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="opacity-70">Nod AI Edge:</span>
              <span className="font-bold text-emerald-400">ONLINE (Jetson AGX Orin 64GB)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="opacity-70">Camere Înrolate:</span>
              <span className="font-bold text-white">{cameras.length} fluxuri RTSP</span>
            </div>
            <div className="flex justify-between py-1 border-b border-white/5">
              <span className="opacity-70">Model Computer Vision:</span>
              <span className="font-bold text-indigo-400">YOLO26-Tarmac + ByteTrack</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="opacity-70">Latență Procesare Cadru:</span>
              <span className="font-bold text-emerald-400">28 ms / frame</span>
            </div>
          </div>
        </div>

        {/* Card 2: Ce Pleacă din Aeroport (Privacy & GDPR) */}
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-4 rounded-xl border shadow-sm space-y-3 text-xs"
        >
          <h3 className="font-bold text-sm uppercase flex items-center gap-1.5 text-indigo-400">
            <Lock size={16} /> Ce Pleacă din Aeroport (Privacy)
          </h3>
          <div className="space-y-2 text-slate-300">
            <p>
              Fluxurile video brute 4K <span className="font-bold text-emerald-400">NU părăsesc niciodată perimetrul aeroportului</span>. Ele sunt procesate local la edge.
            </p>
            <div className="p-2 rounded bg-black/30 space-y-1 font-mono text-[11px]">
              <div className="text-white font-bold">Date exportate în exterior (doar la incident):</div>
              <p className="text-slate-400">• Metadate JSON (tip incident, timestamp, coordonate)</p>
              <p className="text-slate-400">• Snapshot foto cu <span className="text-amber-400 font-bold">fețele blurate la edge</span></p>
              <p className="text-slate-400">• Retenție evenimente: 7 zile pe storage securizat</p>
            </div>
          </div>
        </div>
      </div>

      {/* Card 3: Canale de Notificare */}
      <div
        style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
        className="p-4 rounded-xl border shadow-sm space-y-3 text-xs"
      >
        <h3 className="font-bold text-sm uppercase flex items-center gap-1.5 text-white">
          <MessageSquare size={16} className="text-indigo-400" />
          Canale Notificare & Integrare Dispecerat
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-black/20 border border-white/5">
            <span className="font-bold block text-indigo-400">Slack Webhook</span>
            <span className="text-[11px] opacity-75">#safety-ops-airside (Alertă text + link incident)</span>
          </div>
          <div className="p-3 rounded-lg bg-black/20 border border-white/5">
            <span className="font-bold block text-indigo-400">A-CDM Airport System</span>
            <span className="text-[11px] opacity-75">Blocare automată autorizație Pushback TWR</span>
          </div>
          <div className="p-3 rounded-lg bg-black/20 border border-white/5">
            <span className="font-bold block text-indigo-400">Radio TETRA</span>
            <span className="text-[11px] opacity-75">Apel direct din PWA Mobil</span>
          </div>
        </div>
      </div>

      {/* Card 4: Jurnal de Audit Read-Only */}
      <div
        style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
        className="p-4 rounded-xl border shadow-sm space-y-3 text-xs"
      >
        <h3 className="font-bold text-sm uppercase flex items-center gap-1.5 text-white">
          <Terminal size={16} className="text-emerald-400" />
          Jurnal de Audit Operativ (Audit Log Read-Only)
        </h3>

        <div className="space-y-1.5 font-mono text-[11px] overflow-x-auto">
          {auditLogs.map((log, idx) => (
            <div key={idx} className="p-2 rounded bg-black/30 flex items-center gap-2 border border-white/5">
              <span className="text-slate-400 shrink-0">[{log.time}]</span>
              <span className="text-indigo-400 font-bold shrink-0">{log.actor}:</span>
              <span className="text-slate-200 truncate">{log.action}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
