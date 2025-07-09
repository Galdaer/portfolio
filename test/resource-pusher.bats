#!/usr/bin/env bats

setup() {
  if [ ! -f scripts/resource-pusher.sh ]; then
    skip "resource-pusher.sh not present"
  fi
  # Use a more robust temp directory setup
  if [[ -z "${TMPDIR:-}" ]]; then
    export TMPDIR="/tmp"
  fi
  TMPBIN="$TMPDIR/resource-pusher-test-$$"
  mkdir -p "$TMPBIN"
  export PATH="$TMPBIN:$PATH"
}

teardown() {
  # Clean up test directory
  if [[ -n "${TMPBIN:-}" && -d "$TMPBIN" ]]; then
    rm -rf "$TMPBIN"
  fi
}

create_mock_curl() {
  # Create a safer mock curl script
  cat >"$TMPBIN/curl" <<'CURL_MOCK'
#!/usr/bin/env bash
echo "204"
exit 0
CURL_MOCK
  chmod +x "$TMPBIN/curl"
  # Verify the mock was created
  if [[ ! -x "$TMPBIN/curl" ]]; then
    echo "Failed to create mock curl at $TMPBIN/curl" >&2
    return 1
  fi
}

@test "--help prints usage and exits 0" {
  CI=true run bash scripts/resource-pusher.sh --help
  [ "$status" -eq 0 ]
  # Check that usage message appears in the output (may be after CI messages)
  [[ "${lines[*]}" == *Usage:*resource-pusher.sh* ]]
  # Ensure usage line is present
  local usage_found=false
  for line in "${lines[@]}"; do
    if [[ "$line" == Usage:*resource-pusher.sh* ]]; then
      usage_found=true
      break
    fi
  done
  [ "$usage_found" = true ]
}

# The script uses parse_basic_flags which does not error on unknown arguments;
# verify this behavior intentionally returns exit code 0.
@test "unknown argument exits 0" {
  create_mock_curl
  CI=true run bash scripts/resource-pusher.sh --foo
  [ "$status" -eq 0 ]
}

# Missing positional arguments also lead to a usage message and exit 0 by design
# rather than treating it as an error.
@test "missing required argument exits 0" {
  create_mock_curl
  CI=true run bash scripts/resource-pusher.sh
  [ "$status" -eq 0 ]
}

@test "valid invocation exits 0" {
  tmpfile=$(mktemp)
  create_mock_curl
  CI=true run bash scripts/resource-pusher.sh "$tmpfile"
  [ "$status" -eq 0 ]
  rm -f "$tmpfile"
}

