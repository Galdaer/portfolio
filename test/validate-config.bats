#!/usr/bin/env bats

@test "validate_config fails on malformed compose file" {
  tmp=$(mktemp -d)
  CFG_ROOT="$tmp/stack"
  WG_DIR="$tmp/wg"
  WG_CLIENTS_DIR="$WG_DIR/clients"
  BACKUP_DIR="$CFG_ROOT/backups"
  COMPOSE_FILE="$tmp/docker-compose.yml"
  mkdir -p "$CFG_ROOT" "$WG_CLIENTS_DIR" "$BACKUP_DIR"
  echo "services: [" > "$COMPOSE_FILE"

  CFG_UID=$(id -u)
  CFG_GID=$(id -g)

  docker() { if [[ $1 == compose ]]; then return 1; fi; }
  docker-compose() { return 1; }
  warn() { :; }
  log() { :; }
  err() { :; }
  check_port_in_use() { return 1; }
  show_port_usage() { :; }
  verify_container_ip() { :; }
  is_ci_or_virtual_env() { return 0; }

  eval "$(awk '/^lint_compose\(\)/,/^}/' scripts/clinic-bootstrap.sh)"
  eval "$(awk '/^validate_config\(\)/,/^}/' scripts/clinic-bootstrap.sh)"

  run bash -c "$(declare -f lint_compose validate_config log warn err check_port_in_use show_port_usage verify_container_ip docker docker-compose is_ci_or_virtual_env); set -euo pipefail; validate_config"
  [ "$status" -ne 0 ]
}
