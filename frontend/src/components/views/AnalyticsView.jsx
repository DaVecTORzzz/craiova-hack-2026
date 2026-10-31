import React from 'react';
import { ShieldCheck, RefreshCw, BarChart3, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function AnalyticsView() {
  const { themeStyles } = useTheme();
  const { resetDemoData } = useSecurity();

  const aiCapabilities = [
    { name: 'Fumat lângă Aeronave / Cisterne ATEX', status: 'Activ', score: '99% Conf' },
    { name: 'Personal Fără Căști Antifonice EN 352', status: 'Activ', score: '94% Conf' },
    { name: 'FOD (Foreign Object Debris) pe Runway', status: 'Activ', score: '96% Conf' },
    { name: 'Bagaj Abandonat & Algoritm Re-ID', status: 'Activ', score: '98% Conf' },
    { name: 'Manipulare Brutală / Aruncare Bagaj', status: 'Activ', score: '89% Conf' },
    { name: 'Distanță Minimă Față de Turbină (Perimetru Roșu)', status: 'Activ', score: '95% Conf' },
    { name: 'Aglomerație Masivă & Panic Bottleneck', status: 'Activ', score: '91% Conf' },
    { name: 'Detecție Păsări & Animale Pistă (Bird Strike)', status: 'Activ', score: '93% Conf' },
    { name: 'Intruziune Gard Perimetral PIDS AI', status: 'Activ', score: '97% Conf' }
  ];

  return (
    <div className="flex-1 p-6 overflow-y-auto space-y-6 h-full select-none">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black uppercase tracking-tight">
            Statistici & Metrici Securitate AI
          </h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs">
            Date agregate din ultimele 24 de ore conforme protocoalelor ICAO Anexa 14 & EASA
          </p>
        </div>
        <button
          onClick={resetDemoData}
          style={{ backgroundColor: themeStyles.cardBg, borderColor: themeStyles.panelBorder }}
          className="px-3 py-1.5 rounded-lg border text-xs font-bold flex items-center gap-1.5 hover:opacity-80 shadow-sm"
        >
          <RefreshCw size={14} /> Reîmprospătează Metrici
        </button>
      </div>

      {/* Carduri KPI */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-4 rounded-xl border shadow-md space-y-2"
        >
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
            Timp Mediu Reacție (MTTR)
          </p>
          <p className="text-2xl font-black font-mono text-emerald-400">42 sec</p>
          <p className="text-[10px] text-emerald-400">↓ 18% mai rapid decât media săptămânii</p>
        </div>

        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-4 rounded-xl border shadow-md space-y-2"
        >
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
            Acuratețe Detecție Modele
          </p>
          <p className="text-2xl font-black font-mono text-indigo-400">97.8%</p>
          <p className="text-[10px] text-slate-400">Fals-pozitive sub 2.2% validate de ofițeri</p>
        </div>

        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-4 rounded-xl border shadow-md space-y-2"
        >
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
            FOD Piste Neutralizate
          </p>
          <p className="text-2xl font-black font-mono text-amber-400">14 Obiecte</p>
          <p className="text-[10px] text-amber-400">0 incidente critice la decolare/aterizare</p>
        </div>

        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="p-4 rounded-xl border shadow-md space-y-2"
        >
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-semibold">
            Rată Conformitate EIP Sol
          </p>
          <p className="text-2xl font-black font-mono text-purple-400">93.2%</p>
          <p className="text-[10px] text-slate-400">Căști antifonice, veste reflectorizante</p>
        </div>
      </div>

      {/* Matricea de Detecție AI Antrenată */}
      <div
        style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
        className="p-5 rounded-xl border shadow-md space-y-4"
      >
        <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
          <ShieldCheck size={18} className="text-emerald-400" />
          Matricea de Detecție AI Antrenată (Computer Vision Airport Safety)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          {aiCapabilities.map((item, idx) => (
            <div
              key={idx}
              style={{ backgroundColor: themeStyles.cardBg }}
              className="p-3 rounded-lg flex items-center justify-between border border-white/5 shadow-sm"
            >
              <div>
                <p className="font-bold">{item.name}</p>
                <p className="text-[10px] text-emerald-400 font-mono">Modul: {item.status}</p>
              </div>
              <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-white/10 shrink-0">
                {item.score}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
