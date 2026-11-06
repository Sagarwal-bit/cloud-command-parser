#!/usr/bin/env bash
# report/report.md -> report/report.pdf (pandoc -> docx -> LibreOffice).
set -euo pipefail
cd "$(dirname "$0")/../report"
pandoc report.md -o report.docx
soffice --headless --convert-to pdf report.docx >/dev/null 2>&1
rm -f report.docx
python3 - <<'PY'
import re
data = open("report.pdf", "rb").read()
print("pages:", len(re.findall(rb"/Type\s*/Page[^s]", data)))
PY
