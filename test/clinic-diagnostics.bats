#!/usr/bin/env bats

@test "unknown argument prints usage and exits 1" {
  run bash scripts/clinic-diagnostics.sh --foo
  [ "$status" -eq 1 ]
  # Check that usage message appears in the output (may be after CI messages)
  [[ "${lines[*]}" == *Usage:*clinic-diagnostics.sh* ]]
  # Ensure usage line is present
  local usage_found=false
  for line in "${lines[@]}"; do
    if [[ "$line" == Usage:*clinic-diagnostics.sh* ]]; then
      usage_found=true
      break
    fi
  done
  [ "$usage_found" = true ]
}

extract_init() {
  awk '/^init_dns_config\(\)/{flag=1} flag{print} /^}/{if(flag){exit}}' scripts/clinic-diagnostics.sh
}

@test "DNS_IP defaults to ADGUARD_CONTAINER_IP from config" {
  CFG_ROOT=$(mktemp -d)
  echo "ADGUARD_CONTAINER_IP=10.1.2.3" > "$CFG_ROOT/.clinic-bootstrap.conf"

  snippet=$(extract_init)
  eval "$snippet"
  init_dns_config

  [ "$DNS_IP" = "10.1.2.3" ]
  rm -rf "$CFG_ROOT"
}

@test "DNS_IP falls back to built-in default when config missing" {
  CFG_ROOT=$(mktemp -d)

  snippet=$(extract_init)
  eval "$snippet"
  init_dns_config

  [ "$DNS_IP" = "172.20.0.3" ]
  rm -rf "$CFG_ROOT"
}

@test "DNS_FALLBACK uses value from config" {
  CFG_ROOT=$(mktemp -d)
  echo "DNS_FALLBACK=1.1.1.1" > "$CFG_ROOT/.clinic-bootstrap.conf"

  snippet=$(extract_init)
  eval "$snippet"
  init_dns_config

  [ "$DNS_FALLBACK" = "1.1.1.1" ]
  rm -rf "$CFG_ROOT"
}

@test "DNS_FALLBACK defaults when not in config" {
  CFG_ROOT=$(mktemp -d)

  snippet=$(extract_init)
  eval "$snippet"
  init_dns_config

  [ "$DNS_FALLBACK" = "8.8.8.8" ]
  rm -rf "$CFG_ROOT"
}
