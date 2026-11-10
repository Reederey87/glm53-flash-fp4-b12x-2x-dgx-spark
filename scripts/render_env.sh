#!/usr/bin/env bash
# Derive upstream's unique-key config without rewriting the deployment ledger.
set -euo pipefail
input="${1:?source ledger required}"
output="${2:?derived config required}"
umask 077
mkdir -p "$(dirname "$output")"
temporary=$(mktemp "$output.tmp.XXXXXX")
trap 'rm -f "$temporary"' EXIT
awk '
  { lines[NR]=$0 }
  /^[[:space:]]*($|#)/ { next }
  {
    key=$0
    sub(/=.*/, "", key)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
    if (index($0, "=")==0 || key !~ /^[A-Za-z_][A-Za-z0-9_]*$/) {
      bad=1; exit 2
    }
    keys[NR]=key; last[key]=NR
  }
  END {
    if (!bad) for (i=1; i<=NR; i++)
      if (!(i in keys) || last[keys[i]]==i) print lines[i]
  }
' "$input" > "$temporary"
mv "$temporary" "$output"
