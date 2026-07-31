#!/usr/bin/env bash
# OCR pipeline for كتاب.pdf from Google Drive
set -uo pipefail

FILE_ID="1k9Q7moUs8LBkMp4g6fTa5pxBXs7c4D72"
BRANCH="arena/019fb85f-game"
CHUNK=100

cd "$(git rev-parse --show-toplevel)"
if [ -s ocr_out/book.txt ] && [ -s ocr_out/DONE.txt ]; then
  echo "[v1] already complete, skipping"
  exit 0
fi
mkdir -p work/pages work/txt ocr_out/samples ocr_out/logs

git config user.name "arena-ocr-bot"
git config user.email "arena-ocr-bot@users.noreply.github.com"

exec > >(tee work/pipeline.log) 2>&1

on_exit() {
  code=$?
  echo "[exit handler] exit code = $code"
  cp work/pipeline.log ocr_out/logs/ 2>/dev/null || true
  git add ocr_out/ 2>/dev/null
  git commit -m "ocr: run ended (exit=$code)" >/dev/null 2>&1 || true
  git push origin "HEAD:${BRANCH}" >/dev/null 2>&1 || true
}
trap on_exit EXIT

push_checkpoint() {
  msg="$1"
  git add ocr_out/ && git commit -m "$msg" >/dev/null 2>&1 || true
  git fetch origin "${BRANCH}" >/dev/null 2>&1 || true
  git rebase "origin/${BRANCH}" >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1 || true
  git push origin "HEAD:${BRANCH}" || true
}

echo "==== [1/6] Download ===="
DL_OK=0
for attempt in 1 2 3 4 5; do
  echo "--- gdown attempt $attempt ---"
  gdown "${FILE_ID}" -O work/book.pdf && [ -s work/book.pdf ] && DL_OK=1 && break
  sleep 15
done
if [ "$DL_OK" = 0 ]; then
  echo "--- curl uuid fallback ---"
  for attempt in 1 2 3; do
    rm -f /tmp/ck.txt /tmp/pg.html
    curl -sL -c /tmp/ck.txt "https://drive.usercontent.google.com/download?id=${FILE_ID}&export=download" -o /tmp/pg.html || true
    uuid=$(sed -n 's/.*name="uuid" value="\([^"]*\)".*/\1/p' /tmp/pg.html | head -1)
    echo "uuid found: '${uuid}'"
    if [ -n "$uuid" ]; then
      curl -L -b /tmp/ck.txt -o work/book.pdf \
        "https://drive.usercontent.google.com/download?id=${FILE_ID}&export=download&confirm=t&uuid=${uuid}" \
        && [ -s work/book.pdf ] && DL_OK=1 && break
    fi
    sleep 15
  done
fi
echo "DL_OK=$DL_OK"
ls -la work/book.pdf 2>/dev/null || true
head -c 1024 work/book.pdf 2>/dev/null | grep -q "%PDF" && echo "PDF header OK" || echo "WARNING: no PDF header!"
[ "$DL_OK" = 1 ] && [ -s work/book.pdf ] || { echo "DOWNLOAD FAILED"; exit 1; }

echo "==== [2/6] Info + embedded text check ===="
pdfinfo work/book.pdf | tee ocr_out/pdfinfo.txt
N=$(pdfinfo work/book.pdf | awk '/^Pages:/ {print $2}')
echo "Total pages: $N"
pdftotext work/book.pdf ocr_out/embedded_text.txt 2>/dev/null || true
EMB_CHARS=$(wc -c < ocr_out/embedded_text.txt 2>/dev/null || echo 0)
echo "Embedded text chars: $EMB_CHARS"

push_checkpoint "ocr: downloaded (pages=${N}, embedded_chars=${EMB_CHARS})"

if [ -z "$N" ] || [ "$N" -le 0 ] 2>/dev/null; then echo "No pages found"; exit 1; fi

echo "==== [3/6] Sample renders + quick sample OCR ===="
pdftoppm -f 1 -l 3 -r 100 -jpeg -gray work/book.pdf ocr_out/samples/page || true
mkdir -p work/sample_hi
pdftoppm -f 1 -l 3 -r 300 -gray -png work/book.pdf work/sample_hi/s || true
for f in work/sample_hi/s-*.png; do
  b=$(basename "$f" .png)
  tesseract "$f" "ocr_out/samples/${b}" -l ara --psm 3 2>/dev/null || true
done
ls -la ocr_out/samples/ || true
push_checkpoint "ocr: samples ready"

echo "==== [4/6] Render all pages (300dpi gray) ===="
pdftoppm -r 300 -gray -png work/book.pdf work/pages/p
mapfile -t IMGS < <(ls work/pages/p-*.png | sort)
TOTAL=${#IMGS[@]}
echo "Rendered: $TOTAL pages"
[ "$TOTAL" -gt 0 ] || { echo "RENDER FAILED"; exit 1; }
push_checkpoint "ocr: rendered ${TOTAL} pages"

echo "==== [5/6] OCR (tesseract ara, tessdata_best) ===="
ocr_one() {
  f="$1"
  b=$(basename "$f" .png)
  tesseract "$f" stdout -l ara --psm 3 2>/dev/null > "work/txt/${b}.txt" || true
}
export -f ocr_one

assemble() {
  OUT="$1"
  : > "$OUT"
  for t in $(ls work/txt/p-*.txt | sort); do
    b=$(basename "$t" .txt)
    num=$(echo "$b" | sed 's/^p-0*//')
    printf '\n\n===== [صفحة %s] =====\n\n' "$num" >> "$OUT"
    cat "$t" >> "$OUT"
  done
}

for ((i=0; i<TOTAL; i+=CHUNK)); do
  echo "--- chunk starting at page $((i+1)) / $TOTAL ---"
  printf '%s\0' "${IMGS[@]:i:CHUNK}" | xargs -0 -P 4 -I{} bash -c 'ocr_one "$@"' _ {}
  DONE=$(ls work/txt/ 2>/dev/null | wc -l)
  echo "OCR done for $DONE/$TOTAL pages"
  assemble ocr_out/book.partial.txt
  push_checkpoint "ocr: progress ${DONE}/${TOTAL}"
done

echo "==== [6/6] Final assemble ===="
assemble ocr_out/book.txt
cp ocr_out/book.txt ocr_out/كتاب.txt 2>/dev/null || true
wc -c ocr_out/book.txt
{
  echo "status: done"
  echo "pages: ${TOTAL}"
  echo "date: $(date -u +%FT%TZ)"
} > ocr_out/DONE.txt
wc -c ocr_out/book.txt
echo "ALL DONE"
