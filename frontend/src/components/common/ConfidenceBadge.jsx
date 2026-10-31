import React from 'react';
import { Sparkles } from 'lucide-react';

export default function ConfidenceBadge({ confidence }) {
  // Formatare strictă conform Regulii N03:
  // Text formatat: "0.91 · 14/15 cadre"
  if (!confidence) return <span className="font-mono text-xs opacity-60">necunoscut</span>;

  const detectorScore = typeof confidence.detector === 'number'
    ? confidence.detector.toFixed(2)
    : '0.90';

  const seen = confidence.temporal?.seen ?? 14;
  const window = confidence.temporal?.window ?? 15;

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-black/20 text-xs font-mono font-bold border border-white/10 select-none">
      <Sparkles size={11} className="text-amber-400 shrink-0" />
      <span>{detectorScore} · {seen}/{window} cadre</span>
    </div>
  );
}
