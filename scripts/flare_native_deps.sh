#!/usr/bin/env bash
# Extract pinned Ubuntu build dependencies into the candidate's own directory.
# Does not install host packages or execute Debian maintainer scripts.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
KIT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -m)" == aarch64 && "$(id -un)" == nvidia ]]
[[ "$KIT" == "$ROOT" ]]
mkdir -p "$ROOT/debs" "$ROOT/deps" "$ROOT/local"
exec 9>"$ROOT/local/dependencies.lock"
flock -n 9
mapfile -t packages < "$ROOT/recipes/flare-native-packages.txt"
cd "$ROOT/debs"
apt-get download "${packages[@]}"
for package in "${packages[@]}"; do
    name="${package%%=*}"; version="${package#*=}"
    found=0
    for archive in "$name"_*.deb; do
        [[ -f "$archive" ]] || continue
        [[ "$(dpkg-deb -f "$archive" Version)" == "$version" ]] || continue
        [[ "$(dpkg-deb -f "$archive" Architecture)" == arm64 ]]
        dpkg-deb --extract "$archive" "$ROOT/deps"
        found=1
    done
    [[ "$found" == 1 ]] || { echo "Missing pinned package: $package" >&2; exit 1; }
done
sha256sum ./*.deb > "$ROOT/local/native-debs.sha256"
# Relocate only this candidate's pkg-config metadata, not system metadata.
find "$ROOT/deps/usr" -name '*.pc' -type f -exec sed -i "s|^prefix=/usr$|prefix=$ROOT/deps/usr|" {} +
source "$ROOT/scripts/flare_env.sh"
{
    printf 'Ninja: '; ninja --version
    printf 'Protobuf: '; protoc --version
    for name in openssl liburing libibverbs python-3.12; do
        printf '%s: ' "$name"; pkg-config --modversion "$name"
    done
} | tee "$ROOT/local/native-dependencies.txt"
