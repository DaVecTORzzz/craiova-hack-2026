#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p models

url="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
out="models/face_detection_yunet_2023mar.onnx"

if [[ -f "$out" ]]; then
  echo "already present: $out"
  exit 0
fi

echo "downloading $out"
curl -L --fail --silent --show-error "$url" -o "$out"
echo "done: $out"
