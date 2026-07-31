#!/bin/sh
set -eu

if [ "${SELENIUM_HEADLESS:-true}" = "true" ]; then
    exec python -m scripts.run_crawl_worker
fi

echo "[crawl-worker] Starting headed Chromium in a virtual display..."
exec xvfb-run \
    -a \
    -s "-screen 0 1440x1000x24 -nolisten tcp" \
    python -m scripts.run_crawl_worker
