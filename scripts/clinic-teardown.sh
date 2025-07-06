#!/usr/bin/env bash
set -euo pipefail
# clinic-teardown.sh - Complete removal of CLINIC stack
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/galdaer/intelluxe
#
# Copyright (c) 2025 Justin Michael Sue
#
# Dual License Notice:
# This software is available under two licensing options:
#
# 1. AGPL v3.0 License (Open Source)
#    - Free for personal, educational, and open-source use
#    - Requires derivative works to also be open source
#    - See LICENSE-AGPL file for full terms
#
# 2. Commercial License
#    - For proprietary/commercial use without AGPL restrictions
#    - Contact: jmsue42@gmail.com for commercial licensing terms
#    - Allows embedding in closed-source products
#
# Choose the license that best fits your use case.
#
# TRADEMARK NOTICE: "SHAN" and related branding may be trademark protected.
# Commercial use of project branding requires separate permission.
#
# ─────────────────────────────────────────────────────────────────────────────
# Purpose: Safely tears down Plex, WireGuard, namespace, and iptables rules for the SHaN stack.
#
# Requirements:
#   - Run as root
#   - docker, systemctl, ip, iptables, logger, jq
#
# Usage: ./clinic-teardown.sh [--no-color] [--debug] [--force] [--dry-run] [--all|--vpn-only|--clinic-only]
#   --no-color   Disable colorized output
#   --debug      Enable debug output
#   --force      Skip confirmation prompts
#   --dry-run    Show actions without executing
#   --all        Tear down all components (default)
#   --vpn-only   Only teardown VPN-related components
#   --clinic-only  Only teardown SHaN-related components
#
# Logs to /var/log/clinic-teardown.log and syslog. Exports JSON audit to /tmp/clinic-teardown.json.
# Dependency note: This script requires bash, coreutils, docker, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${COLOR:=true}"
: "${DEBUG:=false}"
: "${FORCE:=false}"
: "${DRY_RUN:=false}"
: "${MODE:=all}"
# Name of the Docker network used by SHaN containers.
# Override via the DOCKER_NETWORK_NAME environment variable or an .env file sourced in clinic-lib.sh.
: "${DOCKER_NETWORK_NAME:=wireguard-net}"

NS_NAME="clinicns"
# shellcheck disable=SC2034
CONTAINERS=(shan traefik wireguard grafana influxdb n8n config-web-ui ollama agentcare-mcp postgres redis)
NETWORKS=("${DOCKER_NETWORK_NAME}")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--no-color] [--debug] [--force] [--dry-run] [--all|--vpn-only|--clinic-only]
Uses DOCKER_NETWORK_NAME (default: ${DOCKER_NETWORK_NAME}) for Docker network cleanup.
Version: $SCRIPT_VERSION
"

require_deps docker systemctl ip iptables logger jq

if [[ "$EUID" -ne 0 ]]; then
	fail "This script must be run as root."
	exit 1
fi

# If running in CI, skip privileged actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi


# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Script-specific flags
while [[ $# -gt 0 ]]; do
	case "$1" in
	--force)
		FORCE=true
		shift
		;;
	--all)
		MODE="all"
		shift
		;;
	--vpn-only)
		MODE="vpn"
		shift
		;;
	--clinic-only)
		MODE="shan"
		shift
		;;
	--help)
		echo "$USAGE"
		exit 0
		;;
	--)
		shift
		break
		;;
	*) break ;;
	esac
done

LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/clinic-teardown.log"

rotate_log_if_needed

# --- Track actions for summary/audit ---
REMOVED_CONTAINERS=()
STOPPED_SERVICES=()
DISABLED_TIMERS=()
DELETED_FILES=()
REMOVED_NETWORKS=()
ACTIONS=()

# --- Teardown Steps ---
if [[ "$MODE" == "all" || "$MODE" == "shan" ]]; then
	confirm "Intelluxe containers and services"
	run systemctl stop clinic-bootstrap.service clinic-reset.service clinic-auto-repair.service || true && STOPPED_SERVICES+=("clinic-bootstrap.service" "clinic-reset.service" "clinic-auto-repair.service")
	run systemctl disable clinic-bootstrap.service clinic-reset.service clinic-auto-repair.service || true
	run systemctl stop clinic-diagnostics.timer clinic-auto-repair.timer || true && DISABLED_TIMERS+=("clinic-diagnostics.timer" "clinic-auto-repair.timer")
	run systemctl disable clinic-diagnostics.timer clinic-auto-repair.timer || true
	run rm -f ./logs/clinic-bootstrap.log ./logs/clinic-reset.log ./logs/clinic-diagnostics.log ./logs/clinic-auto-repair.log && DELETED_FILES+=("./logs/clinic-bootstrap.log" "./logs/clinic-reset.log" "./logs/clinic-diagnostics.log" "./logs/clinic-auto-repair.log")
fi

if [[ "$MODE" == "all" || "$MODE" == "vpn" ]]; then
	confirm "WireGuard stack, namespace, and rules"
	run docker rm -f wireguard || true && REMOVED_CONTAINERS+=("wireguard")
	run ip netns delete "$NS_NAME" || true && ACTIONS+=("netns_removed:$NS_NAME")
	run ip link del wg0 || true && ACTIONS+=("wg_interface_removed:wg0")
	run iptables -F
	iptables -t nat -F
	iptables -t mangle -F && ACTIONS+=("iptables_flushed:true")
	run ip route flush table 66 || true
        run rm -f /etc/netns/$NS_NAME/resolv.conf /var/run/netns/$NS_NAME && DELETED_FILES+=("/etc/netns/$NS_NAME/resolv.conf" "/var/run/netns/$NS_NAME")
        run rm -f ./logs/clinic-teardown.log && DELETED_FILES+=("./logs/clinic-teardown.log")
fi

if [[ "$MODE" == "all" ]]; then
	for net in "${NETWORKS[@]}"; do
		run docker network rm "$net" || true && REMOVED_NETWORKS+=("$net")
	done
fi

ok "🧼 Teardown ($MODE) complete."

# --- Export JSON audit ---
TEARDOWN_JSON="/tmp/clinic-teardown.json"
log "📦 Exporting JSON audit to $TEARDOWN_JSON"
cat >"$TEARDOWN_JSON" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "mode": "$MODE",
  "containers_removed": $(printf '%s\n' "${REMOVED_CONTAINERS[@]}" | jq -R . | jq -s .),
  "services_stopped": $(printf '%s\n' "${STOPPED_SERVICES[@]}" | jq -R . | jq -s .),
  "timers_disabled": $(printf '%s\n' "${DISABLED_TIMERS[@]}" | jq -R . | jq -s .),
  "logs_deleted": $(printf '%s\n' "${DELETED_FILES[@]+"${DELETED_FILES[@]}"}" | jq -R . | jq -s .),
  "netns_removed": "$NS_NAME",
  "wg_interface_removed": "wg0",
  "iptables_flushed": true,
  "networks_removed": $(printf '%s\n' "${REMOVED_NETWORKS[@]}" | jq -R . | jq -s .)
}
EOF

exit 0
