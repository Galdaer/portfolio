#!/usr/bin/env bash
set -euo pipefail
# resource-pusher.sh - Collect system resource metrics and push to InfluxDB
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/galdaer/intelluxe
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
#______________________________________________________________________________
# Purpose: Gather basic system resource metrics (CPU, memory, disk) and push
#          them to InfluxDB for monitoring.
#
# Requirements:
#   - top, free, df, curl, InfluxDB
#
# Usage: ./resource-pusher.sh [--debug] [--influx-host HOST] [--influx-port PORT] [--influx-db DB] [--help]
# Dependency note: This script requires bash, coreutils, top, free, df, curl, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${INFLUX_HOST:=localhost}"
: "${INFLUX_PORT:=8086}"
: "${INFLUX_DB:=shan_metrics}"
: "${DEBUG:=false}"
: "${DEBUG_LOG:=/var/log/resource-pusher-debug.log}"

INFLUX_URL="http://${INFLUX_HOST}:${INFLUX_PORT}/write?db=${INFLUX_DB}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"
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

require_deps top free df curl

: "${CFG_ROOT:=/opt/intelluxe/clinic-stack}"
LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/resource-pusher.log"

if [[ "$DEBUG" == true ]]; then
    rotate_log_if_needed
    exec > >(tee -a "$DEBUG_LOG") 2>&1
    log "[DEBUG] Debug log started: $(date)"
    log "[DEBUG] Using InfluxDB at $INFLUX_URL"
fi

log "Running resource-pusher..."

# If running in CI, skip privileged actions or mock them
if [[ "${CI:-}" == "true" && "$EUID" -ne 0 ]]; then
    echo "[CI] Skipping root-required actions."
    exit 0
fi

HOSTNAME=$(hostname -s 2>/dev/null || hostname)

# --- Collect metrics ---
cpu_idle=$(top -bn1 | awk '/Cpu\(s\)/ {print $8; exit}')
cpu_usage=$(awk -v idle="$cpu_idle" 'BEGIN {printf "%.1f", 100 - idle}')

read -r mem_total mem_used <<<"$(free -m | awk '/Mem:/ {print $2, $3}')"
mem_usage=$(awk -v used="$mem_used" -v total="$mem_total" 'BEGIN {printf "%.1f", used/total*100}')

disk_usage=$(df -h / | awk 'NR==2 {gsub("%", "", $5); print $5}')

timestamp=$(date +%s%N)
line="hostMetrics,host=${HOSTNAME} cpu_usage=${cpu_usage},mem_usage=${mem_usage},disk_usage=${disk_usage} ${timestamp}"

if [[ "$DEBUG" == true ]]; then
    echo "$line" >/tmp/resource-pusher-line.txt
    log "[DEBUG] Wrote line protocol data to /tmp/resource-pusher-line.txt"
fi

# --- Push data to InfluxDB with retry ---
RETRY_LIMIT=3
RETRY_DELAY=5
for attempt in $(seq 1 "$RETRY_LIMIT"); do
    http_response_code="$(curl -sS -w "%{http_code}" -o /tmp/influx-push-response.txt -XPOST "$INFLUX_URL" --data-binary "$line")"
    curl_exit=$?
    if [[ $curl_exit -eq 0 && "$http_response_code" == "204" ]]; then
        break
    fi
    warn "Warning: InfluxDB push failed (attempt $attempt/$RETRY_LIMIT). Retrying in $RETRY_DELAY seconds..."
    sleep "$RETRY_DELAY"
done

if [[ $curl_exit -ne 0 || "$http_response_code" != "204" ]]; then
    fail "Error: Failed to send data to InfluxDB after $RETRY_LIMIT attempts."
    exit 4
fi

if [[ "$DEBUG" == true ]]; then log "[DEBUG] Metrics push completed."; fi

# Clean up temporary files if not in debug mode
if [[ "$DEBUG" != true ]]; then
    rm -f /tmp/resource-pusher-line.txt /tmp/influx-push-response.txt
fi

exit 0
