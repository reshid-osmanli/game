#!/usr/bin/env bash
# v2 pipeline: high-accuracy Arabic OCR (surya) + optional Qari samples
set -uo pipefail

FILE_ID="1k9Q7moUs8LBkMp4g6fTa5pxBXs7c4D72"
BRANCH="arena/019fb85f-game"
CH=20

cd "$(git rev-parse --show-toplevel)"
mkdir -p work/pages ocr_out/compare ocr_out/surya_pages ocr_out/logs

git config user.name "arena-ocr-bot"
git config user.email "arena-ocr-bot@users.noreply.github.com"

exec > >(tee work/v2.log) 2>&1

on_exit() {
  code=$?
  echo "[exit handler] exit code = $code"
  cp work/v2.log ocr_out/logs/ 2>/dev/null || true
  cp work/v2_surya.log ocr_out/logs/ 2>/dev/null || true
  git add ocr_out/ 2>/dev/null
  git commit -m "ocr v2: run ended (exit=$code)" >/dev/null 2>&1 || true
  git push origin "HEAD:${BRANCH}" >/dev/null 2>&1 || true
}
trap on_exit EXIT

push_checkpoint() {
  git add ocr_out/ && git commit -m "$1" >/dev/null 2>&1 || true
  git fetch origin "${BRANCH}" >/dev/null 2>&1 || true
  git rebase "origin/${BRANCH}" >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1 || true
  git push origin "HEAD:${BRANCH}" || true
}

[ -f ocr/DISABLE_V2 ] && { echo "v2 disabled"; exit 0; }

echo "==== v2 [1/5] deps ===="
pip install --quiet "surya-ocr" "transformers>=4.45" "accelerate" "qwen-vl-utils" 2>&1 | tail -3
pip show surya-ocr 2>/dev/null | head -3 || true
( surya_ocr --help 2>&1 || true ) | tee ocr_out/logs/surya_help.txt | head -40

echo "==== v2 [2/5] ensure pdf + render ===="
if [ ! -s work/book.pdf ]; then
  for attempt in 1 2 3 4 5; do
    gdown --fuzzy "https://drive.google.com/file/d/${FILE_ID}/view?usp=sharing" -O work/book.pdf && [ -s work/book.pdf ] && break
    sleep 15
  done
fi
[ -s work/book.pdf ] || { echo "NO PDF"; exit 1; }
ls work/pages/p-*.png >/dev/null 2>&1 || pdftoppm -r 300 -gray -png work/book.pdf work/pages/p
mapfile -t IMGS < <(ls work/pages/p-*.png | sort)
TOTAL=${#IMGS[@]}
echo "pages: $TOTAL"
[ "$TOTAL" -gt 0 ] || { echo "RENDER FAILED"; exit 1; }

surya_run() {
  # $1 = outdir, rest = images ; try known CLI shapes, log everything
  out="$1"; shift
  mkdir -p "$out"
  surya_ocr --output_dir "$out" "$@" >> work/v2_surya.log 2>&1 && return 0
  surya_ocr "$@" --output_dir "$out" >> work/v2_surya.log 2>&1 && return 0
  surya_ocr "$@" >> work/v2_surya.log 2>&1 && return 0
  return 1
}

echo "==== v2 [3/5] compare samples pages 1-6 ===="
for f in "${IMGS[@]:0:6}"; do
  b=$(basename "$f" .png)
  tesseract "$f" stdout -l ara --psm 3 2>/dev/null > "ocr_out/compare/${b}.tess.txt" || true
done
rm -rf work/surya_sample
surya_run work/surya_sample "${IMGS[@]:0:6}" || echo "surya sample CLI failed"
python3 ocr/surya_norm.py work/surya_sample ocr_out/surya_pages || true
for i in 1 2 3 4 5 6; do
  s=$(printf "ocr_out/surya_pages/p-%03d.txt" "$i")
  [ -f "$s" ] && cp "$s" "$(printf 'ocr_out/compare/p-%03d.surya.txt' "$i")"
done
push_checkpoint "ocr v2: compare samples ready (pages 1-6)"

echo "==== v2 [3b] optional Qari sample (pages 1,5; timeboxed) ===="
timeout 1500 python3 ocr/qari_pages.py work/pages/p-001.png work/pages/p-005.png ocr_out/compare || echo "qari skipped/failed (non-fatal)"
push_checkpoint "ocr v2: qari sample phase done"

echo "==== v2 [4/5] full surya (chunked, resumable) ===="
for ((i=0; i<TOTAL; i+=CH)); do
  need=0
  for f in "${IMGS[@]:i:CH}"; do
    b=$(basename "$f" .png)
    [ -s "ocr_out/surya_pages/${b}.txt" ] || need=1
  done
  if [ "$need" = 0 ]; then echo "chunk @$((i+1)) already done"; continue; fi
  echo "--- surya chunk starting page $((i+1))/$TOTAL ---"
  rm -rf work/surya_chunk; mkdir -p work/surya_chunk
  surya_run work/surya_chunk "${IMGS[@]:i:CH}" || echo "chunk @$i failed"
  python3 ocr/surya_norm.py work/surya_chunk ocr_out/surya_pages || true
  if (( (i/CH) % 3 == 2 )); then
    python3 ocr/surya_norm.py --assemble ocr_out/surya_pages ocr_out/book_surya.partial.txt || true
    push_checkpoint "ocr v2: surya progress past page $((i+CH))"
  fi
done

echo "==== v2 [5/5] final assemble ===="
python3 ocr/surya_norm.py --assemble ocr_out/surya_pages ocr_out/book_surya.txt || true
SHARDS=$(ls ocr_out/surya_pages/ 2>/dev/null | wc -l)
wc -c ocr_out/book_surya.txt 2>/dev/null || true
{
  echo "status: v2 done"
  echo "shards: ${SHARDS}/${TOTAL}"
  echo "date: $(date -u +%FT%TZ)"
} > ocr_out/DONE2.txt
push_checkpoint "ocr v2: full surya complete ${SHARDS}/${TOTAL}"
echo "V2 ALL DONE"
