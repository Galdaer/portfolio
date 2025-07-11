#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "CI validate target skips Docker checks when Docker unavailable" {
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/docker" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
  chmod +x "$TMPDIR/bin/docker"
  PATH="$TMPDIR/bin:$PATH" CI=true run make validate
  [ "$status" -eq 0 ]
  [[ "$output" == *"Skipping Docker validation in CI: Docker not available"* ]]
}

@test "--skip-docker-check flag bypasses Docker checks" {
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/docker" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
  chmod +x "$TMPDIR/bin/docker"
  PATH="$TMPDIR/bin:$PATH" run ./scripts/bootstrap.sh --version --skip-docker-check
  [ "$status" -eq 0 ]
  [[ "$output" == *"Version:"* ]]
}

## When running --validate, the script proceeds into the main logic even if
# --skip-docker-check was provided. The main function performs an additional
# docker info check and exits with status 110 if Docker isn't running. The
# --version command exits early inside parse_basic_flags, so it succeeds
# without requiring Docker.
@test "--skip-docker-check works for validate command" {
  if [[ "${CI:-}" == "true" ]]; then
    skip "Skipping Docker validation test in CI - Docker may not be available"
  fi
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/docker" <<'STUB'
#!/usr/bin/env bash
exit 1
STUB
  chmod +x "$TMPDIR/bin/docker"
  PATH="$TMPDIR/bin:$PATH" run ./scripts/bootstrap.sh --validate --skip-docker-check
  [ "$status" -eq 110 ]
  [[ "$output" == *"Docker daemon is not running"* ]]
}
