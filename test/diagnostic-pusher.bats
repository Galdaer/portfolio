#!/usr/bin/env bats

@test "INFLUX_MOCK branch sets 204 response" {
  tmpdir=$(mktemp -d)
  script="$tmpdir/mock.sh"
  cat >"$script" <<'EOS'
set -euo pipefail
INFLUX_MOCK=true
DEBUG=false
warn(){ :; }
fail(){ echo "fail:$*"; exit 1; }
trap 'echo exit=$? code=$http_response_code curl=$curl_exit' EXIT
EOS
  sed -n '187,217p' scripts/diagnostic-pusher.sh >> "$script"
  chmod +x "$script"
  run bash "$script"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "[CI] Skipping InfluxDB push (INFLUX_MOCK set)." ]
  [ "${lines[1]}" = "exit=0 code=204 curl=0" ]
  [ "${#lines[@]}" -eq 2 ]
  rm -rf "$tmpdir"
}

@test "exits when CFG_ROOT unset" {
  # Skip in CI if CFG_ROOT is already set in environment
  if [[ "${CI:-false}" == "true" && -n "${CFG_ROOT:-}" ]]; then
    skip "Skipping CFG_ROOT unset test in CI - CFG_ROOT is set in environment"
  fi
  
  tmpdir=$(mktemp -d)
  script="$tmpdir/guard.sh"
  cat >"$script" <<'EOS'
set -euo pipefail
source scripts/lib.sh
unset CFG_ROOT
EOS
  # Include the default variable settings and the CFG_ROOT check
  sed -n '37,39p' scripts/diagnostic-pusher.sh >> "$script"
  sed -n '86,95p' scripts/diagnostic-pusher.sh >> "$script"
  chmod +x "$script"
  run bash "$script"
  [ "$status" -ne 0 ]
  [[ "$output" == *"CFG_ROOT must be set"* ]]
  rm -rf "$tmpdir"
}

