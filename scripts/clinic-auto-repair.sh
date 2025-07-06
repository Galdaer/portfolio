#!/usr/bin/env bash
set -euo pipefail
# clinic-auto-repair.sh - Automated container health monitoring and repair
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
#───────────────────────────────────────────────────────────────────────
# Purpose: Auto-repairs Plex, WireGuard, and AdGuard containers based on health.
#
# Requirements:
#   - Docker, jq, logger, clinic-diagnostics.sh
#
# Usage: ./clinic-auto-repair.sh [--log-file PATH] [--no-color] [--debug] [--help]
#
# Environment variables:
#   CFG_ROOT  Override log directory (default ./logs when unset)
#
# Dependency note: This script requires bash, coreutils, docker, jq, and standard Unix tools.
# Logs are written to ${CFG_ROOT}/logs (or ./logs if CFG_ROOT is unset).

SCRIPT_VERSION="1.0.0"
: "${LOG_FILE:=/var/log/clinic-auto-repair.log}"
: "${SYSLOG_TAG:=clinic-auto-repair}"
: "${COLOR:=false}"
: "${SOURCE:=auto}"
: "${DEBUG:=false}"

# shellcheck disable=SC2034
EXIT_DEPENDENCY_MISSING=4
EXIT_DIAGNOSTICS_MISSING=2
EXIT_JSON_INVALID=3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--log-file PATH] [--no-color] [--debug] [--help]
Version: $SCRIPT_VERSION
Environment variables:
  CFG_ROOT  Override log directory (default: ./logs)
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

require_deps docker jq ./scripts/clinic-diagnostics.sh

rotate_log_if_needed

# CFG_ROOT should be defined by the calling script (usually clinic-bootstrap.sh).
# It should point to the root configuration directory (e.g., /opt/intelluxe/clinic-stack).
# CFG_ROOT may also be set to an absolute path so logs can be redirected
# elsewhere. If CFG_ROOT is unset, logs will be stored locally in ./logs
# for standalone use.
LOG_DIR="${CFG_ROOT:-.}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/clinic-auto-repair.log"

touch "$LOG_FILE"
if ! chown "$(whoami)" "$LOG_FILE" 2>/dev/null; then
	true
fi

log "🔍 Running auto-repair check..."

log "📋 Running diagnostics"
if [[ "$DRY_RUN" == "true" ]]; then
	log "[DRY-RUN] Would run: ./scripts/clinic-diagnostics.sh --source=\"$SOURCE\" --export-json --no-color --log-file \"$LOG_FILE\" --dry-run"
	log "[DRY-RUN] Would check diagnostics JSON and restart unhealthy containers"
	exit 0
else
	./scripts/clinic-diagnostics.sh --source="$SOURCE" --export-json --no-color --log-file "$LOG_FILE"
fi

if [[ ! -f /tmp/clinic-diagnostics.json ]]; then
	fail "❌ Diagnostics JSON not found"
	exit $EXIT_DIAGNOSTICS_MISSING
fi

if ! jq empty /tmp/clinic-diagnostics.json &>/dev/null; then
	fail "❌ Diagnostics JSON is invalid. Check the diagnostics script output."
	exit $EXIT_JSON_INVALID
fi

RESTARTED=()
SERVICES=$(jq -r 'keys[]' /tmp/clinic-diagnostics.json)

for service in $SERVICES; do
	diag_status=$(jq -r --arg svc "$service" '.[$svc]' /tmp/clinic-diagnostics.json || echo "unknown")
	container_health=$(docker inspect -f '{{.State.Health.Status}}' "$service" 2>/dev/null || echo "missing")

	if [[ "$container_health" == "healthy" ]]; then
		ok "✅ $service is healthy (Docker: $container_health, Diagnostics: $diag_status)"
		continue
	fi

	if [[ "$container_health" == "starting" ]]; then
		log "⏳ $service is still initializing"
		continue
	fi

	if [[ "$container_health" == "unhealthy" ]]; then
		warn "⚠️ $service is unhealthy. Consider manual intervention if it continues to fail."
	elif [[ "$container_health" == "missing" ]]; then
		warn "⚠️ $service container is missing. Ensure it is defined and running."
		continue
	fi

	# Retry restarting the container
	retry_restart() {
		local retries=3
		local attempt=0
		while ((attempt < retries)); do
			((attempt++))
			if docker restart "$service" >>"$LOG_FILE" 2>&1; then
				ok "♻️ Successfully restarted $service on attempt $attempt."
				return 0
			fi
			warn "⚠️ Failed to restart $service (attempt $attempt/$retries). Retrying..."
			sleep 5
		done
		fail "❌ Failed to restart $service after $retries attempts."
		return 1
	}

	log "🛠️ Restarting: $service (Docker: $container_health, Diagnostics: $diag_status)"
	if ! retry_restart "$service"; then
		warn "⚠️ Final attempt to restart $service failed"
	fi
	RESTARTED+=("$service")
done

if [[ ${#RESTARTED[@]} -eq 0 ]]; then
	ok "✅ All containers OK — no restart triggered."
else
	ok "♻️ Restarted: ${RESTARTED[*]}"
fi

rm -f /tmp/clinic-diagnostics.json

# If running in CI, skip privileged actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi
