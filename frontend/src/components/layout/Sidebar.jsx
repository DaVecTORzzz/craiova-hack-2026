import React from 'react';
import {
  Video,
  AlertOctagon,
  PenTool,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

export default function Sidebar() {
  const { isDarkMode, themeStyles } = useTheme();
  const {
    currentView,
    setCurrentView,
    isSidebarCollapsed,
    setIsSidebarCollapsed,
    kpis,
    health
  } = useSecurity();

  const edgeSeen = health?.edge_last_seen_s;
  const edgeActive = Boolean(health?.db && edgeSeen != null && edgeSeen < 60);
  const edgeLabel = edgeActive ? 'ACTIV' : edgeSeen == null ? 'FĂRĂ DATE' : 'ÎNTÂRZIAT';
  const edgeColor = edgeActive ? 'bg-emerald-600' : 'bg-[#FFEB33] text-[#1F1F1F]';

  // Ecranele principale ale aplicației SafeSight
  const menuItems = [
    {
      id: 'live',
      label: 'Live',
      subtitle: 'Monitorizare & Stream',
      icon: Video,
      badge: kpis?.open_incidents_count > 0 ? kpis.open_incidents_count : null
    },
    {
      id: 'incidents',
      label: 'Incidente',
      subtitle: 'Istoric, dovadă & raport',
      // The detail page belongs to this entry.
      also: ['incident_detail'],
      icon: AlertOctagon,
      badge: kpis?.escalated_incidents_count > 0 ? 'ESC' : null,
      badgeCritical: true
    },
    {
      id: 'zones',
      label: 'Configurare Zone',
      subtitle: 'Poligoane & Cadru FOD',
      icon: PenTool
    },
    {
      id: 'reports',
      label: 'Rapoarte Tură',
      subtitle: 'Statistici & Export PDF',
      icon: FileText
    },
    {
      id: 'settings',
      label: 'Edge & Audit',
      subtitle: 'Stare sistem & jurnal',
      icon: Settings
    }
  ];

  return (
    <aside
      style={{
        backgroundColor: isDarkMode ? (themeStyles.navBg || '#181818') : '#FFFFFF',
        borderColor: isDarkMode ? 'rgba(255, 255, 255, 0.08)' : '#E5E7EB',
        width: isSidebarCollapsed ? '0px' : '15rem'
      }}
      className={`no-print flex flex-col justify-between border-r transition-all duration-300 z-20 select-none shadow-md shrink-0 h-full overflow-hidden ${isSidebarCollapsed ? "border-r-0" : ""}`}
    >
      {/* Zona de Sus: Meniu Principal & Lista Categorisită de Feed-uri */}
      <div className="flex-1 py-3 px-2 space-y-4 overflow-y-auto overflow-x-hidden">
        {/* Rubrici Principale */}
        <div className="space-y-1">
          {!isSidebarCollapsed && (
            <div className="px-3 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Module Operaționale
            </div>
          )}

          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id || Boolean(item.also?.includes(currentView));

            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                style={{
                  backgroundColor: isActive ? '#7EDEED' : 'transparent',
                  color: isActive ? '#1F1F1F' : (isDarkMode ? '#F5F5F5' : '#1F1F1F')
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all group text-left relative ${
                  isActive ? 'shadow-md font-bold' : 'hover:bg-white/5'
                }`}
                title={item.label}
              >
                <Icon size={19} className="shrink-0" />
                {!isSidebarCollapsed && (
                  <div className="flex-1 truncate">
                    <span className="block leading-tight truncate">{item.label}</span>
                    <p className={`text-[10px] font-normal truncate mt-0.5 ${isActive ? 'text-[#1F1F1F]/80' : 'text-slate-400'}`}>
                      {item.subtitle}
                    </p>
                  </div>
                )}

                {/* Badge alerte deschise / escaladate */}
                {item.badge && (
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow shrink-0 ${
                      item.badgeCritical
                        ? 'bg-[#D73833] text-white animate-pulse'
                        : isActive
                        ? 'bg-[#1F1F1F] text-[#7EDEED]'
                        : 'bg-[#7EDEED] text-[#1F1F1F]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

      </div>

      {/* Zona de Jos: Status Edge & Buton Minimizare (Fără textul "NAV") */}
      <div
        style={{ borderColor: isDarkMode ? 'rgba(255, 255, 255, 0.08)' : '#E5E7EB' }}
        className="p-2.5 border-t space-y-2 shrink-0 bg-black/15"
      >
        {!isSidebarCollapsed && (
          <div className="p-2 rounded-lg bg-[#7EDEED]/10 border border-[#7EDEED]/25 text-[11px] space-y-1">
            <div className="flex items-center justify-between font-bold text-[#7EDEED]">
              <span className="flex items-center gap-1.5">
                <ShieldCheck size={14} />
                Edge AI
              </span>
              <span className={`text-[10px] font-mono font-bold px-1.5 rounded ${edgeColor}`}>{edgeLabel}</span>
            </div>
            <p className="text-[10px] text-slate-400 leading-tight">
              {health?.db ? 'Backend online' : 'Backend offline'} · {edgeSeen == null ? 'edge fără date' : `edge acum ${Math.round(edgeSeen)}s`}
            </p>
            <p className="text-[10px] text-slate-400 leading-tight">
              YOLO26 + ByteTrack • snapshot automat
            </p>
          </div>
        )}

        <button
          onClick={() => setIsSidebarCollapsed(true)}
          className="w-full flex items-center justify-center gap-2 py-2 px-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 transition-all font-semibold text-xs shadow-sm"
          title="Restrânge Meniul"
        >
          {isSidebarCollapsed ? (
            <ChevronRight size={18} />
          ) : (
            <>
              <ChevronLeft size={16} />
              <span>Restrânge meniu</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
