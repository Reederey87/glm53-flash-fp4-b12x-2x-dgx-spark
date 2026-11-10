#!/usr/bin/env bash
# Fixed safety observer for both A/B arms. Run as a separate user service.
# Measures host memory, not CUDA allocator reserved/live bytes.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:?receipt path required}"
FLOOR_KIB=2097152
TOKEN="${INVOCATION_ID:-manual-$$}"
trap 'exit 0' TERM INT
fail_closed() {
  rc=$?
  trap - EXIT
  if [ "$rc" -ne 0 ]; then
    printf '%s observer failure rc=%s\n' "$(date -u +%FT%TZ)" "$rc" >> "$OUT.abort" || true
    systemctl --user stop vllm-b12x.service || true
  fi
  exit "$rc"
}
trap fail_closed EXIT
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
    [[ "$free" =~ ^[0-9]+$ && "$available" =~ ^[0-9]+$ ]] || exit 1
    printf '%s,%s,%s,%s\n' "$(date -u +%FT%TZ)" "$node" "$free" "$available" >> "$OUT"
    if [ "$available" -lt "$FLOOR_KIB" ]; then
      printf '%s ABORT %s below 2 GiB available (%s KiB)\n' "$(date -u +%FT%TZ)" "$node" "$available" >> "$OUT.abort"
      systemctl --user stop vllm-b12x.service
      exit 1
    fi
  done
  printf '%s %s\n' "$TOKEN" "$(date +%s)" > "$OUT.ready.tmp"
  mv "$OUT.ready.tmp" "$OUT.ready"
  sleep 3
done
