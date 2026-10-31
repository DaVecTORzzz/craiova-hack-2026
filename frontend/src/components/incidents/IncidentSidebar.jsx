import React from 'react';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import IncidentCard from './IncidentCard';

export default function IncidentSidebar() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    filteredIncidents,
    severityFilter,
    setSeverityFilter,
    searchQuery,
    resetDemoData
  } = useSecurity();

  const filterTabs = [
    { key: 'all', label: 'Toate' },
    { key: 'critical', label: 'Critice (Roșu)' },
    { key: 'warning', label: 'Avertismente' },
    { key: 'resolved', label: 'Remediate' }
  ];

  return (
    <aside
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder
      }}
      className="w-full lg:w-96 border-t lg:border-t-0 lg:border-l p-3 md:p-4 flex flex-col shrink-0 overflow-hidden shadow-lg h-full"
    >
      {/* Header Listă Incidente */}
      <div className="flex items-center justify-between pb-3 border-b border-white/10 shrink-0">
        <div className="flex items-center gap-2">
          <ShieldAlert size={20} className="text-red-400 animate-pulse" />
          <div>
            <h2 className="font-bold text-sm uppercase tracking-wider">
              Alerte Incidente AI
            </h2>
            <p style={{ color: themeStyles.textMuted }} className="text-[10px]">
              Explainable AI (XAI) & Live Detection
            </p>
          </div>
        </div>

        <span
          style={{ backgroundColor: themeStyles.accentColor }}
          className={`text-xs font-black px-2 py-0.5 rounded-full ${
            isDarkMode ? 'text-white' : 'text-slate-950'
          }`}
        >
          {filteredIncidents.length} Active
        </span>
      </div>

      {/* Taburi Filtre Severitate */}
      <div className="flex gap-1.5 my-2.5 shrink-0">
        {filterTabs.map((f) => {
          const isSelected = severityFilter === f.key;
          return (
            <button
              key={f.key}
              onClick={() => setSeverityFilter(f.key)}
              style={{
                backgroundColor: isSelected ? themeStyles.accentColor : themeStyles.cardBg,
                color: isSelected && !isDarkMode ? '#0F172A' : themeStyles.textColor
              }}
              className="flex-1 py-1 text-[10px] font-bold rounded transition-colors text-center"
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Listă Verticală Scrollabilă */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 scrollbar-thin">
        {filteredIncidents.length === 0 ? (
          <div
            style={{ backgroundColor: themeStyles.cardBg }}
            className="p-6 rounded-xl text-center space-y-3 mt-4"
          >
            <CheckCircle2 size={36} className="mx-auto text-emerald-400" />
            <p className="font-bold text-sm">Niciun incident activ!</p>
            <p style={{ color: themeStyles.textMuted }} className="text-xs">
              {searchQuery
                ? 'Niciun rezultat nu corespunde filtrelor aplicate.'
                : 'Toate riscurile raportate au fost soluționate cu succes.'}
            </p>
            <button
              onClick={resetDemoData}
              style={{ backgroundColor: themeStyles.accentColor }}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold shadow ${
                isDarkMode ? 'text-white' : 'text-slate-950'
              }`}
            >
              Reîncarcă Incidentele Demo
            </button>
          </div>
        ) : (
          filteredIncidents.map((incident) => (
            <IncidentCard key={incident.id} incident={incident} />
          ))
        )}
      </div>
    </aside>
  );
}
