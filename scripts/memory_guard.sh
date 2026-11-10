#!/usr/bin/env bash
# Fixed safety observer for both A/B arms. Run as a separate user service.
# Measures host memory, not CUDA allocator reserved/live bytes.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:?receipt path required}"
FLOOR_KIB=2097152
mkdir -p "$(dirname "$OUT")"
printf 'utc,node,MemFree_kib,MemAvailable_kib\n' >> "$OUT"
while true; do
  for node in head worker; do
    if [ "$node" = head ]; then
      values=$(awk '/^MemFree:/{f=$2} /^MemAvailable:/{print f, $2}' /proc/meminfo)
    else
      values=$(timeout 12 ssh -o BatchMode=yes -o ConnectTimeout=5 nvidia@192.168.177.11 \
        "awk '/^MemFree:/{f=\$2} /^MemAvailable:/{print f, \$2}' /proc/meminfo") || values="0 0"
    fi
    read -r free available <<< "$values"
    printf '%s,%s,%s,%s\n' "$(date -u +%FT%TZ)" "$node" "$free" "$available" >> "$OUT"
    if [ "$available" -lt "$FLOOR_KIB" ]; then
      printf '%s ABORT %s below 2 GiB available (%s KiB)\n' "$(date -u +%FT%TZ)" "$node" "$available" >> "$OUT.abort"
      systemctl --user stop vllm-b12x.service
      exit 1
    fi
  done
  sleep 3
done
