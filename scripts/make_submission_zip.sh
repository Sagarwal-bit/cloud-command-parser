#!/usr/bin/env bash
# Usage: scripts/make_submission_zip.sh ROLL_NUMBER path/to/ROLL_NUMBER.pdf   (the scanned handwritten reflection)
set -euo pipefail
ROLL="${1:?roll number}"; SCAN="${2:?scanned reflection pdf}"
[ "$(basename "$SCAN")" = "$ROLL.pdf" ] || { echo "scan must be named exactly $ROLL.pdf"; exit 1; }
[ -f report/report.pdf ] || { echo "report/report.pdf missing"; exit 1; }
grep -q "INSERT_" README.md && { echo "README.md still has INSERT_ placeholders"; exit 1; }
rm -rf "/tmp/$ROLL" "$ROLL.zip"; mkdir "/tmp/$ROLL"
git ls-files -z | xargs -0 -I{} cp --parents {} "/tmp/$ROLL/"
cp "$SCAN" "/tmp/$ROLL/$ROLL.pdf"
(cd /tmp && zip -qr "$OLDPWD/$ROLL.zip" "$ROLL")
unzip -l "$ROLL.zip" | tail -n 3
find "/tmp/$ROLL" \( -name '*.safetensors' -o -name '*.env' -o -name '*.tar.gz' \) | grep . && { echo "weights/secrets found!"; exit 1; } || true
echo "created $ROLL.zip"
