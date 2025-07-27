#!/usr/bin/env bash
set -uo pipefail # Removed -e to prevent systemd service failure blocking boot
# diagnostic-pusher.sh - Push diagnostic data to monitoring systems
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
#________________________________________________________________________________________
# Purpose: Exports structured diagnostics metrics to log files and prints JSON if --debug.
#
# Requirements:
#   - jq, curl, diagnostics.sh
#
# Usage: ./diagnostic-pusher.sh [--debug] [--influx-host HOST] [--influx-port PORT] [--influx-db DB] [--help]
# Dependency note: This script requires bash, coreutils, jq, curl, docker, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${INFLUX_HOST:=localhost}"
: "${INFLUX_PORT:=8086}"
: "${INFLUX_DB:=clinic_metrics}"
: "${DEBUG:=false}"
: "${DEBUG_LOG:=/var/log/diagnostic-pusher-debug.log}"
: "${INFLUX_MOCK:=false}"
: "${CI:=false}"

INFLUX_URL="http://${INFLUX_HOST}:${INFLUX_PORT}/write?db=${INFLUX_DB}"
DIAG_JSON="/tmp/diagnostics.json"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--debug] [--influx-host HOST] [--influx-port PORT] [--influx-db DB] [--help]
Version: $SCRIPT_VERSION
"

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Script-specific flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)
            DEBUG=true
            shift
            ;;
        --influx-host)
            INFLUX_HOST="$2"
            shift 2
            ;;
        --influx-port)
            INFLUX_PORT="$2"
            shift 2
            ;;
        --influx-db)
            INFLUX_DB="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *) break ;;
    esac
done
INFLUX_URL="http://${INFLUX_HOST}:${INFLUX_PORT}/write?db=${INFLUX_DB}"

require_deps jq curl

# Ensure CFG_ROOT is defined before using it
: "${CFG_ROOT:?CFG_ROOT must be set}"

LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/diagnostic-pusher.log"

if [[ "$DEBUG" == true ]]; then
    rotate_log_if_needed
    exec > >(tee -a "$DEBUG_LOG") 2>&1
    log "[DEBUG] Debug log started: $(date)"
    log "[DEBUG] Using InfluxDB at $INFLUX_URL"
fi

log "Running diagnostic-pusher..."

# If running in CI, skip privileged actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
    echo "[CI] Skipping root-required actions."
    exit 0
fi

# --- Run diagnostics ---
./scripts/diagnostics.sh --export-json --no-color --log-file "$LOG_FILE"
diag_exit=$?
[[ "$DEBUG" == true ]] && log "[DEBUG] clinic diagnostics tool exited with code $diag_exit."

# --- Validate diagnostics output ---
if [[ ! -s "$DIAG_JSON" ]]; then
    fail "Error: Diagnostics JSON file $DIAG_JSON not found or is empty. Ensure the diagnostics script ran successfully and produced valid output."
    exit 2
fi
if ! jq empty "$DIAG_JSON" &>/dev/null; then
    fail "Error: Diagnostics JSON file $DIAG_JSON is invalid. Check the diagnostics script output."
    exit 3
fi

# --- Parse failures ---
declare -A fail_tests_seen
fail_count=0
failures_array=()
if ! fail_count=$(jq -r 'if .failures then (.failures | length) else 0 end' "$DIAG_JSON" 2>/dev/null); then
    fail "Error: Failed to parse $DIAG_JSON. Please ensure jq is installed and the file is valid JSON."
    exit 3
fi
if ((fail_count > 0)); then
    mapfile -t failures_array < <(jq -r '.failures[]? // empty' "$DIAG_JSON")
    if [[ "$DEBUG" == true ]]; then
        log "Detected $fail_count failure(s) in diagnostics:"
        for f in "${failures_array[@]}"; do
            log "[DEBUG] - $f"
        done
    fi
fi

# --- Prepare InfluxDB line protocol lines ---
LINES=()
HOSTNAME=$(hostname -s 2>/dev/null || hostname)
for f in "${failures_array[@]}"; do
    testName="Unknown"
    if [[ "$f" =~ [Dd][Nn][Ss] || "$f" =~ [Rr]esolve ]]; then
        testName="DNS"
    elif [[ "$f" =~ public[[:space:]]*ip || "$f" =~ clinic\.tv ]]; then
        testName="PublicIP"
    elif [[ "$f" =~ [Pp]ort[[:space:]]*[Mm]apping || "$f" =~ [Uu][Pp][Nn][Pp] || "$f" =~ [Nn][Aa][Tt]-[Pp][Mm][Pp] ]]; then
        testName="PortMapping"
    elif [[ "$f" =~ outside[[:space:]]*your[[:space:]]*network || "$f" =~ not[[:space:]]*reachable[[:space:]]*from[[:space:]]*outside ]]; then
        testName="ExternalReachability"
    elif [[ "$f" =~ [Ll]oopback ]]; then
        testName="NATLoopback"
    elif [[ "$f" =~ [Ss]igned[[:space:]]*in || "$f" =~ [Ss]ign[[:space:]]*in || "$f" =~ [Cc]laimed || "$f" =~ [Aa]uthoriz ]]; then
        testName="Auth"
    fi
    fail_tests_seen["$testName"]=1
    LINES+=("clinicDiagnostics,host=${HOSTNAME},test=${testName} success=0i")
done
known_tests=("DNS" "PublicIP" "PortMapping" "ExternalReachability" "NATLoopback" "Auth")
for t in "${known_tests[@]}"; do
    if [[ -v fail_tests_seen["$t"] ]]; then continue; fi
    LINES+=("clinicDiagnostics,host=${HOSTNAME},test=${t} success=1i")
done
any_fail=0
((fail_count > 0)) && any_fail=1
LINES+=("clinicDiagnosticsSummary,host=${HOSTNAME} fail_count=${fail_count}i,any_failure=${any_fail}i")
TIMESTAMP=$(date +%s%N)
for i in "${!LINES[@]}"; do
    LINES[i]="${LINES[i]} $TIMESTAMP"
done

# --- Debug output of line protocol ---
if [[ "$DEBUG" == true ]]; then
    : >/tmp/influx-debug-lines.txt
    for line in "${LINES[@]}"; do
        echo "$line" >>/tmp/influx-debug-lines.txt
    done
    log "[DEBUG] Wrote line protocol data to /tmp/influx-debug-lines.txt"
fi

# --- Push data to InfluxDB with retry ---
RETRY_LIMIT=3
RETRY_DELAY=5
# Mock InfluxDB push in CI if INFLUX_MOCK is set
if [[ "$INFLUX_MOCK" == "true" ]]; then
    echo "[CI] Skipping InfluxDB push (INFLUX_MOCK set)."
    curl_exit=0            # avoid unbound var; treat as successful curl exit
    http_response_code=204 # mimic 204 No Content success from InfluxDB
    exit 0
else
    for attempt in $(seq 1 "$RETRY_LIMIT"); do
        http_response_code="$(curl -sS -w "%{http_code}" -o /tmp/influx-push-response.txt -XPOST "$INFLUX_URL" --data-binary "$(printf "%s\n" "${LINES[@]}")")"
        curl_exit=$?
        if [[ $curl_exit -eq 0 && "$http_response_code" == "204" ]]; then
            break
        fi
        warn "Warning: InfluxDB push failed (attempt $attempt/$RETRY_LIMIT). Retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
    done
fi

if [[ $curl_exit -ne 0 || "$http_response_code" != "204" ]]; then
    fail "Error: Failed to send data to InfluxDB after $RETRY_LIMIT attempts."
    exit 4
fi

if [[ "$DEBUG" == true ]]; then log "[DEBUG] Metrics push completed."; fi

# --- Clean up temporary files if not in debug mode ---
if [[ "$DEBUG" != true ]]; then
    rm -f /tmp/influx-debug-lines.txt /tmp/influx-push-response.txt
fi
exit 0
