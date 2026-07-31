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
pip install --quiet "surya-ocr<0.20" 2>&1 | tail -3
pip show surya-ocr 2>/dev/null | head -3 || true
( surya_ocr --help 2>&1 || true ) | tee ocr_out/logs/surya_help.txt | head -40

echo "==== v2 [2/5] ensure pdf + render ===="
if [ ! -s work/book.pdf ]; then
  DL_OK=0
  for attempt in 1 2 3; do
    gdown "${FILE_ID}" -O work/book.pdf && [ -s work/book.pdf ] && DL_OK=1 && break
    sleep 15
  done
  if [ "$DL_OK" = 0 ]; then
    for attempt in 1 2 3; do
      rm -f /tmp/ck.txt /tmp/pg.html
      curl -sL -c /tmp/ck.txt "https://drive.usercontent.google.com/download?id=${FILE_ID}&export=download" -o /tmp/pg.html || true
      uuid=$(sed -n 's/.*name="uuid" value="\([^"]*\)".*/\1/p' /tmp/pg.html | head -1)
      echo "uuid: '${uuid}'"
      if [ -n "$uuid" ]; then
        curl -L -b /tmp/ck.txt -o work/book.pdf \
          "https://drive.usercontent.google.com/download?id=${FILE_ID}&export=download&confirm=t&uuid=${uuid}" \
          && [ -s work/book.pdf ] && DL_OK=1 && break
      fi
      sleep 15
    done
  fi
fi
[ -s work/book.pdf ] && head -c 1024 work/book.pdf | grep -q "%PDF" || { echo "NO PDF"; exit 1; }
ls work/pages/p-*.png >/dev/null 2>&1 || pdftoppm -r 300 -gray -png work/book.pdf work/pages/p
mapfile -t IMGS < <(ls work/pages/p-*.png | sort)
TOTAL=${#IMGS[@]}
echo "pages: $TOTAL"
[ "$TOTAL" -gt 0 ] || { echo "RENDER FAILED"; exit 1; }

surya_run() {
  # $1 = outdir, rest = image paths; classic surya (<0.20) = pure torch pipeline
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
SAMPLE_JSON=$(find work/surya_sample -name "*.json" | head -1)
[ -n "$SAMPLE_JSON" ] && head -c 4000 "$SAMPLE_JSON" > ocr_out/compare/sample_raw.json.txt
python3 ocr/surya_norm.py work/surya_sample ocr_out/surya_pages || true
for i in 1 2 3 4 5 6; do
  s=$(printf "ocr_out/surya_pages/p-%03d.txt" "$i")
  [ -f "$s" ] && cp "$s" "$(printf 'ocr_out/compare/p-%03d.surya.txt' "$i")"
done
push_checkpoint "ocr v2: compare samples ready (pages 1-6)"

echo "==== v2 [3b] optional Qari sample (pages 1,5; timeboxed) ===="
if [ -f ocr/ENABLE_QARI ]; then
  pip install --quiet "transformers>=4.45" "accelerate" "qwen-vl-utils" 2>&1 | tail -1
  timeout 1500 python3 ocr/qari_pages.py work/pages/p-001.png work/pages/p-005.png ocr_out/compare || echo "qari skipped/failed (non-fatal)"
  push_checkpoint "ocr v2: qari sample phase done"
else
  echo "qari phase disabled (enable by adding ocr/ENABLE_QARI)"
fi

echo "==== v2 [4/5] full surya (chunked, resumable) ===="
for ((i=0; i<TOTAL; i+=CH)); do
  j=$((i+CH-1)); [ $j -gt $((TOTAL-1)) ] && j=$((TOTAL-1))
  need=0
  for ((k=i; k<=j; k++)); do
    [ -s "$(printf 'ocr_out/surya_pages/p-%03d.txt' $((k+1)))" ] || need=1
  done
  if [ "$need" = 0 ]; then echo "chunk pages $((i+1))-$((j+1)) already done"; continue; fi
  echo "--- surya chunk pages $((i+1))-$((j+1)) / $TOTAL ---"
  rm -rf work/surya_chunk; mkdir -p work/surya_chunk
  surya_run work/surya_chunk "${IMGS[@]:i:CH}" || echo "chunk at $((i+1)) failed"
  python3 ocr/surya_norm.py work/surya_chunk ocr_out/surya_pages || true
  if (( (i/CH) % 3 == 2 )); then
    python3 ocr/surya_norm.py --assemble ocr_out/surya_pages ocr_out/book_surya.partial.txt || true
    push_checkpoint "ocr v2: surya progress past page $((j+1))"
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
