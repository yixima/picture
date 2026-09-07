#!/bin/bash
# Upscale every TIFF in in2/ to out2/<stem>_up.jpg, sequentially, logging to batch2.log
cd "$(dirname "$0")" || exit 1
mkdir -p out2
: > batch2.log
for f in in2/*.tiff; do
  stem=$(basename "$f" .tiff)
  [ -s "out2/${stem}_up.jpg" ] && { echo "=== $stem skip (exists)" >> batch2.log; continue; }
  echo "=== $stem $(date +%H:%M:%S)" >> batch2.log
  python3 upscale.py "$f" "out2/${stem}_up.jpg" --min-width 2000 --max-width 4000 --dpi 300 >> batch2.log 2>&1 || echo "FAILED $stem" >> batch2.log
done
echo "=== ALL DONE $(date +%H:%M:%S)" >> batch2.log
