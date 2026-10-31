import React, { useEffect, useState } from 'react';
import { Shield, Search, Moon, Sun, Wifi, WifiOff, RefreshCw, Zap, Bell, ChevronDown, Check, UserCheck } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import { USE_MOCK } from '../../services/api';

export default function Header() {
  const { isDarkMode, toggleTheme, themeStyles } = useTheme();
  const {
    searchQuery,
    setSearchQuery,
    isWsConnected,
    activeOperator,
    availableOperators,
    switchOperator,
    operatorName,
    setOperatorName,
    simulateIncomingWsEvent,
    toggleWsSimulation
  } = useSecurity();

  const [showDemoMenu, setShowDemoMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [operatorDraft, setOperatorDraft] = useState(operatorName);

  useEffect(() => {
    setOperatorDraft(operatorName);
  }, [operatorName]);

  const commitOperator = () => {
    setOperatorName(operatorDraft);
  };

  return (
    <header
      style={{
        backgroundColor: themeStyles.navBg || themeStyles.panelBg,
        borderColor: themeStyles.navBorder || themeStyles.panelBorder,
        color: '#FFFFFF'
      }}
      className="h-16 px-4 md:px-6 flex items-center justify-between border-b shadow-md z-30 sticky top-0 shrink-0 select-none transition-colors"
    >
      {/* 1. Brand & Titlu SafeSight */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md border border-white/20">
          <Shield size={22} className="text-white" />
        </div>
        <div>
          <h1 className="font-black text-xl tracking-tight leading-none text-white uppercase drop-shadow-sm">
            SafeSight
          </h1>
          <p className="text-xs font-medium text-blue-100/90 tracking-wide mt-0.5">
            Management condiții siguranță
          </p>
        </div>
      </div>

      {/* 2. Banner Conexiune Edge (C-10) */}
      {!isWsConnected && (
        <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-red-600 text-white rounded-lg text-xs font-bold shadow-md animate-pulse">
          <WifiOff size={14} />
          <span>Semnal Edge Pierdut (Polling activat)</span>
          <button
            onClick={toggleWsSimulation}
            className="ml-2 px-2 py-0.5 bg-black/40 hover:bg-black/60 rounded text-[10px] flex items-center gap-1 font-mono"
          >
            <RefreshCw size={11} /> Reconectează
          </button>
        </div>
      )}

      {/* 3. Bara de Căutare (Placeholder simplificat: "Cauta incidente") */}
      <div className="flex-1 max-w-xs md:max-w-sm mx-4 hidden sm:block">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cauta incidente"
            className="w-full pl-10 pr-4 py-2 text-xs rounded-xl bg-white/10 hover:bg-white/15 focus:bg-white/20 border border-white/20 text-white placeholder-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all shadow-inner"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-300 hover:text-white text-xs font-bold"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* 4. Controale Dreapta: Demo Triggers, Dark/Light Mode, Selector User */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Trigger-ele demo sunt doar pentru mock; în real se folosește backend/scripts/demo_event.py */}
        {USE_MOCK && (
        <div className="relative">
          <button
            onClick={() => {
              setShowDemoMenu(!showDemoMenu);
              setShowUserMenu(false);
            }}
            className="px-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white border border-white/20 text-xs font-bold flex items-center gap-1.5 transition-colors shadow-sm"
            title="Triggers pentru prezentarea live în fața juriului"
          >
            <Zap size={14} className="text-amber-300 fill-amber-300" />
            <span className="hidden md:inline">Demo Pitch</span>
            <ChevronDown size={12} className="opacity-80" />
          </button>

          {showDemoMenu && (
            <div
              style={{
                backgroundColor: isDarkMode ? '#1E2433' : '#FFFFFF',
                borderColor: isDarkMode ? 'rgba(255,255,255,0.15)' : '#E2E8F0',
                color: isDarkMode ? '#F8FAFC' : '#212121'
              }}
              className="absolute right-0 mt-2 w-64 rounded-xl border p-2 shadow-2xl space-y-1 text-xs z-50 font-sans"
            >
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b pb-1 mb-1">
                Simulare Scenarii Live (Juriu)
              </div>
              <button
                onClick={() => {
                  simulateIncomingWsEvent('RESTRICTED_ZONE', 'CRITICAL');
                  setShowDemoMenu(false);
                }}
                className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-red-500/10 text-red-600 dark:text-red-400 font-semibold flex items-center gap-2 transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-red-600 shrink-0" />
                <span>+ Alertă Zonă Motor (C-01)</span>
              </button>
              <button
                onClick={() => {
                  simulateIncomingWsEvent('FOD', 'CRITICAL');
                  setShowDemoMenu(false);
                }}
                className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-amber-500/10 text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-2 transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
                <span>+ Fragment FOD Pistă 08R (3s)</span>
              </button>
              <button
                onClick={() => {
                  toggleWsSimulation();
                  setShowDemoMenu(false);
                }}
                className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-500/10 font-semibold flex items-center gap-2 transition-colors"
              >
                <WifiOff size={13} className="text-slate-400" />
                <span>{isWsConnected ? 'Deconectează WS (C-10)' : 'Reconectează WS'}</span>
              </button>
            </div>
          )}
        </div>
        )}

        {/* Toggle Dark / Light Mode (WCAG compliant) */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-all shadow-sm flex items-center gap-1.5 text-xs font-bold"
          title={isDarkMode ? 'Comută la Light Mode (Pânză neutră)' : 'Comută la Dark Mode (Consolă de noapte)'}
        >
          {isDarkMode ? (
            <>
              <Sun size={16} className="text-amber-300" />
              <span className="hidden md:inline text-xs font-medium">Light</span>
            </>
          ) : (
            <>
              <Moon size={16} className="text-blue-200" />
              <span className="hidden md:inline text-xs font-medium">Dark</span>
            </>
          )}
        </button>

        {/* Selector Operator / Profil Activ */}
        <div className="relative">
          <button
            onClick={() => {
              setShowUserMenu(!showUserMenu);
              setShowDemoMenu(false);
            }}
            className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 transition-all shadow-sm"
            title="Schimbă operatorul activ"
          >
            <div className="w-7 h-7 rounded-lg bg-blue-500 text-white font-bold text-xs flex items-center justify-center shadow-inner">
              {operatorName?.[0] || 'A'}
            </div>
            <div className="hidden lg:block text-left text-xs leading-tight">
              <p className="font-bold text-white flex items-center gap-1">
                <span>{operatorName || 'Operator'}</span>
                <ChevronDown size={11} className="opacity-70" />
              </p>
              <p className="text-[10px] text-blue-200 font-medium">
                {activeOperator ? activeOperator.badge : 'AIRSIDE-LEAD'}
              </p>
            </div>
          </button>

          {showUserMenu && availableOperators && (
            <div
              style={{
                backgroundColor: isDarkMode ? '#1E2433' : '#FFFFFF',
                borderColor: isDarkMode ? 'rgba(255,255,255,0.15)' : '#E2E8F0',
                color: isDarkMode ? '#F8FAFC' : '#212121'
              }}
              className="absolute right-0 mt-2 w-64 rounded-xl border p-2 shadow-2xl space-y-1 text-xs z-50 font-sans"
            >
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b pb-1 mb-1">
                Selectare Operator / Rol
              </div>
              {availableOperators.map((op) => {
                const isSelected = activeOperator && op.id === activeOperator.id;
                return (
                  <button
                    key={op.id}
                    onClick={() => {
                      switchOperator(op.id);
                      setShowUserMenu(false);
                    }}
                    className={`w-full text-left px-2.5 py-2 rounded-lg flex items-center justify-between transition-colors ${
                      isSelected
                        ? 'bg-blue-600 text-white font-bold'
                        : 'hover:bg-slate-500/10'
                    }`}
                  >
                    <div>
                      <p className="font-semibold text-xs leading-none">{op.name}</p>
                      <p className={`text-[10px] mt-0.5 ${isSelected ? 'text-blue-100' : 'text-slate-500 dark:text-slate-400'}`}>
                        {op.role}
                      </p>
                    </div>
                    {isSelected && <Check size={14} className="text-white shrink-0" />}
                  </button>
                );
              })}
              <div className="border-t border-slate-500/20 pt-2 mt-2 space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-1 block">
                  Nume afișat
                </label>
                <input
                  value={operatorDraft}
                  onChange={(event) => setOperatorDraft(event.target.value)}
                  onBlur={commitOperator}
                  onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur(); }}
                  maxLength={40}
                  aria-label="Numele operatorului de tură"
                  style={{
                    backgroundColor: isDarkMode ? 'rgba(255,255,255,0.08)' : '#F1F5F9',
                    color: isDarkMode ? '#F8FAFC' : '#212121',
                    borderColor: isDarkMode ? 'rgba(255,255,255,0.15)' : '#CBD5E1'
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg border text-xs font-semibold outline-none focus:ring-2 focus:ring-blue-400"
                />
                <p className="text-[10px] text-slate-400 px-1">
                  Enter sau click în afara câmpului pentru salvare.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
