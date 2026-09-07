#!/bin/bash
# Upscale every JPEG in in/ to out/<stem>_up.jpg, sequentially, logging to batch.log
cd "$(dirname "$0")" || exit 1
mkdir -p out
: > batch.log
for f in in/*.jpg; do
  stem=$(basename "$f" .jpg)
  echo "=== $stem $(date +%H:%M:%S)" >> batch.log
  python3 upscale.py "$f" "out/${stem}_up.jpg" --min-width 2000 --max-width 4000 --dpi 300 >> batch.log 2>&1 || echo "FAILED $stem" >> batch.log
done
echo "=== ALL DONE $(date +%H:%M:%S)" >> batch.log
