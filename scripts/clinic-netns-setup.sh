#!/usr/bin/env bash
set -euo pipefail
# clinic-netns-setup.sh - Network namespace setup for container isolation
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
#____________________________________________________________________________
# Purpose: Setup a Linux network namespace and veth pair for the SHaN stack,
#          with NAT and dynamic outbound interface detection.#
# Requirements:
#   - Run as root
#   - ip, iptables
#
# Usage: ./clinic-netns-setup.sh [--help]
#   Sets up a Linux network namespace called "clinicns" with a veth pair and NAT.
#   Cleans up any prior instance. Requires root privileges.
#
# See README.md or repo for details.
#
# Dependency note: This script requires bash, coreutils, iproute2, iptables, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"

: "${NS_NAME:=clinicns}"
: "${VETH_HOST:=veth-host}"
: "${VETH_NS:=veth-ns}"
: "${NS_CIDR:=192.168.100.0/24}"
: "${HOST_IP:=192.168.100.1}"
: "${NS_IP:=192.168.100.2}"
: "${RESOLV_CONF:=/etc/netns/${NS_NAME}/resolv.conf}"
: "${DNS_SERVER:=1.1.1.1}"
: "${COLOR:=true}"
: "${DEBUG:=false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

require_deps ip iptables

# Must be run as root
if [[ "$EUID" -ne 0 ]]; then
	fail "Must be run as root."
	exit 1
fi

# Skip root-required actions in CI
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
	echo "[CI] Skipping root-required actions."
	exit 0
fi

# Outbound interface detection
OUT_IF=$(ip route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -1)
if [[ -z "$OUT_IF" ]]; then
	fail "Could not determine default outbound adapter"
	exit 1
fi
log "Using outbound interface: $OUT_IF"

# Clean up old namespace and interfaces if they exist
ip netns delete "$NS_NAME" 2>/dev/null || true
rm -f /var/run/netns/"$NS_NAME"
ip link delete "$VETH_HOST" 2>/dev/null || true

# Create namespace and veth pair
ip netns add "$NS_NAME"
ip link add "$VETH_HOST" type veth peer name "$VETH_NS"
ip link set "$VETH_NS" netns "$NS_NAME"

# Assign IP addresses
ip addr add "$HOST_IP/24" dev "$VETH_HOST"
ip link set "$VETH_HOST" up

ip netns exec "$NS_NAME" ip addr add "$NS_IP/24" dev "$VETH_NS"
ip netns exec "$NS_NAME" ip link set "$VETH_NS" up

# Set route in namespace
ip netns exec "$NS_NAME" ip route add default via "$HOST_IP"

# Set DNS in namespace
mkdir -p "$(dirname "$RESOLV_CONF")"
echo "nameserver $DNS_SERVER" >"$RESOLV_CONF"

# Enable NAT on the host
if ! iptables -t nat -C POSTROUTING -s "$NS_CIDR" -o "$OUT_IF" -j MASQUERADE 2>/dev/null; then
	iptables -t nat -A POSTROUTING -s "$NS_CIDR" -o "$OUT_IF" -j MASQUERADE
	log "Added MASQUERADE rule for $NS_CIDR on $OUT_IF"
else
	log "MASQUERADE rule for $NS_CIDR on $OUT_IF already exists"
fi

# Source config file for WG_CONFIG and other settings
CONFIG_FILE=".clinic-bootstrap.conf"
if [[ -f "$CONFIG_FILE" ]]; then
	# shellcheck source=/dev/null
	source "$CONFIG_FILE"
fi

ok "Namespace $NS_NAME setup complete."

# Ensure CFG_ROOT is set before using it for log paths
if [[ -z "${CFG_ROOT:-}" ]]; then
    die "CFG_ROOT is not set" 1
fi

LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/clinic-netns-setup.log"

USAGE="Usage: $(basename "$0") [--help] [--version]
Version: $SCRIPT_VERSION
Sets up a Linux network namespace called \"$NS_NAME\" with a veth pair and NAT.
Cleans up any prior instance. Requires root privileges."
