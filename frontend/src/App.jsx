import React from 'react';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { SecurityProvider, useSecurity } from './context/SecurityContext';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import LiveView from './components/views/LiveView';
import IncidentDetailView from './components/views/IncidentDetailView';
import ZoneEditorView from './components/views/ZoneEditorView';
import ReportsView from './components/views/ReportsView';
import SettingsView from './components/views/SettingsView';
import Toast from './components/common/Toast';

function MainAppLayout() {
  const { themeStyles } = useTheme();
  const { currentView, health } = useSecurity();

  const renderActiveView = () => {
    switch (currentView) {
      case 'incident_detail':
        return <IncidentDetailView />;
      case 'zones':
        return <ZoneEditorView />;
      case 'reports':
        return <ReportsView />;
      case 'settings':
        return <SettingsView />;
      case 'live':
      case 'dashboard':
      default:
        return <LiveView />;
    }
  };

  return (
    <div
      style={{
        backgroundColor: themeStyles.appBg,
        color: themeStyles.textColor
      }}
      className="h-screen w-screen flex flex-col overflow-hidden antialiased selection:bg-indigo-500 selection:text-white"
    >
      {/* 0. Banner de dezvoltare: blur-ul de fețe e oprit (SAFESIGHT_ALLOW_UNBLURRED=1).
          Nu e o setare a produsului; dacă apare, cineva testează local. */}
      {health?.unblurred && (
        <div className="shrink-0 bg-red-600 text-white text-center font-bold text-xs py-1.5 px-3 tracking-wide">
          BLURAREA FEȚELOR E OPRITĂ — MOD DEZVOLTARE. Nu arăta acest ecran public.
        </div>
      )}

      {/* 1. Header (Bara de Sus cu Brand SafeSight AI) */}
      <Header />

      {/* 2. Corp Principal (Sidebar Stânga + Conținut Activ din cele 6 Ecrane) */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-y-auto overflow-x-hidden relative min-h-0">
          {renderActiveView()}
        </div>
      </div>

      {/* 3. Notificări Toast */}
      <Toast />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <SecurityProvider>
        <MainAppLayout />
      </SecurityProvider>
    </ThemeProvider>
  );
}
