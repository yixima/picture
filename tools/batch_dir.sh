#!/bin/bash
# usage: batch_dir.sh IN_DIR OUT_DIR LOG  — upscale every image in IN_DIR to OUT_DIR/<stem>_up.jpg
cd "$(dirname "$0")" || exit 1
IN=$1; OUT=$2; LOG=$3
mkdir -p "$OUT"
: > "$LOG"
for f in "$IN"/*; do
  stem=$(basename "$f"); stem=${stem%.*}
  [ -s "$OUT/${stem}_up.jpg" ] && { echo "=== $stem skip (exists)" >> "$LOG"; continue; }
  echo "=== $stem $(date +%H:%M:%S)" >> "$LOG"
  python3 upscale.py "$f" "$OUT/${stem}_up.jpg" --min-width 2000 --max-width 4000 --dpi 300 >> "$LOG" 2>&1 || echo "FAILED $stem" >> "$LOG"
done
echo "=== ALL DONE $(date +%H:%M:%S)" >> "$LOG"
