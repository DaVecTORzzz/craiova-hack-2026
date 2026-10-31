#!/usr/bin/env bash
# Publish a demo clip to an RTSP server in a loop, so the edge sees a live stream.
#
#   ./scripts/rtsp-loop.sh
#   ./scripts/rtsp-loop.sh ../data/videos/clip.mp4 rtsp://127.0.0.1:8554/stand12
#
# The default assumes mediamtx is already listening on localhost:8554:
#   podman run --rm -d --name safesight-rtsp -p 8554:8554 bluenviron/mediamtx:latest
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CLIP="${1:-$REPO_ROOT/data/videos/2026-10-30_restricted-zone_cam01_persoana-langa-motor.mp4}"
URL="${2:-rtsp://127.0.0.1:8554/stand12}"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg lipsește; instalează ffmpeg înainte de demo." >&2
  exit 1
fi

if [[ ! -f "$CLIP" ]]; then
  echo "clipul nu există: $CLIP" >&2
  echo "pune clipul în data/videos/ sau dă calea ca prim argument." >&2
  exit 1
fi

echo "public ${CLIP} -> ${URL} (buclă; Ctrl-C pentru oprire)"

exec ffmpeg -hide_banner -loglevel warning \
  -nostdin -re -stream_loop -1 -i "$CLIP" \
  -an -c:v libx264 -preset ultrafast -tune zerolatency \
  -f rtsp -rtsp_transport tcp "$URL"
