#!/usr/bin/env bash
# Run city-exposure-study work on the rented box `blgpu` instead of the local 4 vCPU host.
#
# The remote tree mirrors the local one at the same absolute paths, so every
# hard coded /home/user/aegis/... path in this study resolves identically on
# both machines and a command is copy pasteable between them.
#
#   tools/blgpu.sh sync              push code, config, meshes and fused semantics
#   tools/blgpu.sh sync --all-meshes push the meshes the tracer refuses too
#   tools/blgpu.sh push PATH...      push a heavier input the default sync leaves behind
#   tools/blgpu.sh setup             build the python 3.12 venv and install both packages
#   tools/blgpu.sh doctor            print what the remote environment actually is
#   tools/blgpu.sh run "CMD"         start CMD detached, print the job id
#   tools/blgpu.sh run --sync "CMD"  sync first, then start it
#   tools/blgpu.sh status [JOB]      running, or exit code if finished
#   tools/blgpu.sh log [JOB]         tail the log
#   tools/blgpu.sh follow [JOB]      stream the log until the job ends
#   tools/blgpu.sh wait [JOB]        block until the job ends, exit with its code
#   tools/blgpu.sh fetch [JOB] [SUBPATH ...]   rsync results back, default outputs/
#   tools/blgpu.sh jobs              list jobs newest first
#   tools/blgpu.sh sh "CMD"          one off foreground command in the remote venv
#   tools/blgpu.sh verify [RAYS]     prove the tracer reproduces bit for bit
#
# Every job lives in its own directory on the box and records its own pid, log
# and exit code on disk. Nothing is held in the ssh session, so dropping the
# connection at any point is harmless: reconnect and ask again.
set -euo pipefail

HOST="${BLGPU_HOST:-blgpu}"
LOCAL_REPO="/home/user/aegis"
REMOTE_REPO="/home/user/aegis"
STUDY_REL="papers/city-exposure-study/semantic_twin"
LOCAL_STUDY="$LOCAL_REPO/$STUDY_REL"
REMOTE_STUDY="$REMOTE_REPO/$STUDY_REL"
JOBS_DIR="$REMOTE_REPO/.blgpu_jobs"
VENV="$REMOTE_REPO/.venv"

# ControlMaster keeps repeated calls cheap and lets a dropped TCP session be
# re opened without re authenticating. ServerAlive detects a dead peer instead
# of hanging forever.
SSH_CTL_DIR="${TMPDIR:-/tmp}/blgpu-ssh-$(id -u)"
mkdir -p "$SSH_CTL_DIR"
SSH_OPTS=(-o ControlMaster=auto -o "ControlPath=$SSH_CTL_DIR/%r@%h:%p" -o ControlPersist=120
          -o ServerAliveInterval=15 -o ServerAliveCountMax=8 -o ConnectTimeout=20)

rsh() { ssh "${SSH_OPTS[@]}" "$HOST" "$@"; }
die() { echo "blgpu: $*" >&2; exit 1; }

# Fresh images log in as `admin`, while the reproducible mirror deliberately
# lives below /home/user. Create only the exact directories this helper owns.
# In the common case no sudo is used. On a blank image sudo creates a directory
# and ownership is changed on that directory alone, never recursively and never
# on /home or /home/user.
ensure_remote_layout() {
  rsh bash -s -- "$REMOTE_REPO" "$REMOTE_STUDY" "$JOBS_DIR" <<'REMOTE'
set -euo pipefail
remote_uid="$(id -u)"
remote_gid="$(id -g)"

ensure_owned_dir() {
  dir="$1"
  if ! mkdir -p "$dir" 2>/dev/null; then
    command -v sudo >/dev/null 2>&1 || {
      echo "blgpu: cannot create $dir and passwordless sudo is unavailable" >&2
      exit 1
    }
    sudo -n mkdir -p "$dir"
  fi
  if [ ! -w "$dir" ]; then
    command -v sudo >/dev/null 2>&1 || {
      echo "blgpu: $dir is not writable and passwordless sudo is unavailable" >&2
      exit 1
    }
    sudo -n chown "$remote_uid:$remote_gid" "$dir"
  fi
  [ -d "$dir" ] && [ -w "$dir" ] || {
    echo "blgpu: failed to prepare writable directory $dir" >&2
    exit 1
  }
}

ensure_owned_dir "$1"
ensure_owned_dir "$2"
ensure_owned_dir "$3"
REMOTE
}

# About ten agents write into this tree at once, so a file disappearing between
# rsync's scan and its transfer is routine rather than a failure. That is exit
# 24, and only that one is forgiven.
rs() {
  local rc=0
  rsync -a -e "ssh ${SSH_OPTS[*]}" "$@" || rc=$?
  if (( rc == 24 )); then
    echo "blgpu: some source files vanished mid transfer, which is expected in a shared tree" >&2
    return 0
  fi
  return "$rc"
}

# --------------------------------------------------------------------------- sync

# Skipped on purpose. outputs/ is 1.8 GB of results this box is meant to
# produce, not consume. data/panoramas and data/tiles* are 3.6 GB of imagery
# that only the segmentation stage reads and that stage already ran. The .blend
# files and the top level renders are Blender scratch.
sync_excludes=(
  --exclude 'outputs/'
  --exclude 'data/panoramas/'
  --exclude 'data/tiles/'
  --exclude 'data/tiles250/'
  --exclude '*.blend'
  --exclude '*.blend1'
  --exclude '*.zip'
  --exclude '__pycache__/'
  --exclude '.pytest_cache/'
  --exclude '.ruff_cache/'
  --exclude '.hypothesis/'
  --exclude '.coverage'
  --exclude 'lit/'
  --exclude '*.pdf'
  --exclude '*.png'
  --exclude '.blgpu_jobs/'
)

cmd_sync() {
  local all_meshes=0
  [[ "${1:-}" == "--all-meshes" ]] && all_meshes=1

  ensure_remote_layout

  # 1. the AEGIS package itself plus the three data files its tissue and mesh
  #    code opens. The rest of aegis/data is 77 GB of unrelated study output.
  echo "blgpu: sync aegis package"
  rs --delete \
    --exclude '__pycache__/' --exclude '_version.py' \
    "$LOCAL_REPO/src/" "$HOST:$REMOTE_REPO/src/"
  rs \
    "$LOCAL_REPO/pyproject.toml" "$LOCAL_REPO/README.md" "$HOST:$REMOTE_REPO/"
  rs \
    "$LOCAL_REPO/data/duke.stl" "$LOCAL_REPO/data/itis_v5.db" "$LOCAL_REPO/data/phantoms.yaml" \
    "$HOST:$REMOTE_REPO/data/"
  # theory/scripts carries the shared matplotlib style the figure scripts import
  rs --exclude '__pycache__/' \
    "$LOCAL_REPO/theory/scripts/" "$HOST:$REMOTE_REPO/theory/scripts/"

  # 2. the study, code and config and tests, without the heavy artefacts
  echo "blgpu: sync study"
  rs "${sync_excludes[@]}" \
    --exclude 'data/geometry/' \
    "$LOCAL_STUDY/" "$HOST:$REMOTE_STUDY/"

  # 3. geometry, filtered by the rule run_exposure.site_mesh actually applies:
  #    a mesh is usable if its manifest declares format_version 3 or above.
  #    Filtering on the _f64 suffix instead looks equivalent and is not, because
  #    New York and Toulouse only ever got an unsuffixed build and that build is
  #    already double precision. Six older Korenmarkt and Milan crops, 34 MB,
  #    are the only PLYs the tracer would refuse, and they are the only ones
  #    left behind.
  echo "blgpu: sync geometry"
  if (( all_meshes )); then
    rs \
      "$LOCAL_STUDY/data/geometry/" "$HOST:$REMOTE_STUDY/data/geometry/"
  else
    local list; list="$(mktemp)"
    "$LOCAL_REPO/.venv/bin/python" - "$LOCAL_STUDY/data/geometry" > "$list" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
for path in sorted(root.rglob("*")):
    if path.is_dir():
        continue
    if path.suffix == ".ply":
        manifest = path.with_suffix(".json")
        if not manifest.exists():
            continue
        try:
            if int(json.loads(manifest.read_text()).get("format_version", 0)) < 3:
                continue
        except (ValueError, OSError):
            continue
    print(path.relative_to(root))
PY
    rs --files-from="$list" \
      "$LOCAL_STUDY/data/geometry/" "$HOST:$REMOTE_STUDY/data/geometry/"
    rm -f "$list"
  fi
  # 4. the fused panorama semantics. data/panoramas is 3.0 GB, but the part the
  #    propagation stage reads is the fused semantics.json plus
  #    panorama_semantics.npz per site, 309 MB. The per view label rasters and
  #    the source imagery stay behind because only the segmentation stage, which
  #    has already run, touches them.
  echo "blgpu: sync panorama semantics"
  rs \
    --include '*/' --include '*.json' --include '*.npz' --exclude '*' \
    "$LOCAL_STUDY/data/panoramas/" "$HOST:$REMOTE_STUDY/data/panoramas/"

  # 5. the few things under outputs/ that are inputs to the propagation stage
  #    rather than products of it. run_exposure.py reads walk_semantic.npz for
  #    --materials walk, and the site semantics and VLM tables for the material
  #    modes. All small. Anything heavier is pushed explicitly with `push`.
  echo "blgpu: sync propagation inputs"
  for sub in \
    walk_korenmarkt walk_korenmarkt_saturation city_screening \
    site_semantics material_vlm cross_validation antenna; do
    [[ -d "$LOCAL_STUDY/outputs/$sub" ]] || continue
    rs \
      --include '*/' --include '*.npz' --include '*.json' --include '*.jsonl' --include '*.csv' \
      --exclude '*' \
      "$LOCAL_STUDY/outputs/$sub" "$HOST:$REMOTE_STUDY/outputs/"
  done
  echo "blgpu: sync done"
}

# Push any local path under the study to the box, for the heavier inputs the
# default sync leaves behind, such as outputs/bystander_study.
cmd_push() {
  [[ $# -ge 1 ]] || die "push needs at least one path relative to the study directory"
  ensure_remote_layout
  for sub in "$@"; do
    sub="${sub%/}"
    echo "blgpu: push $sub"
    rsh "mkdir -p $(printf '%q' "$REMOTE_STUDY/$(dirname "$sub")")"
    rs --info=stats1 \
      "$LOCAL_STUDY/$sub" "$HOST:$REMOTE_STUDY/$(dirname "$sub")/"
  done
}

# --------------------------------------------------------------------------- setup

cmd_setup() {
  local ver
  ver="$("$LOCAL_REPO/.venv/bin/python" -c 'import aegis;print(aegis.__version__)' 2>/dev/null || echo 0.0.0)"
  ensure_remote_layout
  rsh AEGIS_VERSION="$ver" bash -s <<'REMOTE'
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
REPO=/home/user/aegis
VENV=$REPO/.venv

if ! command -v uv >/dev/null; then
  echo "blgpu: installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv python install 3.12 >/dev/null 2>&1 || true
if [ ! -x "$VENV/bin/python" ]; then
  uv venv --python 3.12 "$VENV"
fi
"$VENV/bin/python" -V

# Pinned to the exact versions the local reference environment carries. The
# tracer is a float64 numpy and mitsuba pipeline, so the numeric result is a
# function of these versions and a drifting minor would show up as a bit level
# difference rather than as an error.
uv pip install --python "$VENV/bin/python" \
  numpy==2.4.6 scipy==1.17.1 mpmath==1.3.0 PyYAML==6.0.3 \
  mitsuba==3.8.0 drjit==1.3.1 trimesh==4.12.2 embreex==4.4.0 \
  shapely==2.1.2 mapbox-earcut pillow==12.2.0 scikit-image==0.26.0 \
  matplotlib==3.10.9 pytest==9.0.3

# The repo is synced without .git, so hatch-vcs cannot derive a version. Pin it
# to whatever the local reference environment reports, which keeps
# aegis.__version__ identical on both machines.
export SETUPTOOLS_SCM_PRETEND_VERSION="${AEGIS_VERSION:-0.0.0}"
uv pip install --python "$VENV/bin/python" --no-deps -e "$REPO"
uv pip install --python "$VENV/bin/python" --no-deps -e "$REPO/papers/city-exposure-study/semantic_twin"
echo "blgpu: setup done"
REMOTE
}

cmd_doctor() {
  rsh bash -s <<'REMOTE'
set -uo pipefail
REPO=/home/user/aegis
echo "host      $(hostname)"
echo "load      $(cut -d' ' -f1-3 /proc/loadavg)"
echo "cores     $(nproc)"
echo "mem       $(free -g | awk '/^Mem:/{print $2" GiB total, "$7" GiB available"}')"
nvidia-smi --query-gpu=name,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null | sed 's/^/gpu       /'
echo "disk      $(df -h / | awk 'NR==2{print $4" free"}')"
cd "$REPO/papers/city-exposure-study/semantic_twin"
export PYTHONPATH="$REPO/papers/city-exposure-study/semantic_twin"
"$REPO/.venv/bin/python" - <<'PY'
import sys
print("python    " + sys.version.split()[0] + "  " + sys.executable)
for name in ("numpy", "scipy", "mitsuba", "drjit", "trimesh", "shapely", "matplotlib"):
    try:
        m = __import__(name)
        print(f"{name:<10}{getattr(m, '__version__', '?')}")
    except Exception as exc:  # noqa: BLE001
        print(f"{name:<10}MISSING ({exc})")
import aegis, semantic_twin
print("aegis     " + aegis.__file__)
print("study     " + str(list(semantic_twin.__path__)))
from semantic_twin.propagation import SbrTracer  # noqa: F401
print("tracer    import ok")
PY
REMOTE
}

# --------------------------------------------------------------------------- jobs

# Second resolution alone collides when two jobs are launched back to back, and
# a collision silently overwrites the first job's records, so a short random
# suffix is appended. Sorting is still chronological.
new_job_id() { printf '%s-%04x\n' "$(date -u +%Y%m%dT%H%M%S)" $((RANDOM % 65536)); }

cmd_run() {
  # A stale remote tree does not look stale. It looks like the box disagreeing
  # with the local machine, which is the one thing this setup exists to rule
  # out, so `run --sync` is the cheap way to never have to wonder.
  if [[ "${1:-}" == "--sync" ]]; then shift; cmd_sync >&2; fi
  [[ $# -ge 1 ]] || die "run needs a command"
  local user_cmd="$1"
  local job="${2:-$(new_job_id)}"
  local jd="$JOBS_DIR/$job"

  # ssh flattens its argument list into one string and the remote shell splits
  # it again, so anything with spaces or quotes has to travel base64 encoded.
  local b64
  b64="$(printf '%s' "$user_cmd" | base64 -w0)"

  # setsid detaches the process group from the ssh session, so the job survives
  # the connection dropping, the client being killed, and the agent going away.
  rsh "JOB_DIR=$(printf '%q' "$jd") CMD_B64=$b64 bash -s" <<'REMOTE'
set -euo pipefail
jd="$JOB_DIR"
mkdir -p "$jd"
printf '%s' "$CMD_B64" | base64 -d > "$jd/cmd"
printf '\n' >> "$jd/cmd"
cat > "$jd/wrapper.sh" <<'WRAP'
#!/usr/bin/env bash
# Plain bash -c, never bash -lc: the login profile prepends ~/.local/bin and
# would shadow the venv interpreter.
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
export PATH=/home/user/aegis/.venv/bin:$PATH
export VIRTUAL_ENV=/home/user/aegis/.venv
export PYTHONUNBUFFERED=1
# /home/admin/semantic_twin is an unrelated 2 GB output directory from earlier
# work on this box and it shadows the study package whenever cwd is the home
# directory. Pinning PYTHONPATH makes the import independent of cwd.
export PYTHONPATH=/home/user/aegis/papers/city-exposure-study/semantic_twin
jd="$(dirname "$0")"
date -u +'started %Y-%m-%dT%H:%M:%SZ' >> "$jd/log"
bash -c "$(cat "$jd/cmd")" >> "$jd/log" 2>&1
rc=$?
echo $rc > "$jd/rc"
date -u +"finished %Y-%m-%dT%H:%M:%SZ rc=$rc" >> "$jd/log"
exit $rc
WRAP
chmod +x "$jd/wrapper.sh"
rm -f "$jd/rc"
setsid nohup "$jd/wrapper.sh" >/dev/null 2>&1 &
echo $! > "$jd/pid"
REMOTE
  echo "$job"
}

latest_job() { rsh "ls -1 '$JOBS_DIR' 2>/dev/null | sort | tail -1"; }
resolve_job() { if [[ -n "${1:-}" ]]; then echo "$1"; else latest_job; fi; }

cmd_status() {
  local job; job="$(resolve_job "${1:-}")"
  [[ -n "$job" ]] || die "no jobs"
  rsh bash -s -- "$JOBS_DIR/$job" <<'REMOTE'
jd="$1"
[ -d "$jd" ] || { echo "no such job"; exit 1; }
if [ -f "$jd/rc" ]; then
  echo "finished rc=$(cat "$jd/rc")"
elif kill -0 "$(cat "$jd/pid" 2>/dev/null)" 2>/dev/null; then
  echo "running pid=$(cat "$jd/pid")"
else
  echo "died without writing rc"
fi
echo "cmd: $(cat "$jd/cmd")"
REMOTE
}

cmd_jobs() {
  rsh bash -s -- "$JOBS_DIR" <<'REMOTE'
jd="$1"
for d in $(ls -1 "$jd" 2>/dev/null | sort -r); do
  if [ -f "$jd/$d/rc" ]; then s="rc=$(cat "$jd/$d/rc")"; else s="running"; fi
  printf '%-22s %-10s %s\n' "$d" "$s" "$(head -c 90 "$jd/$d/cmd")"
done
REMOTE
}

cmd_log() {
  local job; job="$(resolve_job "${1:-}")"
  rsh "tail -n ${BLGPU_TAIL:-80} '$JOBS_DIR/$job/log'"
}

cmd_follow() {
  local job; job="$(resolve_job "${1:-}")"
  # --pid is not usable across ssh, so stop when the rc file appears
  rsh "tail -n 40 -f '$JOBS_DIR/$job/log' & tp=\$!; while [ ! -f '$JOBS_DIR/$job/rc' ]; do sleep 3; done; sleep 2; kill \$tp"
}

cmd_wait() {
  local job; job="$(resolve_job "${1:-}")"
  local rc
  while true; do
    # A dropped connection must not be read as a finished job, so a failed
    # probe just sleeps and retries.
    if rc="$(rsh "cat '$JOBS_DIR/$job/rc' 2>/dev/null" 2>/dev/null)" && [[ -n "$rc" ]]; then
      echo "job $job finished rc=$rc"
      return "$rc"
    fi
    sleep 10
  done
}

cmd_fetch() {
  # A leading argument is a job id only if it looks like one. Matching on "no
  # slash" instead would swallow a bare subpath such as `outputs`.
  local job=""
  if [[ "${1:-}" =~ ^[0-9]{8}T[0-9]{6}(-[0-9a-f]{4})?$ ]]; then job="$1"; shift; fi
  local subs=("$@")
  [[ ${#subs[@]} -gt 0 ]] || subs=("outputs/")
  for sub in "${subs[@]}"; do
    # A trailing slash on the source would drop the directory's contents one
    # level too high, so it is stripped before the parent is worked out.
    sub="${sub%/}"
    local parent; parent="$(dirname "$sub")"
    echo "blgpu: fetch $sub"
    mkdir -p "$LOCAL_STUDY/$parent"
    # No --delete. The local outputs/ tree is shared with other work and the
    # box only ever holds the subset it produced.
    rs --info=stats1 \
      "$HOST:$REMOTE_STUDY/$sub" "$LOCAL_STUDY/$parent/"
  done
  if [[ -n "$job" ]]; then
    rsync -a -e "ssh ${SSH_OPTS[*]}" "$HOST:$JOBS_DIR/$job/log" "$LOCAL_STUDY/outputs/blgpu_$job.log" 2>/dev/null || true
    echo "blgpu: log at outputs/blgpu_$job.log"
  fi
}

# --------------------------------------------------------------------------- verify

cmd_verify() {
  local rays="${1:-200000}"
  # Not local: the EXIT trap fires after the function's scope is already gone.
  tmp="$(mktemp -d)"
  trap 'test -n "${tmp:-}" && rm -r -f "${tmp}"' EXIT
  echo "blgpu: tracer fingerprint at $rays rays, local"
  "$LOCAL_REPO/.venv/bin/python" "$LOCAL_STUDY/tools/blgpu_reference.py" --rays "$rays" > "$tmp/local.txt"
  echo "blgpu: tracer fingerprint at $rays rays, remote"
  cmd_sh "python tools/blgpu_reference.py --rays $rays" > "$tmp/remote.txt"
  echo "blgpu: tracer fingerprint at $rays rays, remote pinned to one core"
  cmd_sh "taskset -c 0 python tools/blgpu_reference.py --rays $rays" > "$tmp/remote1.txt"
  # The host name is the only line that is allowed to differ.
  local fail=0
  for other in remote remote1; do
    if diff <(grep -v '^# host' "$tmp/local.txt") <(grep -v '^# host' "$tmp/$other.txt") > "$tmp/$other.diff"; then
      echo "  $other: bit identical ($(grep -c . "$tmp/local.txt") lines of hex float64 and sha256)"
    else
      echo "  $other: DIFFERS"
      cat "$tmp/$other.diff"
      fail=1
    fi
  done
  return "$fail"
}

cmd_sh() {
  [[ $# -ge 1 ]] || die "sh needs a command"
  local b64
  b64="$(printf '%s' "$1" | base64 -w0)"
  rsh "CMD_B64=$b64 bash -s" <<'REMOTE'
set -euo pipefail
REPO=/home/user/aegis
STUDY=$REPO/papers/city-exposure-study/semantic_twin
VENV=$REPO/.venv
cd "$STUDY"
export PATH="$VENV/bin:$PATH"
export VIRTUAL_ENV="$VENV"
export PYTHONUNBUFFERED=1
export PYTHONNOUSERSITE=1
export PYTHONPATH="$STUDY"
# Use a plain non-login shell. A login shell may prepend ~/.local/bin after the
# venv and silently select the image's Python instead.
bash -c "$(printf '%s' "$CMD_B64" | base64 -d)"
REMOTE
}

# --------------------------------------------------------------------------- main

sub="${1:-help}"; shift || true
case "$sub" in
  sync)   cmd_sync "$@" ;;
  push)   cmd_push "$@" ;;
  setup)  cmd_setup ;;
  doctor) cmd_doctor ;;
  run)    cmd_run "$@" ;;
  status) cmd_status "$@" ;;
  jobs)   cmd_jobs ;;
  log)    cmd_log "$@" ;;
  follow) cmd_follow "$@" ;;
  wait)   cmd_wait "$@" ;;
  fetch)  cmd_fetch "$@" ;;
  verify) cmd_verify "$@" ;;
  sh)     cmd_sh "$@" ;;
  *)      sed -n '2,30p' "$0" | sed 's/^# \?//' ;;
esac
