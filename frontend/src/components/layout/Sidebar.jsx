import React from 'react';
import {
  Video,
  AlertOctagon,
  PenTool,
  FileText,
  Smartphone,
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
    kpis
  } = useSecurity();

  // Cele 6 Ecrane Solicitate în Brief-ul SafeSight AI
  const menuItems = [
    {
      id: 'live',
      label: 'Live Ops',
      subtitle: 'KPI, Stream & Feed',
      icon: Video,
      badge: kpis.open_incidents_count > 0 ? kpis.open_incidents_count : null
    },
    {
      id: 'incident_detail',
      label: 'Incidente',
      subtitle: 'Dovadă & Cronologie 5 Pași',
      icon: AlertOctagon,
      badge: kpis.escalated_incidents_count > 0 ? 'ESC' : null,
      badgeCritical: true
    },
    {
      id: 'zones',
      label: 'Editor Zone',
      subtitle: 'Poligoane & Cadru FOD',
      icon: PenTool
    },
    {
      id: 'reports',
      label: 'Rapoarte Tură',
      subtitle: 'Indicatori & Export PDF',
      icon: FileText
    },
    {
      id: 'mobile',
      label: 'Alerte Mobile',
      subtitle: 'PWA 390px & Apel Radio',
      icon: Smartphone
    },
    {
      id: 'settings',
      label: 'Edge & Audit',
      subtitle: 'Stare Edge & Canale Slack',
      icon: Settings
    }
  ];

  return (
    <aside
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder,
        width: isSidebarCollapsed ? '4.5rem' : '15rem'
      }}
      className="flex flex-col justify-between border-r transition-all duration-300 z-10 select-none shadow-md shrink-0 h-full"
    >
      {/* Meniu Principal */}
      <div className="py-4 px-2 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider opacity-60">
          {!isSidebarCollapsed ? 'Meniu SafeSight' : 'Meniu'}
        </div>

        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              style={{
                backgroundColor: isActive ? themeStyles.accentColor : 'transparent',
                color: isActive ? '#FFFFFF' : themeStyles.textColor
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs md:text-sm font-semibold transition-all hover:bg-white/10 group text-left relative"
              title={item.label}
            >
              <Icon size={19} className="shrink-0" />
              {!isSidebarCollapsed && (
                <div className="flex-1 truncate">
                  <span className="block leading-tight truncate">{item.label}</span>
                  <p className="text-[10px] opacity-75 font-normal truncate">{item.subtitle}</p>
                </div>
              )}

              {/* Badge alerte deschise / escaladate */}
              {item.badge && (
                <span
                  className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full shadow shrink-0 ${
                    item.badgeCritical
                      ? 'bg-red-600 text-white animate-pulse'
                      : 'bg-indigo-600 text-white'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Subsol Sidebar: Status Edge & Buton Colapsare */}
      <div
        style={{ borderColor: themeStyles.panelBorder }}
        className="p-3 border-t space-y-3 shrink-0"
      >
        {!isSidebarCollapsed && (
          <div
            style={{ backgroundColor: themeStyles.cardBg }}
            className="p-2.5 rounded-lg text-[11px] space-y-1.5 shadow-inner"
          >
            <div className="flex items-center justify-between font-bold">
              <span className="flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-emerald-400" />
                Edge AI Pipeline
              </span>
              <span className="text-emerald-400 font-mono text-[10px]">ACTIV</span>
            </div>
            <p style={{ color: themeStyles.textMuted }} className="text-[10px] leading-tight">
              YOLO26 + ByteTrack • Slack Webhook cablat • Retenție 7 zile
            </p>
          </div>
        )}

        <button
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          style={{
            backgroundColor: themeStyles.cardBg,
            borderColor: themeStyles.panelBorder
          }}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border hover:opacity-80 transition-all font-semibold text-xs shadow-sm"
          title={isSidebarCollapsed ? 'Extinde Meniul' : 'Restrânge Meniul'}
        >
          {isSidebarCollapsed ? (
            <ChevronRight size={18} />
          ) : (
            <>
              <ChevronLeft size={18} />
              <span>Restrânge Meniul</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
