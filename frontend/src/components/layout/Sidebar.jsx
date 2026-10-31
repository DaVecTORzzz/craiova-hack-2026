import React, { useMemo } from 'react';
import {
  Video,
  AlertOctagon,
  PenTool,
  FileText,
  Smartphone,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Building2,
  Plane,
  Fuel,
  Radio
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
    cameras,
    selectedCameraId,
    setSelectedCameraId,
    health
  } = useSecurity();

  const edgeSeen = health?.edge_last_seen_s;
  const edgeActive = Boolean(health?.db && edgeSeen != null && edgeSeen < 60);
  const edgeLabel = edgeActive ? 'ACTIV' : edgeSeen == null ? 'FĂRĂ DATE' : 'ÎNTÂRZIAT';
  const edgeColor = edgeActive ? 'bg-emerald-500' : 'bg-amber-500';

  // Ecranele principale ale aplicației SafeSight
  const menuItems = [
    {
      id: 'live',
      label: 'Live Ops & Feed-uri',
      subtitle: 'Monitorizare & Stream',
      icon: Video,
      badge: kpis?.open_incidents_count > 0 ? kpis.open_incidents_count : null
    },
    {
      id: 'incident_detail',
      label: 'Incidente & XAI',
      subtitle: 'Dovadă & Cronologie',
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
      id: 'mobile',
      label: 'Alerte Mobile PWA',
      subtitle: 'Deck Sol & Apel Radio',
      icon: Smartphone
    },
    {
      id: 'settings',
      label: 'Edge & Audit',
      subtitle: 'Stare Pipeline & Logs',
      icon: Settings
    }
  ];

  // Gruparea camerelor pe categorii de zonă aeroportuară
  const categorizedCameras = useMemo(() => {
    const groups = {
      'Terminal & Porți': { icon: Building2, list: [] },
      'Pistă & Căi Rulare': { icon: Plane, list: [] },
      'Alimentare & Rampă': { icon: Fuel, list: [] }
    };

    (cameras || []).forEach((cam) => {
      const cat = cam.category || 'Alimentare & Rampă';
      if (!groups[cat]) {
        groups[cat] = { icon: Radio, list: [] };
      }
      groups[cat].list.push(cam);
    });

    return groups;
  }, [cameras]);

  const handleSelectCamera = (camId) => {
    setSelectedCameraId(camId);
    if (currentView !== 'live') {
      setCurrentView('live');
    }
  };

  return (
    <aside
      style={{
        backgroundColor: isDarkMode ? '#141A28' : '#FFFFFF',
        borderColor: isDarkMode ? 'rgba(255, 255, 255, 0.08)' : '#E2E8F0',
        width: isSidebarCollapsed ? '4.25rem' : '16rem'
      }}
      className="flex flex-col justify-between border-r transition-all duration-300 z-20 select-none shadow-md shrink-0 h-full overflow-hidden"
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
            const isActive = currentView === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                style={{
                  backgroundColor: isActive ? '#1976D2' : 'transparent',
                  color: isActive ? '#FFFFFF' : (isDarkMode ? '#F8FAFC' : '#212121')
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all group text-left relative ${
                  isActive ? 'shadow-md' : 'hover:bg-slate-500/10'
                }`}
                title={item.label}
              >
                <Icon size={19} className="shrink-0" />
                {!isSidebarCollapsed && (
                  <div className="flex-1 truncate">
                    <span className="block leading-tight truncate">{item.label}</span>
                    <p className={`text-[10px] font-normal truncate mt-0.5 ${isActive ? 'text-blue-100' : 'text-slate-400'}`}>
                      {item.subtitle}
                    </p>
                  </div>
                )}

                {/* Badge alerte deschise / escaladate */}
                {item.badge && (
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow shrink-0 ${
                      item.badgeCritical
                        ? 'bg-red-600 text-white animate-pulse'
                        : 'bg-blue-600 text-white'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* FEED-URI CATEGORISITE PE ZONE AEROPORTUARE */}
        {!isSidebarCollapsed && (
          <div className="pt-2 border-t border-slate-500/15 space-y-3">
            <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Zone & Feed-uri CCTV
            </div>

            {Object.entries(categorizedCameras).map(([categoryName, group]) => {
              if (group.list.length === 0) return null;
              const CategoryIcon = group.icon;
              return (
                <div key={categoryName} className="space-y-1">
                  <div className="px-3 flex items-center gap-1.5 text-[11px] font-bold text-slate-500 dark:text-slate-400">
                    <CategoryIcon size={13} className="text-blue-500 shrink-0" />
                    <span>{categoryName}</span>
                  </div>

                  <div className="space-y-0.5 pl-2">
                    {group.list.map((cam) => {
                      const isCamActive = cam.id === selectedCameraId && currentView === 'live';
                      return (
                        <button
                          key={cam.id}
                          onClick={() => handleSelectCamera(cam.id)}
                          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-all flex flex-col ${
                            isCamActive
                              ? 'bg-blue-500/15 text-blue-600 dark:text-blue-400 font-bold border-l-2 border-blue-500'
                              : 'hover:bg-slate-500/10 text-slate-700 dark:text-slate-300'
                          }`}
                          title={`${cam.name} - ${cam.subtitle || ''}`}
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="truncate text-[11px] font-semibold">{cam.name}</span>
                            <span
                              className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                                cam.status === 'offline' ? 'bg-red-500' : 'bg-emerald-500'
                              }`}
                            />
                          </div>
                          {/* Detalii afișate sub denumirea camerei conform cerinței */}
                          <span className="text-[10px] text-slate-400 font-normal truncate mt-0.5">
                            {cam.subtitle || cam.id}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Zona de Jos: Status Edge & Buton Minimizare (Fără textul "NAV") */}
      <div
        style={{ borderColor: isDarkMode ? 'rgba(255, 255, 255, 0.08)' : '#E2E8F0' }}
        className="p-2.5 border-t space-y-2 shrink-0 bg-black/5 dark:bg-white/5"
      >
        {!isSidebarCollapsed && (
          <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[11px] space-y-1">
            <div className="flex items-center justify-between font-bold text-blue-600 dark:text-blue-400">
              <span className="flex items-center gap-1.5">
                <ShieldCheck size={14} />
                Edge AI Pipeline
              </span>
              <span className={`text-[10px] font-mono font-bold text-white px-1.5 rounded ${edgeColor}`}>{edgeLabel}</span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">
              {health?.db ? 'Backend online' : 'Backend offline'} · {edgeSeen == null ? 'edge fără date' : `edge acum ${Math.round(edgeSeen)}s`}
            </p>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">
              YOLO26 + ByteTrack • Auto-Snapshot
            </p>
          </div>
        )}

        <button
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          className="w-full flex items-center justify-center gap-2 py-2 px-2 rounded-xl bg-slate-500/10 hover:bg-slate-500/20 text-slate-700 dark:text-slate-200 transition-all font-semibold text-xs shadow-sm"
          title={isSidebarCollapsed ? 'Extinde Meniul' : 'Restrânge Meniul'}
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
