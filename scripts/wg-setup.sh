#!/usr/bin/env bash
set -uo pipefail # Removed -e to prevent systemd service failure blocking boot
# wg-setup.sh - WireGuard client setup in clinic namespace
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
#_____________________________________________________________________
# Purpose: Bring up the WireGuard interface inside the clinic namespace.
#
# Requirements:
#   - wg-quick, ip
#
# Usage: ./wg-setup.sh [--iface IFACE] [--netns NAME] [--no-color] [--debug] [--help]
#
# Dependency note: This script requires bash, coreutils, iproute2, wg-quick, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${NS_NAME:=clinicns}"
: "${IFACE:=wg0}"
: "${COLOR:=true}"
: "${DEBUG:=false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

USAGE="Usage: $0 [--iface IFACE] [--netns NAME] [--no-color] [--debug] [--help]
Version: $SCRIPT_VERSION"

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Script-specific flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --iface)
            IFACE="$2"
            shift 2
            ;;
        --netns)
            NS_NAME="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

require_deps ip wg-quick

# Must be run as root
if [[ "$EUID" -ne 0 ]]; then
    fail "Must be run as root."
    exit 1
fi

LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/wg-setup.log"
rotate_log_if_needed

run ip netns exec "$NS_NAME" wg-quick up "$IFACE"

ok "WireGuard interface $IFACE brought up in namespace $NS_NAME."
