import React from 'react';
import { Sparkles } from 'lucide-react';

export default function ConfidenceBar({ score }) {
  return (
    <div className="space-y-1 select-none">
      <div className="flex justify-between items-center text-[10px]">
        <span className="font-semibold flex items-center gap-1 opacity-90">
          <Sparkles size={11} className="text-amber-400" />
          Confidence Score:
        </span>
        <span className="font-mono font-black text-xs">
          {score}%
        </span>
      </div>

      {/* Bara cu Gradient Multi-Stop Roșu -> Portocaliu -> Verde */}
      <div className="w-full h-2 rounded-full overflow-hidden bg-black/30 relative">
        {/* Fundal gradient subtil */}
        <div className="absolute inset-0 bg-gradient-to-r from-red-600 via-amber-400 to-emerald-500 opacity-25" />
        {/* Bară umplută proporțional cu scorul */}
        <div
          style={{ width: `${score}%` }}
          className="h-full bg-gradient-to-r from-red-600 via-amber-400 to-emerald-500 transition-all duration-500 rounded-full shadow"
        />
      </div>

      <div className="flex justify-between text-[8px] font-mono opacity-60">
        <span>0% Critic (Roșu)</span>
        <span>50% Avertisment</span>
        <span>100% Conform / Ok</span>
      </div>
    </div>
  );
}
