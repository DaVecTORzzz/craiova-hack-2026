import React from 'react';
import { Info } from 'lucide-react';
import { useSecurity } from '../../context/SecurityContext';

export default function Toast() {
  const { toastMessage } = useSecurity();

  if (!toastMessage) return null;

  return (
    <div className="no-print fixed bottom-5 right-5 z-50 bg-slate-900/95 text-white px-4 py-3 rounded-xl shadow-2xl border border-indigo-500/60 flex items-center gap-3 animate-bounce-short font-sans text-xs md:text-sm backdrop-blur-md select-none max-w-md">
      <Info size={18} className="text-indigo-400 shrink-0" />
      <span className="leading-snug">{toastMessage}</span>
    </div>
  );
}
