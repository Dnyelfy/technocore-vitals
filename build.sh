#!/usr/bin/env bash
# public/index.html'i src/ icinden uretir. Calisma aninda hicbir kutuphane cekilmiyor.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p public
cat src/page-head.html src/page-app.html > public/index.html
echo "wrote public/index.html ($(wc -c < public/index.html) bytes)"
