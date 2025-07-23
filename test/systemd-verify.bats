#!/usr/bin/env bats

extract_vars() {
  awk '
    /SCRIPT_VERSION=/ {flag=1}
    flag && /source .*lib.sh/ {exit}
    flag {print}
  ' scripts/systemd-verify.sh
}

setup() {
  snippet=$(extract_vars)
}

@test "LOG_DIR uses built-in CFG_ROOT" {
  if [[ "${CI:-}" == "true" ]]; then
    skip "Skipping systemd log directory test in CI - may not have permission to create directories"
  fi
  unset LOG_DIR CFG_ROOT
  eval "$snippet"
  [ "$LOG_DIR" = "/opt/intelluxe/stack/logs" ]
}

@test "LOG_DIR honors custom CFG_ROOT" {
  if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
    skip "Skipping systemd log directory test in CI - may not have permission to create directories"
  fi
  unset LOG_DIR
  export CFG_ROOT="/tmp/custom-root"
  eval "$snippet"
  [ "$LOG_DIR" = "$CFG_ROOT/logs" ]
}

@test "invokes systemd-analyze when present" {
  if [[ "${CI:-}" == "true" ]]; then
    skip "Skipping systemd-analyze test in CI - systemd may not be available"
  fi
  TMPDIR=$(mktemp -d)
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/systemd-analyze" <<EOS
#!/usr/bin/env bash
echo "\$@" >"$TMPDIR/call"
EOS
  chmod +x "$TMPDIR/bin/systemd-analyze"
  # Mock ls to return no installed units so it checks source units instead
  cat >"$TMPDIR/bin/ls" <<'EOS'
#!/usr/bin/env bash
if [[ "$*" == *"intelluxe-"* ]]; then
  exit 1  # No installed units found
else
  /bin/ls "$@"
fi
EOS
  chmod +x "$TMPDIR/bin/ls"
  CI=false CFG_ROOT="$TMPDIR" PATH="$TMPDIR/bin:$PATH" run bash scripts/systemd-verify.sh --no-color
  [ -f "$TMPDIR/call" ]
  grep -q verify "$TMPDIR/call"
  rm -rf "$TMPDIR"
}

@test "exports JSON with --export-json" {
  if [[ "${CI:-}" == "true" ]]; then
    skip "Skipping systemd JSON export test in CI - systemd may not be available"
  fi
  TMPDIR=$(mktemp -d)
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/systemd-analyze" <<'EOS'
#!/usr/bin/env bash
# no-op verify stub
exit 0
EOS
  chmod +x "$TMPDIR/bin/systemd-analyze"
  # Mock ls to return no installed units so it checks source units instead
  cat >"$TMPDIR/bin/ls" <<'EOS'
#!/usr/bin/env bash
if [[ "$*" == *"intelluxe-"* ]]; then
  exit 1  # No installed units found
else
  /bin/ls "$@"
fi
EOS
  chmod +x "$TMPDIR/bin/ls"
  JSON_FILE="/tmp/systemd-verify.json"
  rm -f "$JSON_FILE"
  CI=false CFG_ROOT="$TMPDIR" PATH="$TMPDIR/bin:$PATH" run bash scripts/systemd-verify.sh --export-json
  [ -f "$JSON_FILE" ]
  grep -q '"timestamp"' "$JSON_FILE"
  jq empty "$JSON_FILE" >/dev/null
  rm -rf "$TMPDIR" "$JSON_FILE"
}
