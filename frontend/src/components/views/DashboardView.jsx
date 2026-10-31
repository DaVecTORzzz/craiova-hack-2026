import React from 'react';
import VideoPlayer from '../video/VideoPlayer';
import CameraCarousel from '../video/CameraCarousel';
import IncidentSidebar from '../incidents/IncidentSidebar';
import { useSecurity } from '../../context/SecurityContext';

export default function DashboardView() {
  const { setCurrentView } = useSecurity();

  return (
    <div className="flex-1 flex flex-col lg:flex-row overflow-hidden h-full">
      {/* Zona Centrală: Player Video + Miniaturi Camere */}
      <main className="flex-1 flex flex-col p-3 md:p-4 overflow-y-auto min-w-0 space-y-3 h-full">
        <VideoPlayer onMaximize={() => setCurrentView('fullscreen')} />
        <CameraCarousel />
      </main>

      {/* Zona Dreapta: Alerte Incidente AI & XAI */}
      <IncidentSidebar />
    </div>
  );
}
