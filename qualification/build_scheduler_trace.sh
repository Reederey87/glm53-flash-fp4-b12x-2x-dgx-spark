#!/usr/bin/env bash
# Build the native completion observer in an idle, isolated worker worktree.
set -euo pipefail
ROOT=/home/nvidia/b12x-flare
LAB=$1
KIT_COMMIT=$2
[[ "$(hostname)" == spark-7829 ]]
[[ "$LAB" == "$ROOT"/local/scheduler-trace-* && ! -e "$LAB" ]]
[[ "$KIT_COMMIT" =~ ^[0-9a-f]{40}$ ]]
[[ -z "$(docker ps -q)" ]]
awk '/MemFree:/ {f=$2} /MemAvailable:/ {a=$2} END {exit !(f>=94371840 && a>=104857600)}' /proc/meminfo
source "$ROOT/scripts/flare_env.sh"
export CUDA_VISIBLE_DEVICES=
git -C "$ROOT/upstream/flare" worktree add --detach "$LAB" 5a4e867954593b2e05bba43bc2a6eeaddca402d7
cd "$LAB"
sha256sum helios/Cargo.lock flare-cli/Cargo.lock > locks.before
git apply "$ROOT/qualification/flare-prefill-latency.patch"
git apply "$ROOT/qualification/flare-scheduler-trace.patch"
sha256sum -c locks.before
TEST_TARGET="$ROOT/local/scheduler-lab-20261116T005600Z/target"
cargo test --locked --offline --jobs 2 --manifest-path helios/Cargo.toml --target-dir "$TEST_TARGET" --features server --lib server::dashboard:: -- --test-threads=1
cargo test --locked --offline --jobs 2 --manifest-path helios/Cargo.toml --target-dir "$TEST_TARGET" --features server --lib server::metrics::scheduler:: -- --test-threads=1
cargo test --locked --offline --jobs 2 --manifest-path helios/Cargo.toml --target-dir "$TEST_TARGET" --features server --lib scheduler:: -- --test-threads=1
cargo test --locked --offline --jobs 2 --manifest-path helios/Cargo.toml --target-dir "$TEST_TARGET" --features server --lib server::config::tests:: -- --test-threads=1
cargo test --locked --offline --jobs 2 --manifest-path flare-cli/Cargo.toml --target-dir "$TEST_TARGET" --bin flare cli::tests::scheduling_preference_is_explicit_and_validated -- --test-threads=1
RELEASE_TARGET="$ROOT/local/scheduler-release-20261116T012000Z/target"
cargo build --release --locked --offline --jobs 2 --manifest-path flare-cli/Cargo.toml --target-dir "$RELEASE_TARGET"
sha256sum -c locks.before
"$RELEASE_TARGET/release/flare" --version
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 python - "$LAB" "$RELEASE_TARGET/release/flare" "$KIT_COMMIT" <<'PY'
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
lab,binary,commit=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
root=Path('/home/nvidia/b12x-flare')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'schema':1,'kind':'prefill-latency','flare_revision':'5a4e867954593b2e05bba43bc2a6eeaddca402d7',
          'patch_sha256':sha(root/'qualification/flare-prefill-latency.patch'),
          'trace_patch_sha256':sha(root/'qualification/flare-scheduler-trace.patch'),'trace_schema':1,
          'binary_sha256':sha(binary),'kit_commit':commit,
          'lock_sha256':{n:sha(lab/n) for n in ('helios/Cargo.lock','flare-cli/Cargo.lock')},
          'rustc':subprocess.check_output(['rustc','--version'],text=True).strip(),
          'qualification':'CPU tests and release build passed; native trace and GPU performance unqualified'}
data=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
arm=hashlib.sha256(data).hexdigest();dest=root/'native'/arm
dest.mkdir(parents=True,exist_ok=False)
shutil.copyfile(binary,dest/'flare.tmp');os.chmod(dest/'flare.tmp',0o755)
(dest/'manifest.json.tmp').write_bytes(data)
os.replace(dest/'flare.tmp',dest/'flare');os.replace(dest/'manifest.json.tmp',dest/'manifest.json')
(lab/'artifact.json').write_text(json.dumps({'arm':arm,'binary_sha256':manifest['binary_sha256']})+'\n')
print(json.dumps({'arm':arm,'binary_sha256':manifest['binary_sha256']}))
PY
