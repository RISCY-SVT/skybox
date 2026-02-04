#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$ROOT/build-xlen32-gfxmicro}"
OUTDIR="${OUTDIR:-$BUILD_DIR/artifacts/microtests}"
CONFIGS="${CONFIGS:--DEXT_GFX_ENABLE}"
DRIVER_FILTER="${DRIVER_FILTER:-both}"
OSVERSION="${OSVERSION:-ubuntu/focal}"
VERILATOR_BIN="${VERILATOR_BIN:-}"
if [[ -z "$VERILATOR_BIN" && -n "${VERILATOR_ROOT:-}" ]]; then
  VERILATOR_BIN="$VERILATOR_ROOT/bin"
fi
DO_BUILD=1

usage() {
  cat <<USAGE
Usage: $0 [--build-dir <path>] [--out-dir <path>] [--no-build] [--driver simx|rtlsim|both]
Env: BUILD_DIR, OUTDIR, CONFIGS, DRIVER_FILTER, OSVERSION, VERILATOR_BIN, VERILATOR_ROOT
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-dir) BUILD_DIR="$2"; shift 2;;
    --out-dir) OUTDIR="$2"; shift 2;;
    --no-build) DO_BUILD=0; shift;;
    --driver) DRIVER_FILTER="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
 done

mkdir -p "$OUTDIR/logs"

ensure_build() {
  if [[ ! -f "$BUILD_DIR/Makefile" ]]; then
    mkdir -p "$BUILD_DIR"
    (cd "$BUILD_DIR" && "${ROOT}/configure" --xlen=32 --osversion="$OSVERSION")
  fi
  if [[ $DO_BUILD -eq 1 ]]; then
    if [[ -n "$VERILATOR_BIN" ]]; then
      PATH="$VERILATOR_BIN:$PATH" CC=gcc CXX=g++ make -s -C "$BUILD_DIR"
    else
      CC=gcc CXX=g++ make -s -C "$BUILD_DIR"
    fi
  fi
}

run_case() {
  local name="$1" driver="$2" trace="$3" ref="$4" w="$5" h="$6" cores="$7" warps="$8" threads="$9" repeat="${10}"
  local trace_path="$ROOT/tests/regression/draw3d/$trace"
  local ref_path="$ROOT/tests/regression/draw3d/$ref"
  local ref_arg=""
  if [[ -n "$ref" && -f "$ref_path" ]]; then
    ref_arg="-r$ref_path"
  fi
  local hashes=()
  local status=0
  local perf=""
  local elapsed=""
  for i in $(seq 1 "$repeat"); do
    local out_png="$OUTDIR/${name}_${driver}_${w}x${h}_run${i}.png"
    local log="$OUTDIR/logs/${name}_${driver}_${w}x${h}_run${i}.log"
    local args="-t$trace_path $ref_arg -w$w -h$h -o$out_png"
    : >"$log"
    echo "==> $name ($driver) run $i: $args" | tee -a "$log" >&2
    echo "CMD: CONFIGS=\"$CONFIGS\" CC=gcc CXX=g++ $BUILD_DIR/ci/blackbox.sh --driver=$driver --app=draw3d --args=\"$args\" --cores=$cores --warps=$warps --threads=$threads" >>"$log"
    set +e
    if [[ -n "$VERILATOR_BIN" ]]; then
      PATH="$VERILATOR_BIN:$PATH" CONFIGS="$CONFIGS" CC=gcc CXX=g++ \
        "$BUILD_DIR/ci/blackbox.sh" --driver="$driver" --app=draw3d --args="$args" \
        --cores="$cores" --warps="$warps" --threads="$threads" >>"$log" 2>&1
    else
      CONFIGS="$CONFIGS" CC=gcc CXX=g++ \
        "$BUILD_DIR/ci/blackbox.sh" --driver="$driver" --app=draw3d --args="$args" \
        --cores="$cores" --warps="$warps" --threads="$threads" >>"$log" 2>&1
    fi
    status=$?
    set -e
    if [[ -f "$out_png" ]]; then
      hashes+=("$(sha256sum "$out_png" | awk '{print $1}')")
    else
      hashes+=("MISSING")
    fi
    # grab perf/elapsed from this run
    perf=$(grep -E "PERF: instrs=" "$log" | tail -n1 | sed 's/,/;/g' || true)
    elapsed=$(grep -E "Total elapsed time|Elapsed time" "$log" | tail -n1 | sed 's/,/;/g' || true)
  done

  local ref_hash="-"
  local match="-"
  if [[ -n "$ref" && -f "$ref_path" ]]; then
    ref_hash=$(sha256sum "$ref_path" | awk '{print $1}')
    if [[ "${hashes[0]}" == "$ref_hash" ]]; then
      match="yes"
    else
      match="no"
    fi
  fi

  local determinism="-"
  if [[ "$repeat" -gt 1 ]]; then
    if [[ "${hashes[0]}" == "${hashes[1]}" ]]; then
      determinism="yes"
    else
      determinism="no"
    fi
  fi

  printf "|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n" \
    "$name" "$driver" "$status" "${elapsed:-}" "${perf:-}" "${hashes[0]}" "$ref_hash" "$match" "$determinism"

  return $status
}

ensure_build

# cases: name driver trace ref w h cores warps threads repeat
CASES=(
  "tri8 simx triangle.cgltrace triangle_ref_8.png 8 8 2 1 2 2"
  "tri64 simx triangle.cgltrace triangle_ref_64.png 64 64 2 1 2 1"
  "vase32 simx vase.cgltrace vase_ref_32.png 32 32 2 1 2 1"
  "box128 simx box.cgltrace box_ref_128.png 128 128 2 1 2 1"
  "tri8 rtlsim triangle.cgltrace triangle_ref_8.png 8 8 1 1 2 1"
  "box128 rtlsim box.cgltrace box_ref_128.png 128 128 1 1 2 1"
)

RESULTS_MD="$OUTDIR/results.md"
RESULTS_CSV="$OUTDIR/results.csv"

{
  echo "|case|driver|exit|elapsed|perf|out_sha256|ref_sha256|match_ref|deterministic|"
  echo "|---|---|---|---|---|---|---|---|---|"
  for entry in "${CASES[@]}"; do
    set -- $entry
    name=$1; driver=$2
    if [[ "$DRIVER_FILTER" != "both" && "$driver" != "$DRIVER_FILTER" ]]; then
      continue
    fi
    run_case "$@"
  done
} | tee "$RESULTS_MD"

# CSV
{
  echo "case,driver,exit,elapsed,perf,out_sha256,ref_sha256,match_ref,deterministic"
  sed -n '3,$p' "$RESULTS_MD" | sed 's/^|//; s/|$//; s/|/,/g'
} > "$RESULTS_CSV"

echo "Results: $RESULTS_MD"
