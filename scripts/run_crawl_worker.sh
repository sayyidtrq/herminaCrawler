#!/bin/sh
set -eu

if [ "${SELENIUM_HEADLESS:-true}" = "true" ]; then
    exec python -m scripts.run_crawl_worker
fi

echo "[crawl-worker] Starting headed Chromium in a virtual display..."
# Keep this wrapper as PID 1. Debian's xvfb-run waits for SIGUSR1 from Xvfb,
# which can remain blocked when xvfb-run itself is the container init process.
xvfb-run \
    -a \
    -s "-screen 0 1440x1000x24 -nolisten tcp" \
    python -m scripts.run_crawl_worker
