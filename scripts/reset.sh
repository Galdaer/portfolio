#!/usr/bin/env bash
set -euo pipefail
# reset.sh - Reset CLINIC stack to clean state
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/Intelluxe-AI/intelluxe-core
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
#    - Contact: licensing@intelluxeai.com for commercial licensing terms
#    - Allows embedding in closed-source products
#
# Choose the license that best fits your use case.
#
# TRADEMARK NOTICE: "Intelluxe" and related branding may be trademark protected.
# Commercial use of project branding requires separate permission.
#________________________________________________________________________________________________
# Purpose: Resets the Plex + WireGuard namespace stack by removing containers, routes, iptables, and configs, then reboots the stack with bootstrap.sh.
#
# Requirements:
#   - Docker, WireGuard, iptables, iproute2, bootstrap.sh
#
# Usage: ./reset.sh [--log-file PATH] [--no-color] [--debug] [--dry-run] [--help]
#
# Dependency note: This script requires bash, coreutils, docker, iproute2, iptables, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${NS_NAME:=clinicns}"
: "${COLOR:=true}"
: "${DEBUG:=false}"
: "${DRY_RUN:=false}"
: "${DOCKER_NETWORK_NAME:=wireguard-net}"

EXIT_DEPENDENCY_MISSING=2
EXIT_NAMESPACE_DELETE_FAILED=3
EXIT_BOOTSTRAP_FAILED=4

# If running in CI, skip privileged actions or mock them
if [[ "${CI:-false}" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--log-file PATH] [--no-color] [--debug] [--dry-run] [--help]
Version: $SCRIPT_VERSION
"

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Script-specific flags
while [[ $# -gt 0 ]]; do
	case "$1" in
	--log-file)
		LOG_FILE="$2"
		shift 2
		;;
	--)
		shift
		break
		;;
	*) break ;;
	esac
done

require_deps docker ip iptables

if [[ ! -x ./scripts/bootstrap.sh ]]; then
	fail "bootstrap.sh is not found or not executable."
	exit $EXIT_DEPENDENCY_MISSING
fi

LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/reset.log"

rotate_log_if_needed
touch "$LOG_FILE"
if ! chown "$(whoami)" "$LOG_FILE" 2>/dev/null; then
	true
fi

log "💚 Cleaning up containers & Docker network"
if [[ $DRY_RUN == true ]]; then
    log "[DRY-RUN] Would remove containers matching (clinic|wireguard)"
    log "[DRY-RUN] Would remove docker network ${DOCKER_NETWORK_NAME}"
else
    docker ps -a --format '{{.ID}} {{.Names}}' | grep -E '(clinic|wireguard)' | awk '{print $1}' | xargs -r docker rm -f
    docker network rm "${DOCKER_NETWORK_NAME}" 2>/dev/null || true
fi

log "💥 Deleting namespace + veth interfaces"
if [[ $DRY_RUN == true ]]; then
	log "[DRY-RUN] Would delete namespace $NS_NAME and veth interfaces"
else
	if [[ -e "/var/run/netns/$NS_NAME" ]]; then
		if ! ip netns del "$NS_NAME" 2>/dev/null; then
			warn "❌ Failed to delete namespace $NS_NAME."
			exit $EXIT_NAMESPACE_DELETE_FAILED
		fi
	else
		log "ℹ️ Namespace $NS_NAME does not exist; skipping deletion"
	fi
	ip link del veth-host 2>/dev/null || true
fi

log "📉 Tearing down WireGuard interface"
if [[ $DRY_RUN == true ]]; then
	log "[DRY-RUN] Would delete WireGuard interface wg0"
else
	ip link del wg0 2>/dev/null || true
fi

log "🚫 Flushing iptables and NAT rules"
if [[ $DRY_RUN == true ]]; then
	log "[DRY-RUN] Would flush iptables and remove policy routing rules"
else
	ip rule del fwmark 66 table 66 2>/dev/null || true
	iptables -t nat -F
	iptables -t filter -F
	iptables -t mangle -F
fi

log "📄 Removing policy routing (fwmark + table 66)"
if [[ $DRY_RUN == true ]]; then
	log "[DRY-RUN] Would flush route table 66"
else
	ip route flush table 66 2>/dev/null || true
fi

log "🧼 Cleaning up stale WireGuard configs"
if [[ $DRY_RUN == true ]]; then
	log "[DRY-RUN] Would remove netns resolv.conf and namespace files"
else
	rm -f "/etc/netns/$NS_NAME/resolv.conf"
	rm -f "/var/run/netns/$NS_NAME"
fi

# --- Check for Persistent Firewall Rules ---
if [[ -f /etc/iptables/rules.v4 || -f /etc/iptables/rules.v6 ]]; then
	warn "⚠️ Warning: Persistent iptables rules detected"
	warn "    These may override flushed rules on reboot if netfilter-persistent is enabled."
	warn "    You can update them manually via: sudo iptables-save > /etc/iptables/rules.v4"
fi

log "🔁 Restarting full stack"
bootstrap_exit=0
args=(--log-file "$LOG_FILE")
if [[ $DEBUG == true ]]; then
	args+=("--debug")
fi
if [[ $DRY_RUN == true ]]; then
	args+=("--dry-run" "--non-interactive")
else
	args+=("--non-interactive")
fi
if [[ $COLOR == false ]]; then
	args+=("--no-color")
fi

if [[ $DRY_RUN == true ]]; then
	log "[DRY-RUN] Would run: ./scripts/bootstrap.sh ${args[*]}"
else
	./scripts/bootstrap.sh "${args[@]}"
	bootstrap_exit=$?
fi

if ((bootstrap_exit != 0)); then
	warn "⚠️ bootstrap.sh exited with code $bootstrap_exit (non-critical)"
	exit $EXIT_BOOTSTRAP_FAILED
fi

ok "✅ reset.sh complete."
