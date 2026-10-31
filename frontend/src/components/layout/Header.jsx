import React, { useState } from 'react';
import { Shield, Search, Moon, Sun, Wifi, WifiOff, RefreshCw, Zap, Bell, ChevronDown } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';
import { USE_MOCK } from '../../services/api';

export default function Header() {
  const { isDarkMode, toggleTheme, themeStyles } = useTheme();
  const {
    searchQuery,
    setSearchQuery,
    isWsConnected,
    operatorName,
    setOperatorName,
    simulateIncomingWsEvent,
    toggleWsSimulation
  } = useSecurity();

  const [showDemoMenu, setShowDemoMenu] = useState(false);
  const [operatorDraft, setOperatorDraft] = useState(operatorName);

  // Numele operatorului pleacă la ack / fals pozitiv / reopen; gol revine la numele curent.
  const commitOperator = () => {
    if (operatorDraft.trim()) setOperatorName(operatorDraft);
    else setOperatorDraft(operatorName);
  };

  return (
    <header
      style={{
        backgroundColor: themeStyles.panelBg,
        borderColor: themeStyles.panelBorder
      }}
      className="h-16 px-4 md:px-6 flex items-center justify-between border-b shadow-sm z-20 sticky top-0 shrink-0 select-none"
    >
      {/* Brand & Logo SafeSight AI */}
      <div className="flex items-center gap-3">
        <div
          style={{ backgroundColor: themeStyles.accentColor }}
          className="w-10 h-10 rounded-lg flex items-center justify-center text-white shadow-md transition-colors"
        >
          <Shield size={22} className="animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-black text-lg md:text-xl tracking-tight leading-none uppercase">
              SafeSight AI
            </h1>
            <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              TARMAC EDGE v1.0
            </span>
          </div>
          <p
            style={{ color: themeStyles.textMuted }}
            className="text-xs font-mono font-medium hidden md:block"
          >
            Airside Safety, FOD & PPE Compliance • Human-In-The-Loop
          </p>
        </div>
      </div>

      {/* Banner de Stare Conexiune WS (Conform Scenariului C-10: Banner în UI, nu doar consolă) */}
      {!isWsConnected && (
        <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-red-600/90 text-white rounded-lg text-xs font-bold animate-pulse">
          <WifiOff size={14} />
          <span>Conexiune pierdută cu Edge (Polling 2s activ)</span>
          <button
            onClick={toggleWsSimulation}
            className="ml-2 px-2 py-0.5 bg-black/40 hover:bg-black/60 rounded text-[10px] flex items-center gap-1"
          >
            <RefreshCw size={11} /> Reconectează
          </button>
        </div>
      )}

      {/* Bara de Căutare Evenimente */}
      <div className="flex-1 max-w-sm mx-4 hidden sm:block">
        <div className="relative">
          <Search
            size={16}
            style={{ color: themeStyles.textMuted }}
            className="absolute left-3 top-1/2 -translate-y-1/2"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Caută eveniment, track_id, FOD, stand12..."
            style={{
              backgroundColor: themeStyles.inputBg,
              color: themeStyles.textColor,
              borderColor: themeStyles.panelBorder
            }}
            className="w-full pl-9 pr-4 py-1.5 text-xs rounded-lg border focus:outline-none focus:ring-2 focus:ring-indigo-400 shadow-inner"
          />
        </div>
      </div>

      {/* Controale Dreapta: Demo Triggers, Toggle Teme, Operator */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Demo triggers sunt doar pentru modul mock; în demo real folosește backend/scripts/demo_event.py */}
        {USE_MOCK && (
        <div className="relative">
          <button
            onClick={() => setShowDemoMenu(!showDemoMenu)}
            className="px-2.5 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-400/30 text-xs font-bold flex items-center gap-1.5 shadow-sm"
            title="Triggers pentru prezentarea live în fața juriului"
          >
            <Zap size={14} className="text-amber-400" />
            <span className="hidden md:inline">Demo Pitch</span>
            <ChevronDown size={12} />
          </button>

          {showDemoMenu && (
            <div
              style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
              className="absolute right-0 mt-2 w-56 rounded-xl border p-2 shadow-2xl space-y-1 text-xs z-50 font-sans"
            >
              <div className="px-2 py-1 text-[10px] font-bold uppercase text-slate-400">
                Simulare C-01 & C-10 (Juriu)
              </div>
              <button
                onClick={() => {
                  simulateIncomingWsEvent('RESTRICTED_ZONE', 'CRITICAL');
                  setShowDemoMenu(false);
                }}
                className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-white/10 text-red-400 font-semibold flex items-center gap-2"
              >
                <Bell size={13} />
                <span>+ Alertă Nouă WS (C-01)</span>
              </button>
              <button
                onClick={() => {
                  simulateIncomingWsEvent('FOD_DETECTED', 'CRITICAL');
                  setShowDemoMenu(false);
                }}
                className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-white/10 text-amber-400 font-semibold flex items-center gap-2"
              >
                <Bell size={13} />
                <span>+ FOD pe Pistă (3s Seed)</span>
              </button>
              <button
                onClick={() => {
                  toggleWsSimulation();
                  setShowDemoMenu(false);
                }}
                className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-white/10 text-slate-300 font-semibold flex items-center gap-2"
              >
                <WifiOff size={13} />
                <span>{isWsConnected ? 'Deconectează WS (C-10)' : 'Reconectează WS'}</span>
              </button>
            </div>
          )}
        </div>
        )}

        {/* Toggle DARK / LIGHT MODE */}
        <button
          onClick={toggleTheme}
          style={{
            backgroundColor: themeStyles.cardBg,
            borderColor: themeStyles.panelBorder
          }}
          className="p-2 rounded-lg border hover:scale-105 transition-transform shadow-sm flex items-center gap-1.5 text-xs font-bold"
          title={isDarkMode ? 'Comută la Light Mode' : 'Comută la Dark Mode'}
        >
          {isDarkMode ? (
            <>
              <Sun size={16} className="text-amber-300" />
              <span className="hidden md:inline text-xs">Light</span>
            </>
          ) : (
            <>
              <Moon size={16} className="text-indigo-800" />
              <span className="hidden md:inline text-xs">Dark</span>
            </>
          )}
        </button>

        {/* Profil Operator (Ariana) */}
        <div
          style={{
            backgroundColor: themeStyles.cardBg,
            borderColor: themeStyles.panelBorder
          }}
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border shadow-sm"
        >
          <div className="relative">
            <div
              style={{ backgroundColor: themeStyles.accentColor }}
              className="w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs text-white"
            >
              {operatorName[0]}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-slate-900" />
          </div>
          <div className="hidden xl:block text-left text-xs leading-tight">
            <label className="font-bold flex items-center gap-1">
              Operator:
              <input
                value={operatorDraft}
                onChange={(e) => setOperatorDraft(e.target.value)}
                onBlur={commitOperator}
                onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }}
                maxLength={40}
                aria-label="Numele operatorului de tură"
                className="w-28 bg-transparent border-b border-white/20 focus:border-indigo-400 outline-none font-bold"
              />
            </label>
            <p style={{ color: themeStyles.textMuted }} className="text-[10px]">
              Tarmac Dispecerat
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
