#!/bin/bash
# Simple local server — run this script to host the site at http://localhost:8000
# Press Ctrl+C to stop.

PORT=${1:-8000}
echo "Serving at http://localhost:$PORT"
echo "Press Ctrl+C to stop."
python3 -m http.server "$PORT" --directory "$(dirname "$0")"
