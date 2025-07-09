#!/usr/bin/env bats

setup() {
  # Preserve original CI value for skip conditions
  export ORIGINAL_CI="${CI:-}"
  unset CODEX_ENV_PYTHON_VERSION CODEX_PROXY_CERT CI VIRTUAL_ENV
}

teardown() {
  unset CODEX_ENV_PYTHON_VERSION CODEX_PROXY_CERT CI VIRTUAL_ENV
}

@test "is_ci_or_virtual_env returns 1 when no env vars set" {
  source scripts/clinic-lib.sh
  trap - ERR
  set +e
  is_ci_or_virtual_env
  status=$?
  set -e
  [ "$status" -eq 1 ]
}

@test "is_ci_or_virtual_env succeeds with CODEX_ENV_PYTHON_VERSION" {
  export CODEX_ENV_PYTHON_VERSION=1
  source scripts/clinic-lib.sh
  trap - ERR
  set +e
  is_ci_or_virtual_env
  status=$?
  set -e
  [ "$status" -eq 0 ]
}

@test "is_ci_or_virtual_env succeeds with CODEX_PROXY_CERT" {
  export CODEX_PROXY_CERT=cert
  source scripts/clinic-lib.sh
  trap - ERR
  set +e
  is_ci_or_virtual_env
  status=$?
  set -e
  [ "$status" -eq 0 ]
}

@test "is_ci_or_virtual_env succeeds with CI=true" {
  export CI=true
  source scripts/clinic-lib.sh
  trap - ERR
  set +e
  is_ci_or_virtual_env
  status=$?
  set -e
  [ "$status" -eq 0 ]
}

@test "is_ci_or_virtual_env fails with CI=false" {
  export CI=false
  source scripts/clinic-lib.sh
  trap - ERR
  set +e
  is_ci_or_virtual_env
  status=$?
  set -e
  [ "$status" -eq 1 ]
}

@test "is_ci_or_virtual_env succeeds with VIRTUAL_ENV" {
  export VIRTUAL_ENV=/tmp/venv
  source scripts/clinic-lib.sh
  trap - ERR
  set +e
  is_ci_or_virtual_env
  status=$?
  set -e
  [ "$status" -eq 0 ]
}

# Verify set_ownership uses default UID/GID values
@test "set_ownership uses default CFG_UID/GID" {
  if [[ "${ORIGINAL_CI:-}" == "true" ]]; then
    skip "Skipping file ownership test in CI - running in container"
  fi
  CHOWN_LOG="$TMPDIR/chown_default"
  # Stub chown to capture its arguments instead of altering file ownership
  chown() { echo "$*" > "$CHOWN_LOG"; }
  export -f chown
  source scripts/setup-environment.sh
  set_ownership -R /tmp/testfile
  read -r args <"$CHOWN_LOG"
  [ "$args" = "1000:1000 -R /tmp/testfile" ]
}

# Verify set_ownership respects custom UID/GID overrides
@test "set_ownership uses custom CFG_UID/GID" {
  if [[ "${ORIGINAL_CI:-}" == "true" ]]; then
    skip "Skipping file ownership test in CI - running in container"
  fi
  CHOWN_LOG="$TMPDIR/chown_custom"
  # Stub chown again for this test case
  chown() { echo "$*" > "$CHOWN_LOG"; }
  export -f chown
  export CFG_UID=2000
  export CFG_GID=3000
  source scripts/setup-environment.sh
  set_ownership /opt/intelluxe/data
  read -r args <"$CHOWN_LOG"
  [ "$args" = "2000:3000 /opt/intelluxe/data" ]
}

@test "check_docker_socket uses DOCKER_SOCKET override" {
  if [[ "${ORIGINAL_CI:-}" == "true" ]]; then
    skip "Skipping Docker socket test in CI - no Docker socket access"
  fi
  export DOCKER_SOCKET="$TMPDIR/custom.sock"
  nc -lU "$DOCKER_SOCKET" &
  sock_pid=$!
  sleep 0.5
  chmod 777 "$DOCKER_SOCKET"
  source scripts/clinic-lib.sh
  set +e
  output=$(check_docker_socket 2>&1)
  status=$?
  set -e
  kill $sock_pid
  rm -f "$DOCKER_SOCKET"
  [ "$status" -eq 0 ]
  [[ "$output" == *"$DOCKER_SOCKET"* ]]
}

@test "DOCKER_SOCKET strips unix prefix" {
  tmpdir=$(mktemp -d)
  export DOCKER_SOCKET="unix://$tmpdir/prefixed.sock"
  source scripts/clinic-lib.sh
  [ "$DOCKER_SOCKET" = "$tmpdir/prefixed.sock" ]
  rm -rf "$tmpdir"
}

@test "LOG_DIR defaults using builtin CFG_ROOT when both unset" {
  # With neither variable defined, LOG_DIR should derive from the builtin
  # CFG_ROOT path. In CI, use a temp dir as the default.
  unset LOG_DIR CFG_ROOT
  if [[ "${ORIGINAL_CI:-}" == "true" ]]; then
    # In CI, we'll test with a temp directory as the default
    export INTELLUXE_DEFAULT_ROOT="$TMPDIR/intelluxe-test"
    mkdir -p "$INTELLUXE_DEFAULT_ROOT"
    source scripts/clinic-lib.sh
    [ "$LOG_DIR" = "$INTELLUXE_DEFAULT_ROOT/logs" ]
    [ "$CFG_ROOT" = "$INTELLUXE_DEFAULT_ROOT" ]
  else
    source scripts/clinic-lib.sh
    [ "$LOG_DIR" = "/opt/intelluxe/clinic-stack/logs" ]
    [ "$CFG_ROOT" = "/opt/intelluxe/clinic-stack" ]
  fi
}

@test "LOG_DIR defaults to custom CFG_ROOT when LOG_DIR unset" {
  # When only CFG_ROOT is provided, LOG_DIR should fall back to a logs
  # directory relative to that custom root.
  unset LOG_DIR
  tmpdir=$(mktemp -d)
  export CFG_ROOT="$tmpdir/custom-root"
  source scripts/clinic-lib.sh
  [ "$LOG_DIR" = "$CFG_ROOT/logs" ]
}

@test "LOG_DIR keeps value when CFG_ROOT unset" {
  # Explicit LOG_DIR should remain unchanged even if CFG_ROOT is missing,
  # while CFG_ROOT falls back to the builtin default.
  tmpdir=$(mktemp -d)
  export LOG_DIR="$tmpdir/mylogs"
  unset CFG_ROOT
  if [[ "${CI:-}" == "true" ]]; then
    # In CI, use a temp directory as the default
    export INTELLUXE_DEFAULT_ROOT="$tmpdir/intelluxe-default"
    mkdir -p "$INTELLUXE_DEFAULT_ROOT"
    source scripts/clinic-lib.sh
    [ "$LOG_DIR" = "$tmpdir/mylogs" ]
    [ "$CFG_ROOT" = "$INTELLUXE_DEFAULT_ROOT" ]
  else
    source scripts/clinic-lib.sh
    [ "$LOG_DIR" = "$tmpdir/mylogs" ]
    [ "$CFG_ROOT" = "/opt/intelluxe/clinic-stack" ]
  fi
}

@test "LOG_DIR keeps value when both variables set" {
  # If both LOG_DIR and CFG_ROOT are explicitly defined, LOG_DIR should not be
  # overridden by the value derived from CFG_ROOT.
  tmpdir=$(mktemp -d)
  export LOG_DIR="$tmpdir/explicit-log"
  export CFG_ROOT="$tmpdir/root"
  source scripts/clinic-lib.sh
  [ "$LOG_DIR" = "$tmpdir/explicit-log" ]
  [ "$CFG_ROOT" = "$tmpdir/root" ]
}
