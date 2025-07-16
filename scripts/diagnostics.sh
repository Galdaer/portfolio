#!/usr/bin/env bash
set -euo pipefail
# diagnostics.sh - System diagnostic and health check tool
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
#
#────────────────────────────────────────────────────────────────────────
# Requirements: ss, curl, docker, jq, dig
#
# Usage: ./diagnostics.sh [options]
#   --log-file FILE       Log file path (default: /var/log/diagnostics.log)
#   --dns-ip IP           DNS server to test (default: ADGUARD_CONTAINER_IP from
#                         ${CFG_ROOT}/.bootstrap.conf)
#   --dns-fallback IP     Fallback DNS server (default: 8.8.8.8)
#   --wg-port PORT        WireGuard UDP port (default: 51820)

#   --no-color            Disable color output
#   --debug               Enable debug logging
#   --deep-check          Enable extra systemd checks
#   --export-json         Output JSON report
#   --safe                Safe mode (skip auto-repair)
#   --critical-only       Only log critical issues
#   --source=SRC          Source tag for metrics
#   --help                Show this help and exit

# Dependency note: This script requires bash, coreutils, jq, docker, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${NS_NAME:=clinicns}"
: "${COLOR:=true}"
: "${DEBUG:=false}"
: "${DRY_RUN:=false}"
: "${CRITICAL_ONLY:=false}"
: "${EXPORT_JSON:=false}"
: "${SAFE_MODE:=false}"
: "${DEEP_CHECK:=false}"
: "${SOURCE:=manual}"
START_TIME=$(date +%s%3N)

init_dns_config() {
    : "${CFG_ROOT:=/opt/intelluxe/stack}"
    local config_file="${CFG_ROOT}/.bootstrap.conf"
    if [[ -f "$config_file" ]]; then
        # shellcheck source=/dev/null
        source "$config_file"
    fi

    : "${ADGUARD_CONTAINER_IP:=172.20.0.3}"
    : "${DNS_IP:=$ADGUARD_CONTAINER_IP}"
    DNS_FALLBACK="${DNS_FALLBACK:-8.8.8.8}"
}

init_dns_config
# Default WireGuard port
: "${WG_PORT:=51820}"


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--log-file FILE] [--dns-ip IP] [--dns-fallback IP] [--wg-port PORT] [--no-color] [--debug] [--deep-check] [--export-json] [--safe] [--critical-only] [--source=SRC] [--help]
Version: $SCRIPT_VERSION
"


# Print usage then exit without triggering cleanup traps
exit_with_usage() {
        local code="${1:-0}"
        trap - SIGINT SIGTERM ERR EXIT
        echo "$USAGE" | head -n 1
        exit "$code"
}

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Script-specific flags
while [[ $# -gt 0 ]]; do
	case "$1" in
	--log-file)
		LOG_FILE="$2"
		shift 2
		;;
	--dns-ip)
		DNS_IP="$2"
		shift 2
		;;
	--dns-fallback)
		DNS_FALLBACK="$2"
		shift 2
		;;
	--wg-port)
		WG_PORT="$2"
		shift 2
		;;

	--critical-only)
		CRITICAL_ONLY=true
		shift
		;;
	--export-json)
		EXPORT_JSON=true
		shift
		;;
	--safe)
		SAFE_MODE=true
		shift
		;;
	--deep-check)
		DEEP_CHECK=true
		shift
		;;
	--source=*)
		SOURCE="${1#*=}"
		shift
		;;
        --)
                shift
                break
                ;;
        *)
                exit_with_usage 1
                ;;
        esac
done

if [[ $# -gt 0 ]]; then
        exit_with_usage 1
fi

require_deps ss curl jq dig

# Logs are stored under the configured Intelluxe root by default.
# Set CFG_ROOT in /opt/intelluxe/stack/.bootstrap.conf or export it before running
# to change the log location.
LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/diagnostics.log"

rotate_log_if_needed
touch "$LOG_FILE"
if [[ $(id -u) -eq 0 ]]; then chown "$(whoami)" "$LOG_FILE" 2>/dev/null || true; fi

FAILURES=()
PASS=true
CHECK_COUNT=0

write_metric() {
	local test="$1"
	local value="$2"
	# Log metrics to file instead of InfluxDB
	echo "$(date -Iseconds) host=$(hostname -s) test=$test success=$value" >> "$LOG_FILE"
}

report() {
	local type="$1"
	shift
	local msg="$*"
	case "$type" in
	pass) ok "[PASS]  $msg" ;;
	fail)
		fail "[FAIL]  $msg"
		FAILURES+=("$msg")
		PASS=false
		;;
	info) $CRITICAL_ONLY || log "[INFO]  $msg" ;;
	esac
}

# Check core Intelluxe services
CHECK_COUNT=$((CHECK_COUNT + 1))
if docker ps --filter "name=ollama" --filter "status=running" --format "table {{.Names}}" | grep -q ollama; then
	report pass "Ollama service is running"
	write_metric "Ollama" 1
else
	report fail "Ollama service is not running"
	write_metric "Ollama" 0
fi

CHECK_COUNT=$((CHECK_COUNT + 1))
if docker ps --filter "name=healthcare-mcp" --filter "status=running" --format "table {{.Names}}" | grep -q healthcare-mcp; then
	report pass "Healthcare-MCP service is running"
	write_metric "HealthcareMCP" 1
else
	report fail "Healthcare-MCP service is not running"
	write_metric "HealthcareMCP" 0
fi

CHECK_COUNT=$((CHECK_COUNT + 1))
dns_ok=false
for i in {1..3}; do
	if timeout 5 dig +short google.com @"$DNS_IP" &>/dev/null; then
		dns_ok=true
		break
	fi
	sleep 1
done
if ! $dns_ok; then
	for i in {1..3}; do
		if timeout 5 dig +short google.com @"$DNS_FALLBACK" &>/dev/null; then
			dns_ok=true
			break
		fi
		sleep 1
	done
fi
if $dns_ok; then
	report pass "DNS lookup succeeded (google.com)"
	write_metric "DNS" 1
else
	report fail "DNS resolution failed via $DNS_IP and fallback $DNS_FALLBACK"
	write_metric "DNS" 0
fi

CHECK_COUNT=$((CHECK_COUNT + 1))
if ss -uln | grep -q ":$WG_PORT"; then
	report pass "WireGuard server is listening on UDP $WG_PORT"
	write_metric "ExternalReachability" 1
else
	report fail "WireGuard UDP $WG_PORT is closed. Ensure the WireGuard service is running and the port is correctly configured."
	write_metric "ExternalReachability" 0
fi

if [[ "$DEEP_CHECK" == true ]]; then
	CHECK_COUNT=$((CHECK_COUNT + 1))
	log "[INFO] Running deep systemd verification..."
	if [[ -x /usr/local/bin/systemd-verify.sh ]]; then
		tmpjson=$(mktemp)
		/usr/local/bin/systemd-verify.sh --export-json >"$tmpjson" || true
		if jq -e '.failures? | length > 0' "$tmpjson" &>/dev/null; then
			while IFS= read -r issue; do
				report fail "$issue"
				write_metric "SystemdIssue" 0
			done < <(jq -r '.failures[]' "$tmpjson")
		else
			report pass "No systemd issues detected (deep check)"
			write_metric "SystemdIssue" 1
		fi
		rm -f "$tmpjson"
	else
		report fail "Deep check skipped: systemd-verify.sh not found or not executable."
	fi
fi

# If running in CI, skip privileged actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi

# CI mode handling
if [[ "$CI" == "true" ]]; then
	echo "[CI] Running in CI mode."
fi

END_TIME=$(date +%s%3N)
DURATION_MS=$((END_TIME - START_TIME))
FAIL_COUNT=${#FAILURES[@]}
ANY_FAILURE=0
[[ $FAIL_COUNT -gt 0 ]] && ANY_FAILURE=1

if [[ "$DRY_RUN" != true ]]; then
	# Write summary metrics to log file
	echo "$(date -Iseconds) host=$(hostname -s) summary any_failure=$ANY_FAILURE fail_count=$FAIL_COUNT total_checks=$CHECK_COUNT duration_ms=$DURATION_MS" >> "$LOG_FILE"
fi

log "===== Diagnostics Summary ====="
log "Checks run: $CHECK_COUNT"
log "Failures: $FAIL_COUNT"
for f in "${FAILURES[@]}"; do log "  - $f"; done

if [[ "$EXPORT_JSON" == true ]]; then
	JSON_PATH="/tmp/diagnostics.json"
	{
		echo '{'
		echo '  "source": "'"$SOURCE"'",'
		echo '  "timestamp": "'"$(date -Iseconds)"'",'
		echo '  "status": "'"$($PASS && echo 'PASS' || echo 'FAIL')"'",'
		echo '  "failures": ['
		for ((i = 0; i < ${#FAILURES[@]}; i++)); do
			if [[ $i -lt $((${#FAILURES[@]} - 1)) ]]; then
				sep=','
			else
				sep=''
			fi
			printf '    "%s"%s\n' "${FAILURES[$i]//\"/\\\"}" "$sep"
		done
		echo '  ]'
		echo '}'
	} >"$JSON_PATH"
	info "Exported JSON to $JSON_PATH"
fi

if $PASS; then
	log "[INFO] Diagnostics complete."
	exit 0
else
	if $SAFE_MODE; then
		log "[SAFE] Skipping auto-repair due to --safe mode"
	fi
	exit 1
fi
