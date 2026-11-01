import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Camera,
  Code,
  Copy,
  ImageOff,
  Layers,
  PenTool,
  Plus,
  Redo2,
  Save,
  Trash2,
  Undo2,
  X,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useSecurity } from '../../context/SecurityContext';

// Un punct e ținut în coordonate normalizate 0-1, ca poligonul să urmeze orice rezoluție.
const EMPTY_DRAFT = {
  name: '',
  rule_type: 'RESTRICTED',
  active_when: 'always',
  severity: 'CRITICAL',
  debounce_s: 1,
  notify_channel: 'slack',
  escalate_after_s: null,
};

const HISTORY_LIMIT = 60;

function rounded(point) {
  return { x: Number(point.x.toFixed(4)), y: Number(point.y.toFixed(4)) };
}

function distanceToSegment(point, start, end) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const lengthSquared = dx * dx + dy * dy;
  if (lengthSquared === 0) return Math.hypot(point.x - start.x, point.y - start.y);
  const t = Math.max(0, Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / lengthSquared));
  return Math.hypot(point.x - (start.x + t * dx), point.y - (start.y + t * dy));
}

/** Index of the edge the click is closest to, so the point lands between the two nearest. */
function nearestEdgeIndex(points, point) {
  let best = { index: 0, distance: Number.POSITIVE_INFINITY };
  for (let index = 0; index < points.length; index += 1) {
    const start = points[index];
    const end = points[(index + 1) % points.length];
    const distance = distanceToSegment(point, start, end);
    if (distance < best.distance) best = { index, distance };
  }
  return best.index;
}

function slugify(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);
}

function uniqueZoneId(base, zones) {
  const root = slugify(base) || 'zona-noua';
  if (!zones.some((zone) => zone.zone_id === root)) return root;
  let suffix = 2;
  while (zones.some((zone) => zone.zone_id === `${root}-${suffix}`)) suffix += 1;
  return `${root}-${suffix}`;
}

export default function ZoneEditorView() {
  const { themeStyles } = useTheme();
  const {
    cameras,
    selectedCameraId,
    setSelectedCameraId,
    activeCamera,
    zones,
    saveZone,
    deleteZone,
    captureReferenceFrame,
    clearReferenceFrame,
    showToast,
  } = useSecurity();

  const [zoneId, setZoneId] = useState('');
  const cameraZones = useMemo(
    () => zones.filter((item) => item.camera_id === selectedCameraId),
    [zones, selectedCameraId]
  );
  const zone = useMemo(
    () => cameraZones.find((item) => item.zone_id === zoneId) || null,
    [cameraZones, zoneId]
  );

  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [points, setPoints] = useState([]);
  const [closed, setClosed] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [dragIndex, setDragIndex] = useState(null);
  const [dragged, setDragged] = useState(false);
  const [history, setHistory] = useState({ past: [], future: [] });
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const [jsonInput, setJsonInput] = useState('[]');
  const [referenceAspect, setReferenceAspect] = useState(null);
  const [uploading, setUploading] = useState(false);

  const canvasRef = useRef(null);
  const referenceInputRef = useRef(null);
  const suppressClickRef = useRef(false);
  const dragStartRef = useRef(null);

  const hydrate = useCallback((nextZone) => {
    setPoints((nextZone?.polygon || []).map(rounded));
    setClosed((nextZone?.polygon || []).length >= 3);
    setDraft({
      name: nextZone?.name || nextZone?.zone_id || '',
      rule_type: nextZone?.rule_type || 'RESTRICTED',
      active_when: nextZone?.active_when || 'always',
      severity: nextZone?.severity || 'CRITICAL',
      debounce_s: nextZone?.debounce_s ?? 1,
      notify_channel: nextZone?.notify_channel || 'slack',
      escalate_after_s: nextZone?.escalate_after_s ?? null,
    });
    setHistory({ past: [], future: [] });
    setSelectedIndex(null);
    setReferenceAspect(null);
  }, []);

  // Se reîncarcă doar când se schimbă selecția, nu la fiecare actualizare a store-ului:
  // altfel o salvare (sau un eveniment) ar arunca editarea în curs.
  useEffect(() => {
    if (isNew) return; // o zonă nouă nu e încă în store: nu o înlocui
    const current = cameraZones.find((item) => item.zone_id === zoneId);
    if (current) {
      hydrate(current);
      return;
    }
    if (cameraZones.length > 0) {
      const preferred = cameraZones.find((item) => item.zone_id === 'engine-left') || cameraZones[0];
      setZoneId(preferred.zone_id);
    } else if (cameraZones.length === 0) {
      setZoneId('');
      setPoints([]);
      setDraft(EMPTY_DRAFT);
      setClosed(true);
      setHistory({ past: [], future: [] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCameraId, zoneId, isNew, cameraZones.length]);

  const pushPoints = useCallback(
    (next) => {
      setHistory((current) => ({
        past: [...current.past, points].slice(-HISTORY_LIMIT),
        future: [],
      }));
      setPoints(next);
      setJsonInput(JSON.stringify(next, null, 2));
    },
    [points]
  );

  const replacePoints = useCallback((next) => {
    setPoints(next);
    setJsonInput(JSON.stringify(next, null, 2));
  }, []);

  const undo = useCallback(() => {
    setHistory((current) => {
      if (current.past.length === 0) return current;
      const previous = current.past[current.past.length - 1];
      setPoints(previous);
      setJsonInput(JSON.stringify(previous, null, 2));
      setSelectedIndex(null);
      return { past: current.past.slice(0, -1), future: [points, ...current.future].slice(0, HISTORY_LIMIT) };
    });
  }, [points]);

  const redo = useCallback(() => {
    setHistory((current) => {
      if (current.future.length === 0) return current;
      const next = current.future[0];
      setPoints(next);
      setJsonInput(JSON.stringify(next, null, 2));
      setSelectedIndex(null);
      return { past: [...current.past, points].slice(-HISTORY_LIMIT), future: current.future.slice(1) };
    });
  }, [points]);

  const toNormalized = useCallback((event) => {
    const rect = canvasRef.current.getBoundingClientRect();
    return rounded({
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    });
  }, []);

  const addPoint = useCallback(
    (event) => {
      if (suppressClickRef.current) {
        suppressClickRef.current = false;
        return;
      }
      if (!zoneId) return;
      const point = toNormalized(event);
      const next =
        points.length >= 2
          ? (() => {
              // Între cele mai apropiate două puncte, nu la coada listei.
              const edge = nearestEdgeIndex(points, point);
              const copy = [...points];
              copy.splice(edge + 1, 0, point);
              return copy;
            })()
          : [...points, point];
      pushPoints(next);
      setSelectedIndex(next.length - 1);
      if (next.length >= 3) setClosed(true);
    },
    [points, pushPoints, toNormalized, zoneId]
  );

  const startDrag = (index) => (event) => {
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragStartRef.current = points;
    setDragIndex(index);
    setDragged(false);
    setSelectedIndex(index);
  };

  const moveDrag = (event) => {
    if (dragIndex === null) return;
    setDragged(true);
    const point = toNormalized(event);
    replacePoints(points.map((item, index) => (index === dragIndex ? point : item)));
  };

  const endDrag = () => {
    if (dragIndex === null) return;
    if (dragged) {
      // Un singur pas de undo pentru toată tragerea: starea de dinainte de pointerdown.
      const before = dragStartRef.current ?? points;
      setHistory((current) => ({ past: [...current.past, before].slice(-HISTORY_LIMIT), future: [] }));
      suppressClickRef.current = true;
    }
    setDragIndex(null);
    setDragged(false);
  };

  const removePoint = useCallback(
    (index) => {
      const next = points.filter((_, position) => position !== index);
      pushPoints(next);
      setSelectedIndex(null);
      if (next.length < 3) setClosed(false);
    },
    [points, pushPoints]
  );

  const handleKeyDown = useCallback((event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
    const step = event.shiftKey ? 0.01 : 0.002;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
      event.preventDefault();
      if (event.shiftKey) redo();
      else undo();
      return;
    }
    if (selectedIndex === null) return;
    if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault();
      removePoint(selectedIndex);
      return;
    }
    const deltas = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    const delta = deltas[event.key];
    if (!delta) return;
    event.preventDefault();
    const point = points[selectedIndex];
    const next = points.map((item, index) =>
      index === selectedIndex
        ? rounded({ x: Math.max(0, Math.min(1, point.x + delta[0])), y: Math.max(0, Math.min(1, point.y + delta[1])) })
        : item
    );
    replacePoints(next);
  }, [points, redo, removePoint, replacePoints, selectedIndex, undo]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleCanvasDoubleClick = () => {
    if (points.length >= 3) {
      setClosed(true);
      showToast('Poligon închis. Trage de puncte ca să ajustezi.');
    } else {
      showToast('Ai nevoie de cel puțin 3 puncte.');
    }
  };

  const handleApplyJson = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      const valid =
        Array.isArray(parsed) &&
        parsed.length >= 3 &&
        parsed.every((point) => typeof point?.x === 'number' && typeof point?.y === 'number');
      if (!valid) {
        showToast('JSON invalid: ai nevoie de minimum 3 puncte {x, y}.');
        return;
      }
      pushPoints(parsed.map(rounded));
      setClosed(true);
      showToast('Coordonate aplicate pe cadru.');
    } catch {
      showToast('JSON invalid: nu am putut parsa coordonatele.');
    }
  };

  const handleNewZone = () => {
    const id = uniqueZoneId(`${selectedCameraId}-zona`, zones);
    setIsNew(true);
    setZoneId(id);
    setPoints([]);
    setClosed(false);
    setHistory({ past: [], future: [] });
    setSelectedIndex(null);
    setDraft({ ...EMPTY_DRAFT, name: id });
    showToast('Zonă nouă: desenează poligonul, apoi salvează.');
  };

  const handleDeleteZone = async () => {
    if (!zoneId) return;
    if (!window.confirm(`Ștergi zona „${zoneId}"? Acțiunea nu poate fi anulată.`)) return;
    await deleteZone(zoneId);
    const remaining = cameraZones.filter((item) => item.zone_id !== zoneId);
    setZoneId(remaining[0]?.zone_id || '');
    setPoints([]);
    setClosed(true);
  };

  const handleSave = async () => {
    if (!zoneId) {
      showToast('Completează un ID de zonă.');
      return;
    }
    if (!/^[a-z0-9-]+$/.test(zoneId)) {
      showToast('ID-ul poate conține doar litere mici, cifre și cratime.');
      return;
    }
    if (points.length < 3) {
      showToast('Poligonul are nevoie de minimum 3 puncte.');
      return;
    }
    const payload = {
      zone_id: zoneId,
      camera_id: selectedCameraId,
      name: draft.name?.trim() || zoneId,
      rule_type: draft.rule_type,
      active_when: draft.active_when,
      required_ppe: zone?.required_ppe || [],
      severity: draft.severity,
      debounce_s: Number(draft.debounce_s) || 0,
      notify_channel: 'slack',
      escalate_after_s:
        draft.escalate_after_s === null || draft.escalate_after_s === ''
          ? null
          : Number(draft.escalate_after_s),
      polygon: points.map(({ x, y }) => ({ x, y })),
      reference_frame: zone?.reference_frame || null,
    };
    setSaving(true);
    try {
      await saveZone(zoneId, payload);
      setIsNew(false);
    } finally {
      setSaving(false);
    }
  };

  const handleReferenceUpload = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !zoneId) return;
    setUploading(true);
    try {
      // Backend-ul acceptă doar JPEG; orice imagine aleasă e convertită aici, ca omul să
      // nu trebuiască să caute un convertor.
      const bitmap = await createImageBitmap(file);
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext('2d').drawImage(bitmap, 0, 0);
      bitmap.close?.();
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
      if (!blob) throw new Error('conversia în JPEG a eșuat');
      await captureReferenceFrame(zoneId, new File([blob], 'referinta.jpg', { type: 'image/jpeg' }));
    } catch (error) {
      showToast(`Încărcarea referinței a eșuat: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleCopyFrom = () => {
    const other = zones.find((item) => item.camera_id !== selectedCameraId && (item.polygon || []).length >= 3);
    if (!other) {
      showToast('Nu există o zonă pe altă cameră din care să copiezi.');
      return;
    }
    pushPoints(other.polygon.map(rounded));
    setClosed(true);
    showToast(`Poligon copiat din ${other.camera_id} / ${other.zone_id}.`);
  };

  if (!activeCamera) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div
          style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
          className="max-w-md rounded-xl border p-5 text-center space-y-2"
        >
          <h2 className="font-bold text-sm uppercase">Nu există camere</h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs">
            Backend-ul nu a returnat camere. Pornește stack-ul cu ./run.sh demo.
          </p>
        </div>
      </div>
    );
  }

  const canSave = Boolean(zoneId) && points.length >= 3 && !saving;
  const hasReference = Boolean(zone?.reference_frame_url);

  return (
    <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 h-full max-w-7xl mx-auto">
      <div className="flex items-center justify-between border-b border-white/10 pb-3 flex-wrap gap-2">
        <div>
          <h2 className="font-black text-lg uppercase tracking-tight flex items-center gap-2">
            <PenTool size={20} className="text-indigo-400" />
            Configurare zone
          </h2>
          <p style={{ color: themeStyles.textMuted }} className="text-xs font-mono">
            Trage punctele cu mouse-ul · click pe latură adaugă între cele mai apropiate două · click dreapta șterge
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyFrom}
            disabled={!zoneId}
            className="px-2.5 py-1.5 rounded-lg border border-white/20 hover:bg-white/10 disabled:opacity-40 text-xs font-mono font-bold flex items-center gap-1.5"
            title="Copiază poligonul celei mai apropiate zone de pe altă cameră"
          >
            <Copy size={14} /> Copiază de pe altă cameră
          </button>
          <button
            onClick={() => setShowJson(!showJson)}
            className="px-2.5 py-1.5 rounded-lg border border-white/20 hover:bg-white/10 text-xs font-mono font-bold flex items-center gap-1.5"
          >
            <Code size={14} /> JSON
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 space-y-3">
          <div className="flex items-center gap-2 text-xs flex-wrap">
            <span className="font-bold opacity-75">Camera:</span>
            {cameras.map((camera) => (
              <button
                key={camera.id}
                onClick={() => setSelectedCameraId(camera.id)}
                className={`px-2.5 py-1 rounded font-mono font-bold border ${
                  camera.id === selectedCameraId
                    ? 'bg-indigo-600 text-white border-indigo-400'
                    : 'bg-black/30 text-slate-300 border-white/10'
                }`}
              >
                {camera.id}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-bold opacity-75 mr-1">Zone salvate:</span>
            {cameraZones.length === 0 && (
              <span className="text-[11px] font-mono text-amber-300/80">
                niciuna pe camera asta — creează una
              </span>
            )}
            {cameraZones.map((item) => (
              <button
                key={item.zone_id}
                data-testid={`zone-chip-${item.zone_id}`}
                onClick={() => {
                  setIsNew(false);
                  setZoneId(item.zone_id);
                }}
                className={`px-2.5 py-1 rounded border text-[11px] font-mono flex items-center gap-1.5 ${
                  item.zone_id === zoneId
                    ? 'bg-emerald-700/70 border-emerald-400 text-white'
                    : 'bg-black/30 border-white/10 text-slate-300 hover:bg-white/10'
                }`}
                title={`${item.rule_type} · ${(item.polygon || []).length} puncte`}
              >
                {item.zone_id}
                <span className="opacity-60">{item.rule_type === 'PPE_REQUIRED' ? 'PPE' : item.rule_type === 'RESTRICTED' ? 'ZONĂ' : item.rule_type}</span>
              </button>
            ))}
            <button
              data-testid="zone-new"
              onClick={handleNewZone}
              className="px-2.5 py-1 rounded border border-emerald-400/40 bg-emerald-900/30 text-emerald-200 text-[11px] font-bold flex items-center gap-1 hover:bg-emerald-800/40"
            >
              <Plus size={12} /> Zonă nouă
            </button>
          </div>

          <div
            data-testid="zone-canvas"
            ref={canvasRef}
            onClick={addPoint}
            onDoubleClick={handleCanvasDoubleClick}
            style={hasReference && referenceAspect ? { aspectRatio: referenceAspect } : undefined}
            className={`relative rounded-xl overflow-hidden bg-black border-2 border-indigo-500/40 shadow-2xl select-none ${
              hasReference && referenceAspect ? 'w-full max-h-[68vh] mx-auto' : 'min-h-[380px]'
            } ${dragIndex === null ? 'cursor-crosshair' : 'cursor-move'}`}
          >
            {hasReference ? (
              <img
                key={zone.reference_frame_url}
                src={zone.reference_frame_url}
                alt="Cadru de referință"
                className="absolute inset-0 w-full h-full object-fill pointer-events-none"
                draggable={false}
                onLoad={(event) => {
                  const { naturalWidth, naturalHeight } = event.currentTarget;
                  if (naturalWidth && naturalHeight) setReferenceAspect(naturalWidth / naturalHeight);
                }}
                onError={() => setReferenceAspect(null)}
              />
            ) : (
              <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-black flex items-center justify-center">
                <p className="text-[11px] text-slate-400 font-mono text-center px-6">
                  Fără cadru de referință. Încarcă unul din panoul din dreapta,
                  <br />
                  sau pornește edge-ul ca să apară imaginea camerei.
                </p>
              </div>
            )}

            <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none">
              {points.length > 1 && (
                <polygon
                  points={points.map((point) => `${point.x * 1000},${point.y * 1000}`).join(' ')}
                  fill="rgba(239, 68, 68, 0.18)"
                  stroke="#EF4444"
                  strokeWidth="2.5"
                  vectorEffect="non-scaling-stroke"
                  strokeDasharray={closed ? 'none' : '6,4'}
                />
              )}
            </svg>

            {points.map((point, index) => (
              <div
                data-testid={`zone-point-${index}`}
                key={index}
                onPointerDown={startDrag(index)}
                onPointerMove={moveDrag}
                onPointerUp={endDrag}
                onPointerCancel={endDrag}
                onClick={(event) => event.stopPropagation()}
                onContextMenu={(event) => {
                  event.preventDefault();
                  removePoint(index);
                }}
                style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                className={`group absolute w-4 h-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 shadow-lg touch-none ${
                  selectedIndex === index || dragIndex === index
                    ? 'bg-emerald-400 border-emerald-200 ring-4 ring-emerald-400/40'
                    : 'bg-white border-red-600 ring-2 ring-red-400/40'
                }`}
                title={`Punct ${index + 1}: (${point.x.toFixed(3)}, ${point.y.toFixed(3)}) — trage, click dreapta șterge`}
              >
                <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[9px] font-mono text-white/80">
                  {index + 1}
                </span>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    removePoint(index);
                  }}
                  className="hidden group-hover:flex absolute -top-2 -right-2 w-4 h-4 items-center justify-center rounded-full bg-red-600 text-white border border-black/40"
                  title="Șterge punctul"
                >
                  <X size={10} />
                </button>
              </div>
            ))}

            <div className="absolute top-3 left-3 bg-black/80 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10 text-white text-[11px] font-mono shadow">
              {closed ? '✓ poligon închis' : 'desenare: click = punct · dublu-click = închide'}
            </div>

            <div className="absolute bottom-3 right-3 flex items-center gap-1.5">
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  undo();
                }}
                disabled={history.past.length === 0}
                className="p-1.5 rounded bg-black/70 border border-white/20 text-white disabled:opacity-30"
                title="Undo (Ctrl+Z)"
              >
                <Undo2 size={14} />
              </button>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  redo();
                }}
                disabled={history.future.length === 0}
                className="p-1.5 rounded bg-black/70 border border-white/20 text-white disabled:opacity-30"
                title="Redo (Ctrl+Shift+Z)"
              >
                <Redo2 size={14} />
              </button>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  pushPoints([]);
                  setClosed(false);
                  setSelectedIndex(null);
                }}
                className="px-2.5 py-1 rounded bg-red-900/80 hover:bg-red-800 text-white text-xs font-bold flex items-center gap-1 border border-red-500/40"
              >
                <Trash2 size={13} /> Golește
              </button>
            </div>
          </div>

          {showJson && (
            <div
              style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
              className="p-3 rounded-xl border space-y-2 text-xs"
            >
              <div className="flex items-center justify-between font-bold font-mono text-[11px]">
                <span>Coordonate normalizate (JSON)</span>
                <button onClick={handleApplyJson} className="px-2 py-0.5 bg-indigo-600 text-white rounded text-[10px]">
                  Aplică pe cadru
                </button>
              </div>
              <textarea
                value={jsonInput}
                onChange={(event) => setJsonInput(event.target.value)}
                rows={4}
                className="w-full p-2 rounded bg-black/40 border border-white/10 font-mono text-[10px] text-emerald-400"
              />
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div
            style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
            className="rounded-xl border p-4 shadow-lg space-y-3 text-xs"
          >
            <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
              <Layers size={16} className="text-indigo-400" /> Parametri
            </h3>

            <div>
              <label className="font-bold block mb-1">ID zonă</label>
              <input
                type="text"
                value={zoneId}
                disabled={Boolean(zone) && !isNew}
                onChange={(event) => setZoneId(slugify(event.target.value))}
                className="w-full p-2 rounded bg-black/30 border border-white/20 font-mono text-xs disabled:opacity-60"
                placeholder="engine-left"
              />
              {Boolean(zone) && !isNew && (
                <p className="text-[10px] font-mono opacity-60 mt-1">
                  ID-ul e cheia zonei; pentru alt nume folosește câmpul „Nume".
                </p>
              )}
            </div>

            <div>
              <label className="font-bold block mb-1">Nume</label>
              <input
                type="text"
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs"
                placeholder="Motor stâng"
              />
            </div>

            <div>
              <label className="font-bold block mb-1">Tip regulă</label>
              <select
                value={draft.rule_type}
                onChange={(event) => setDraft({ ...draft, rule_type: event.target.value })}
                className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white"
              >
                <option value="RESTRICTED">RESTRICTED (zonă interzisă)</option>
                <option value="PPE_REQUIRED">PPE_REQUIRED (echipament obligatoriu)</option>
                <option value="FOD_WATCH">FOD_WATCH (obiecte pe tarmac)</option>
              </select>
            </div>

            <div>
              <label className="font-bold block mb-1">Activă când</label>
              <select
                value={draft.active_when}
                onChange={(event) => setDraft({ ...draft, active_when: event.target.value })}
                className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white"
              >
                <option value="always">always — permanent</option>
                <option value="engine_on">engine_on — doar cu motorul pornit</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="font-bold block mb-1">Severitate</label>
                <select
                  value={draft.severity}
                  onChange={(event) => setDraft({ ...draft, severity: event.target.value })}
                  className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white"
                >
                  <option value="CRITICAL">CRITICAL</option>
                  <option value="WARNING">WARNING</option>
                </select>
              </div>
              <div>
                <label className="font-bold block mb-1">Debounce (s)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  value={draft.debounce_s}
                  onChange={(event) => setDraft({ ...draft, debounce_s: event.target.value })}
                  className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs font-mono"
                />
              </div>
            </div>

            <div>
              <label className="font-bold block mb-1">Escaladează după</label>
              <select
                value={draft.escalate_after_s ?? 'null'}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    escalate_after_s: event.target.value === 'null' ? null : Number(event.target.value),
                  })
                }
                className="w-full p-2 rounded bg-black/30 border border-white/20 text-xs text-white font-mono"
              >
                <option value="30">30 s</option>
                <option value="60">60 s</option>
                <option value="120">120 s</option>
                <option value="null">niciodată</option>
              </select>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <button
                data-testid="zone-save"
                onClick={handleSave}
                disabled={!canSave}
                className="flex-1 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg"
              >
                <Save size={15} /> {saving ? 'Se salvează…' : `Salvează (${points.length} puncte)`}
              </button>
              <button
                onClick={handleDeleteZone}
                disabled={!zone}
                className="p-2.5 rounded-lg border border-red-500/40 text-red-300 hover:bg-red-900/40 disabled:opacity-30"
                title="Șterge zona"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>

          <div
            style={{ backgroundColor: themeStyles.panelBg, borderColor: themeStyles.panelBorder }}
            className="rounded-xl border p-4 shadow-lg space-y-2 text-xs"
          >
            <h3 className="font-bold text-sm uppercase tracking-wider flex items-center gap-2">
              <Camera size={16} className="text-indigo-400" /> Referință FOD
            </h3>
            <p style={{ color: themeStyles.textMuted }} className="text-[11px] leading-snug">
              Cadrul pe care desenezi zonele. Folosește doar un cadru <b>deja blurat</b> — nicio față nu
              trebuie să ajungă aici.
            </p>

            <input
              ref={referenceInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleReferenceUpload}
            />

            {hasReference ? (
              <div className="space-y-2">
                <img
                  src={zone.reference_frame_url}
                  alt="Referință"
                  className="w-full rounded-lg border border-white/10"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => referenceInputRef.current?.click()}
                    disabled={uploading || !zone}
                    className="flex-1 py-1.5 rounded bg-indigo-700 hover:bg-indigo-600 disabled:opacity-50 text-white text-[11px] font-bold"
                  >
                    {uploading ? 'Se încarcă…' : 'Înlocuiește'}
                  </button>
                  <button
                    onClick={() => clearReferenceFrame(zoneId)}
                    disabled={!zone}
                    className="px-2 py-1.5 rounded border border-red-500/40 text-red-300 hover:bg-red-900/40 text-[11px] font-bold flex items-center gap-1"
                  >
                    <ImageOff size={12} /> Șterge
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => referenceInputRef.current?.click()}
                disabled={!zone || uploading}
                className="w-full py-6 rounded-lg border-2 border-dashed border-white/20 hover:border-indigo-400/60 text-slate-300 text-[11px] font-mono flex flex-col items-center gap-1 disabled:opacity-40"
              >
                <Camera size={18} />
                {uploading ? 'se încarcă…' : zone ? 'încarcă imagine (JPG/PNG)' : 'salvează zona întâi'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
