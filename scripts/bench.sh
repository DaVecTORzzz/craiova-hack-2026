#!/usr/bin/env bash
# Benchmark A/B pentru edge-uri, cu metodologia care nu te mintă:
#   * omoară edge-urile rămase (după executabil, nu după PID — un filtru greșit lasă
#     procese în urmă și face rularea următoare cu 30-50% mai rea);
#   * rulează configurațiile intercalat (deriva termică pe laptop e reală);
#   * măsoară fps doar cu un client conectat la /stream și CPU din /proc, nu din `ps`.
#
#   ./scripts/bench.sh --cameras 3 --runs 2 --config "torch" --config "ncnn:--backend ncnn"
#
# Fiecare `--config` e "nume" sau "nume:argumente pentru dev.py demo".
set -u

CAMERAS=3
RUNS=1
SETTLE=32
SECONDS_LIVE=12
CONFIGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cameras) CAMERAS="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    --settle) SETTLE="$2"; shift 2 ;;
    --seconds) SECONDS_LIVE="$2"; shift 2 ;;
    --config) CONFIGS+=("$2"); shift 2 ;;
    *) echo "necunoscut: $1" >&2; exit 2 ;;
  esac
done

if [[ ${#CONFIGS[@]} -eq 0 ]]; then
  CONFIGS=("torch" "ncnn:--backend ncnn")
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

kill_edges() {
  ps -eo pid,args --no-headers | awk '$2 ~ /python3$/ && $0 ~ /safesight_ml\.run/ {print $1}' | xargs -r kill 2>/dev/null
  sleep 2
}

edge_count() {
  ps -eo args --no-headers | awk '$1 ~ /python3$/ && $0 ~ /safesight_ml\.run/' | wc -l
}

live_fps() {
  python3 - "$SECONDS_LIVE" <<'PY'
import pathlib, sys, time
seconds = float(sys.argv[1])
path = pathlib.Path("backend/snapshots/live/stand12.jpg")
seen: set[int] = set()
start = time.time()
while time.time() - start < seconds:
    try:
        seen.add(path.stat().st_mtime_ns)
    except FileNotFoundError:
        pass
    time.sleep(0.03)
print(f"{len(seen) / seconds:.1f}")
PY
}

edge_cpu() {
  python3 - <<'PY'
import glob, os, time
CLK = os.sysconf("SC_CLK_TCK")

def edges() -> list[int]:
    pids = []
    for directory in glob.glob("/proc/[0-9]*"):
        try:
            with open(f"{directory}/cmdline", "rb") as handle:
                parts = handle.read().split(b"\0")
        except OSError:
            continue
        if not parts or not parts[0]:
            continue
        if os.path.basename(parts[0].decode(errors="ignore")) in ("uv", "bash", "sh"):
            continue
        if b"safesight_ml.run" in b" ".join(parts):
            pids.append(int(directory.split("/")[-1]))
    return pids

def cpu(pid: int) -> float:
    with open(f"/proc/{pid}/stat") as handle:
        fields = handle.read().split()
    return (int(fields[13]) + int(fields[14])) / CLK

pids = edges()
before = {pid: cpu(pid) for pid in pids}
start = time.time()
time.sleep(8)
spent = sum(cpu(pid) - before[pid] for pid in pids)
print(f"{spent / (time.time() - start) * 100:.0f}%")
PY
}

run_one() {
  local name="$1"
  local extra="$2"
  kill_edges
  fuser -k 8000/tcp 5173/tcp >/dev/null 2>&1
  sleep 2
  rm -f backend/safesight.db
  rm -rf backend/snapshots

  local camera_flag=()
  [[ "$CAMERAS" == "1" ]] && camera_flag=(--cameras stand12)

  # shellcheck disable=SC2086
  timeout $((SETTLE + SECONDS_LIVE + 60)) ./run.sh demo "${camera_flag[@]}" $extra --no-reload >/tmp/bench-edge.log 2>&1 &
  sleep "$SETTLE"

  local count
  count=$(edge_count)
  (timeout "$((SECONDS_LIVE + 8))" curl -s -o /dev/null http://127.0.0.1:8000/stream/stand12.mjpg &)
  sleep 6

  local fps cpu_used
  fps=$(live_fps)
  cpu_used=$(edge_cpu)
  printf "%-16s %-6s %-4s %8s %8s\n" "$name" "$CAMERAS" "$count" "$fps" "$cpu_used"
  if [[ "$count" -lt "$CAMERAS" ]]; then
    echo "  ! expected $CAMERAS edges, found $count - config rejected? see /tmp/bench-edge.log" >&2
  fi
}

echo "config           camere edge      fps      CPU"
for ((run = 1; run <= RUNS; run++)); do
  for entry in "${CONFIGS[@]}"; do
    name="${entry%%:*}"
    extra=""
    [[ "$entry" == *:* ]] && extra="${entry#*:}"
    run_one "$name" "$extra"
  done
done

kill_edges
fuser -k 8000/tcp 5173/tcp >/dev/null 2>&1
echo "gata (edge-uri oprite; ./run.sh demo pentru demo)"
