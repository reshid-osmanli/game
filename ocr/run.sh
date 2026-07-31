#!/usr/bin/env bash
# dispatcher: tesseract baseline (v1) then high-accuracy surya (v2)
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

if [ -s ocr_out/book.txt ] && [ -s ocr_out/DONE.txt ]; then
  echo "[dispatcher] tesseract baseline already complete, skipping v1"
else
  bash ocr/run_tesseract.sh || echo "[dispatcher] v1 failed"
fi

bash ocr/run_v2.sh || echo "[dispatcher] v2 failed"
