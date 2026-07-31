#!/usr/bin/env bash
# OCR pipeline for كتاب.pdf from Google Drive
set -uo pipefail

FILE_ID="1k9Q7moUs8LBkMp4g6fTa5pxBXs7c4D72"
BRANCH="arena/019fb85f-game"
CHUNK=100

cd "$(git rev-parse --show-toplevel)"
mkdir -p work/pages work/txt ocr_out/samples

echo "==== [1/6] Download ===="
cd work
for attempt in 1 2 3; do
  gdown --fuzzy "https://drive.google.com/file/d/${FILE_ID}/view?usp=sharing" -O book.pdf && break
  echo "gdown attempt $attempt failed, retrying in 10s"; sleep 10
done
[ -s book.pdf ] || { echo "DOWNLOAD FAILED"; exit 1; }
ls -la book.pdf
cd ..

echo "==== [2/6] Info + embedded text check ===="
pdfinfo work/book.pdf | tee ocr_out/pdfinfo.txt
N=$(pdfinfo work/book.pdf | awk '/^Pages:/ {print $2}')
echo "Total pages: $N"
pdftotext work/book.pdf ocr_out/embedded_text.txt 2>/dev/null || true
EMB_CHARS=$(wc -c < ocr_out/embedded_text.txt 2>/dev/null || echo 0)
echo "Embedded text chars: $EMB_CHARS"

echo "==== [3/6] Sample renders + quick sample OCR ===="
pdftoppm -f 1 -l 3 -r 100 -jpeg -gray work/book.pdf ocr_out/samples/page || true
mkdir -p work/sample_hi
pdftoppm -f 1 -l 3 -r 300 -gray -png work/book.pdf work/sample_hi/s || true
for f in work/sample_hi/s-*.png; do
  b=$(basename "$f" .png)
  tesseract "$f" "ocr_out/samples/${b}" -l ara --psm 3 2>/dev/null || true
done
ls -la ocr_out/samples/ || true

git config user.name "arena-ocr-bot"
git config user.email "arena-ocr-bot@users.noreply.github.com"
git add ocr_out/ && git commit -m "ocr: start run (pages=${N}, embedded_chars=${EMB_CHARS})" >/dev/null 2>&1 || true
git push origin "HEAD:${BRANCH}" || true

if [ "$N" -le 0 ] 2>/dev/null; then echo "No pages found"; exit 1; fi

echo "==== [4/6] Render all pages (300dpi gray) ===="
pdftoppm -r 300 -gray -png work/book.pdf work/pages/p
mapfile -t IMGS < <(ls work/pages/p-*.png | sort)
TOTAL=${#IMGS[@]}
echo "Rendered: $TOTAL pages"

echo "==== [5/6] OCR (tesseract ara, tessdata_best) ===="
unset TESSDATA_PREFIX
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
  git add ocr_out/ && git commit -m "ocr: progress ${DONE}/${TOTAL}" >/dev/null 2>&1 || true
  git fetch origin "${BRANCH}" >/dev/null 2>&1 || true
  git rebase "origin/${BRANCH}" >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1 || true
  git push origin "HEAD:${BRANCH}" || true
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
git add ocr_out/
git commit -m "ocr: complete ${TOTAL}/${TOTAL}" >/dev/null 2>&1 || true
git push origin "HEAD:${BRANCH}" || true
echo "ALL DONE"
