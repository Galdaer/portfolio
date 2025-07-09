#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  TMPBIN="$TMPDIR/bin"
  mkdir -p "$TMPBIN"
  PATH="$TMPBIN:$PATH"
  cat >"$TMPBIN/systemctl" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
  cat >"$TMPBIN/info" <<'EOS'
#!/usr/bin/env bash
# minimal stub to satisfy script
exit 0
EOS
  chmod +x "$TMPBIN/systemctl" "$TMPBIN/info"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "creates log directory under CFG_ROOT" {
  if [[ "${CI:-}" == "true" ]]; then
    skip "Skipping systemd log directory test in CI - may not have permission to create directories"
  fi
  export CFG_ROOT="$TMPDIR/root1"
  CI=false run bash scripts/systemd-summary.sh foo
  [ "$status" -eq 0 ]
  [ -d "$CFG_ROOT/logs" ]
  [ -f "$CFG_ROOT/logs/systemd-summary.log" ]
}

@test "overriding CFG_ROOT uses new log path" {
  if [[ "${CI:-}" == "true" ]]; then
    skip "Skipping systemd log directory test in CI - may not have permission to create directories"
  fi
  export CFG_ROOT="$TMPDIR/override"
  CI=false run bash scripts/systemd-summary.sh bar
  [ "$status" -eq 0 ]
  [ -d "$CFG_ROOT/logs" ]
  [ -f "$CFG_ROOT/logs/systemd-summary.log" ]
}
