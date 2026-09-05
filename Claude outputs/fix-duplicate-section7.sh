#!/usr/bin/env bash
# bash 3.2 compatible (macOS default) - no mapfile, no bash-4 builtins
set -eu
cd "/Users/galsamuchian/Documents/Claude"
F=DASHBOARD-EDITING-GUIDE.md
PAT='^## 7\. Log under the label that matches who you are'

N=$(grep -c "$PAT" "$F" || true)
echo "copies of section 7 found: $N"

if [ "$N" -le 1 ]; then
  echo "nothing to do."
  exit 0
fi

SECOND=$(grep -n "$PAT" "$F" | sed -n '2s/:.*//p')
echo "second copy starts at line $SECOND"

BAK="$F.bak-$(date +%Y%m%d-%H%M%S)"
cp "$F" "$BAK"
echo "backup: $BAK"

head -n $((SECOND - 1)) "$F" > "$F.tmp"
mv "$F.tmp" "$F"

echo "--- after ---"
echo "copies now: $(grep -c "$PAT" "$F" || true)"
echo "last 4 lines:"
tail -4 "$F"
