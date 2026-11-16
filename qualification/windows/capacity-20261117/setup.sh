#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
s=$r/qualification/capacity-window-files
w=$r/local/capacity-window-20261117T010000Z
prior=$r/local/mtp-replay-serial-window-20261117T050000Z
[[ -f "$prior/restoration-verified.txt" && -f "$prior/fallback-disarmed.txt" && -f "$prior/mtp-replay-gate-passed.txt" ]]
/home/nvidia/.local/bin/uv run --offline --no-project --python /usr/bin/python3 python - "$r/local/performance-abba-window-20261116T220000Z/comparison.json" <<'PY'
import json,sys
assert json.load(open(sys.argv[1]))['repeat_gate_passed'] is True
PY
[[ $(sha256sum "$r/scripts/flare_run.py" | cut -d ' ' -f1) == 41b65a5a4bc39af18de9310d4096752809c223bea7ca4994cf8c2aa6f97e8793 ]]
[[ $(systemctl --user show b12x-flare@0.service -p MainPID --value) == 0 ]]
systemctl --user is-active --quiet vllm-b12x.service
sha256sum --check "$s/staged-source.sha256"
ssh -n nvidia@192.168.177.11 "sha256sum --check $s/staged-source.sha256; test \$(systemctl --user show b12x-flare@1.service -p MainPID --value) = 0"
mkdir "$w"
cp -n "$r/.env" "$w/head-env-before.private"
cp -p "$r/scripts/flare_run.py" "$w/flare_run.py.before"
cp -p "$r/scripts/flare_candidate.py" "$w/flare_candidate.py.before"
sha256sum "$r/.env" "$r/scripts/flare_run.py" "$r/scripts/flare_candidate.py" "$r/local/accepted-core.json" > "$w/head-before.sha256"
docker inspect vllm_node --format '{{.Image}}' > "$w/head-image-before.txt"
ssh -n nvidia@192.168.177.11 "set -e; mkdir $w; cp -n $r/.env $w/worker-env-before.private; cp -p $r/scripts/flare_run.py $w/flare_run.py.before; cp -p $r/scripts/flare_candidate.py $w/flare_candidate.py.before; sha256sum $r/.env $r/scripts/flare_run.py $r/scripts/flare_candidate.py $r/local/accepted-core.json > $w/worker-before.sha256; docker inspect vllm_node --format '{{.Image}}' > $w/worker-image-before.txt"
cp "$s/run.sh" "$s/verify-native.py" "$s/runtime-source.sha256" "$s/head-source.sha256" "$w/"
ssh -n nvidia@192.168.177.11 "cp $s/verify-native.py $s/runtime-source.sha256 $w/"
cat > "$w/restore.sh" <<'RESTORE'
#!/bin/bash
set -euo pipefail
r=/home/nvidia/b12x-flare
w=$r/local/capacity-window-20261117T010000Z
for role in window memory; do
 systemctl --user stop "b12x-flare-capacity-$role-20261117T010000Z.service" || true
done
systemctl --user stop b12x-flare@0.service
ssh -n -o BatchMode=yes -o ConnectTimeout=10 nvidia@192.168.177.11 systemctl --user stop b12x-flare@1.service
cat >> "$r/.env" <<'ARM'

# --- capacity qualification closed; restore original wrapper and B12X ---
FLARE_SERVE_RESERVE_GIB=4
FLARE_NATIVE_ARM=upstream
FLARE_SCHEDULER_POLICY=balanced
FLARE_SCHEDULER_TRACE=off
ARM
ssh nvidia@192.168.177.11 'cat >> /home/nvidia/b12x-flare/.env' <<'ARM'

# --- capacity qualification closed; restore original wrapper and B12X ---
FLARE_SERVE_RESERVE_GIB=4
FLARE_NATIVE_ARM=upstream
FLARE_SCHEDULER_POLICY=balanced
FLARE_SCHEDULER_TRACE=off
ARM
for file in flare_run.py flare_candidate.py; do
 cp -p "$w/$file.before" "$r/scripts/$file.restore-tmp"
 mv "$r/scripts/$file.restore-tmp" "$r/scripts/$file"
done
ssh -n nvidia@192.168.177.11 "set -e; for file in flare_run.py flare_candidate.py; do cp -p $w/\$file.before $r/scripts/\$file.restore-tmp; mv $r/scripts/\$file.restore-tmp $r/scripts/\$file; done"
exec /bin/bash "$r/scripts/flare_restore.sh"
RESTORE
systemd-run --user --unit=b12x-flare-capacity-restore-20261117T010000Z --on-active=90m --property=Type=exec --property=RemainAfterExit=yes /bin/bash "$w/restore.sh"
trap 'systemctl --user start --no-block b12x-flare-capacity-restore-20261117T010000Z.service' ERR
# Both native units are stopped. Atomically install the same frozen wrapper in both arms.
for file in flare_candidate.py flare_run.py flare_production.py flare_capacity_stress.py; do
 cp -p "$s/$file" "$r/scripts/$file.capacity-tmp"
 mv "$r/scripts/$file.capacity-tmp" "$r/scripts/$file"
done
ssh -n nvidia@192.168.177.11 "set -e; for file in flare_candidate.py flare_run.py; do cp -p $s/\$file $r/scripts/\$file.capacity-tmp; mv $r/scripts/\$file.capacity-tmp $r/scripts/\$file; done"
