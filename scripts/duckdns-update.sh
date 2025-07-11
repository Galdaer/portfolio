#!/usr/bin/env bash
set -euo pipefail
# duckdns-update.sh - DuckDNS dynamic DNS updater
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
#___________________________________________________________________
# Purpose: Update DuckDNS with current (or specified) IP address.
#
# Requirements:
#   - curl, logger, date, stat, mv
#   - Environment: DUCK_TOKEN, DUCK_DOMAIN (required), DUCK_IP (optional)
#
# Usage: ./duckdns-update.sh [--help]
#        Updates DuckDNS using DUCK_TOKEN and DUCK_DOMAIN env vars (no .duckdns.org).
#        Optionally set DUCK_IP to override auto-detection.
#
# Logs to /var/log/duckdns.log and syslog.
# Dependency note: This script requires bash, coreutils, curl, logger, date, stat, mv, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${MAX_LOG_SIZE:=1048576}" # 1 MB
: "${COLOR:=true}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--help]
Version: $SCRIPT_VERSION
"

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

require_deps curl logger date stat mv

# --- Environment check ---
: "${DUCK_TOKEN:?DUCK_TOKEN env var required}"
: "${DUCK_DOMAIN:?DUCK_DOMAIN env var required}"
DUCK_IP="${DUCK_IP:-}"

# --- Log file rotation ---
# Ensure CFG_ROOT is defined (via lib.sh) before using it here.
LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/duckdns-update.log"
rotate_log_if_needed

# --- Prepare URL ---
url="https://www.duckdns.org/update?domains=${DUCK_DOMAIN}&token=${DUCK_TOKEN}&ip=${DUCK_IP}"

# If running in CI, skip root-required actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi

# --- Retry logic ---
max_tries=3
attempt=1
response=""

while ((attempt <= max_tries)); do
	response="$(curl -sSf "$url" || echo FAIL)"
	if [[ "$response" == "OK" ]]; then
		ok "DuckDNS update succeeded."
		break
	fi
	warn "DuckDNS update failed (attempt $attempt): $response"
	sleep 3
	((attempt++))
done

if [[ "$response" != "OK" ]]; then
	fail "DuckDNS update failed after $max_tries attempts: $response"
	exit 1
fi
