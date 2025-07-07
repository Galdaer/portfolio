#!/usr/bin/env bash
set -euo pipefail
# systemd-summary.sh - SystemD service status summary
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
# ─────────────────────────────────────────────────────────────────────────────
# Purpose: Summarizes systemd services and timers:
#   - Running services
#   - Enabled services (start on boot)
#   - Active and scheduled timers
#   - Services pulled in at boot (default.target)
#   - Failed services
#
# Requirements: systemctl
#
# Usage: ./systemd-summary.sh [--no-color] [--dry-run] [--help]
#   --no-color    Disable colorized output
#   --dry-run     Simulate commands without executing them
#   --help        Show this help and exit

SCRIPT_VERSION="1.0.0"
: "${COLOR:=true}"
: "${DRY_RUN:=false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--no-color] [--dry-run] [--help]
Version: $SCRIPT_VERSION
"

# Dependency note: This script requires bash, coreutils, systemctl, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Handle --dry-run for consistency
if [[ "$1" == "--dry-run" ]]; then
	echo "[DRY-RUN] $(basename "$0") would run, but no actions taken."
	exit 0
fi

# If running in CI, skip privileged actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi

# No extra script-specific flags for now

require_deps systemctl

# Logs are stored under $CFG_ROOT/logs. CFG_ROOT defaults to
# /opt/intelluxe/clinic-stack and can be overridden in
# /etc/default/clinic.conf; see scripts/clinic-lib.sh for details.
LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/systemd-summary.log"

log ""
info "🟢 Running Services:"
run systemctl list-units --type=service --state=running

log ""
ok "✅ Enabled Services (Start on Boot):"
run systemctl list-unit-files --type=service --state=enabled

log ""
warn "⏰ Active + Scheduled Timers:"
run systemctl list-timers --all

log ""
note "🚀 Services Pulled In At Boot (default.target):"
run systemctl list-dependencies --after default.target | grep service || true

log ""
fail "❌ Failed Services:"
run systemctl list-units --type=service --state=failed || echo "None"
