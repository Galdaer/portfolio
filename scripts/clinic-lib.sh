#!/usr/bin/env bash
# clinic-lib.sh - Core library functions for CLINIC project
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
#────────────────────────────────────────────────────────────────────────────
# Provides: logging, color, dependency checking, error helpers, argument parsing, dry-run/validate helpers, log rotation, ownership, SELinux, email alert, port checks, and cleanup.
# Dependency note: This script requires bash, coreutils, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

# --- Global Option Defaults (can be overridden by scripts) ---
: "${COLOR:=true}"
: "${DRY_RUN:=false}"
: "${DEBUG:=false}"
: "${NON_INTERACTIVE:=false}"
: "${VALIDATE_ONLY:=false}"
# Allow override for default path in testing environments
: "${INTELLUXE_DEFAULT_ROOT:=/opt/intelluxe/clinic-stack}"
: "${CFG_ROOT:=$INTELLUXE_DEFAULT_ROOT}"
LOG_DIR="${LOG_DIR:-${CFG_ROOT}/logs}"
# Directory creation moved to init_logging function to respect DRY_RUN
LOG_FILE="$LOG_DIR/clinic-lib.log"
: "${LOG_SIZE_LIMIT:=1048576}" # 1MB default
: "${SYSLOG_TAG:=clinic-script}"
EMAIL_ALERT_ENABLED=${EMAIL_ALERT_ENABLED:-false}
EMAIL_ALERT_ADDR=${EMAIL_ALERT_ADDR:-""}
DOCKER_SOCKET="${DOCKER_SOCKET:-/var/run/docker.sock}"
# Ensure DOCKER_SOCKET is a plain path without protocol prefix
if [[ "$DOCKER_SOCKET" == unix://* ]]; then
    DOCKER_SOCKET="${DOCKER_SOCKET#unix://}"
fi
export DOCKER_SOCKET

# --- Color + Log Prefix ---
: "${LOG_PREFIX:=}"

if [[ "$COLOR" == true ]] && [[ -t 1 ]]; then
	_COL_BLUE="\033[1;34m"
	_COL_CYAN="\033[1;36m"
	_COL_YELLOW="\033[1;33m"
	_COL_MAGENTA="\033[1;35m"
	_COL_RED="\033[1;31m"
	_COL_RESET="\033[0m"
else
	_COL_BLUE=""
	_COL_CYAN=""
	_COL_YELLOW=""
	_COL_MAGENTA=""
	_COL_RED=""
	_COL_RESET=""
fi

# --- Logging Helpers ---
ts() { date '+%Y-%m-%d %H:%M:%S'; }

color_echo() {
	local color="$1"
	shift
	if [[ "$COLOR" == true ]]; then
		echo -e "${color}${LOG_PREFIX}$*${_COL_RESET}"
	else
		echo "${LOG_PREFIX}$*"
	fi
}

log_syslog() { command -v logger >/dev/null 2>&1 && logger -t "$SYSLOG_TAG" "$*"; }

log() {
	color_echo "$_COL_BLUE" "[INFO] $*"
	# Create log directory if it doesn't exist (without using run() to avoid recursion)
	if [[ "$DRY_RUN" != true ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
		echo "$(ts) [INFO] $*" >>"$LOG_FILE" 2>/dev/null || true
	fi
	log_syslog "[INFO] $*"
}
ok() {
	color_echo "$_COL_CYAN" "[OK] $*"
	# Create log directory if it doesn't exist (without using run() to avoid recursion)
	if [[ "$DRY_RUN" != true ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
		echo "$(ts) [OK] $*" >>"$LOG_FILE" 2>/dev/null || true
	fi
	log_syslog "[OK] $*"
}
warn() {
	color_echo "$_COL_YELLOW" "[WARN] $*"
	# Create log directory if it doesn't exist (without using run() to avoid recursion)
	if [[ "$DRY_RUN" != true ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
		echo "$(ts) [WARN] $*" >>"$LOG_FILE" 2>/dev/null || true
	fi
	log_syslog "[WARN] $*"
}
fail() {
	color_echo "$_COL_RED" "[FAIL] $*"
	# Create log directory if it doesn't exist (without using run() to avoid recursion)
	if [[ "$DRY_RUN" != true ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
		echo "$(ts) [FAIL] $*" >>"$LOG_FILE" 2>/dev/null || true
	fi
	log_syslog "[FAIL] $*"
}
note() {
	color_echo "$_COL_MAGENTA" "[NOTE] $*"
	# Create log directory if it doesn't exist (without using run() to avoid recursion)
	if [[ "$DRY_RUN" != true ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
		echo "$(ts) [NOTE] $*" >>"$LOG_FILE" 2>/dev/null || true
	fi
	log_syslog "[NOTE] $*"
}
debug() {
	[[ "$DEBUG" == true ]] && color_echo "$_COL_CYAN" "[DEBUG] $*"
	return 0
}
err() {
	color_echo "$_COL_RED" "[ERROR] $*" >&2
	if [[ -n "${LOG_FILE:-}" ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
		echo "$(ts) [ERROR] $*" >>"$LOG_FILE" 2>/dev/null || true
	fi
	log_syslog "[ERROR] $*"
}
die() {
	local code="${2:-1}"
	err "$1"
	[[ -n "$EMAIL_ALERT_ADDR" ]] && email_on_failure "$1"
	exit "$code"
}

# --- Dependency Checking ---
require_deps() {
	local missing=0
	for dep; do
		if ! command -v "$dep" &>/dev/null; then
			fail "Missing dependency: $dep"
			missing=1
		fi
	done
	if ((missing)); then
		exit 2
	fi
}

# --- Argument Parsing Helper ---
parse_basic_flags() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--no-color)
			COLOR=false
			shift
			;;
		--dry-run)
			DRY_RUN=true
			shift
			;;
                --validate)
                        VALIDATE=true
                        VALIDATE_ONLY=true
                        shift
                        ;;
                --validate-only)
                        VALIDATE=true
                        VALIDATE_ONLY=true
                        shift
                        ;;
		--debug)
			DEBUG=true
			shift
			;;
		--non-interactive)
			NON_INTERACTIVE=true
			shift
			;;
		--help)
			[[ -n "$USAGE" ]] && echo "$USAGE"
			exit 0
			;;
		--version)
			if [[ -n "$SCRIPT_VERSION" ]]; then
				echo "Version: $SCRIPT_VERSION"
			else
				echo "Version information not available."
			fi
			exit 0
			;;
		*) 
			# Don't consume unrecognized flags - let the calling script handle them
			break
			;;
		esac
	done
	return 0
}

# --- Dry-run / Validation helpers ---
run() {
	if [[ "$DRY_RUN" == true ]]; then
		log "[dry-run] $*"
		return 0
	fi
	if "$@"; then
		return 0
	else
		return 1
	fi
}

validate_mode() {
	if [[ "${VALIDATE:-false}" == "true" ]]; then
		log "[validate] $*"
		return 0
	fi
	return 1
}

# --- Log Rotation ---
rotate_log_if_needed() {
	# Create log directory if it doesn't exist (without using run() to avoid recursion)
	if [[ "$DRY_RUN" != true ]]; then
		mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
	fi
	
	if [[ -f "$LOG_FILE" ]]; then
		local size
		size=$(stat -c %s "$LOG_FILE")
		if ((size > LOG_SIZE_LIMIT)); then
			local ts
			ts="$(date +"%Y%m%d-%H%M%S")"
			mv "$LOG_FILE" "${LOG_FILE}.${ts}"
			log "Log rotated: ${LOG_FILE}.${ts}"
		fi
	fi
	if [[ "$DRY_RUN" != true ]]; then
		: >"$LOG_FILE"
		chmod 0600 "$LOG_FILE" 2>/dev/null || true
	fi
}

# --- Ownership Helpers ---
set_ownership() {
	if [[ -n "${CFG_UID:-}" && -n "${CFG_GID:-}" ]]; then
		chown "$CFG_UID:$CFG_GID" "$@" 2>/dev/null || true
	fi
}

# --- Secret File Permissions Checker ---
check_secret_perms() {
	local file="$1"
	if [[ -f "$file" ]]; then
		local perm
		perm=$(stat -c "%a" "$file")
		if [[ "$perm" != "600" && "$perm" != "400" ]]; then
			warn "Permissions on $file are $perm (should be 600 or 400)!"
		fi
		if [[ $(stat -c "%U" "$file") != "$USER" ]]; then
			warn "Ownership of $file is not $USER!"
		fi
	fi
}

# --- SELinux Helpers ---
selinux_enabled() {
	command -v getenforce &>/dev/null && [[ "$(getenforce 2>/dev/null)" == "Enforcing" ]]
}
selinux_volume_flag() {
	if selinux_enabled; then
		echo ":Z"
	else
		echo ""
	fi
}

# --- Email Alert on Failure ---
email_on_failure() {
	local msg="$1"
	if [[ "$EMAIL_ALERT_ENABLED" == "true" ]] && command -v mail &>/dev/null && [[ -n "$EMAIL_ALERT_ADDR" ]]; then
		echo "ERROR: $msg" | mail -s "Script Failure [$SYSLOG_TAG]" "$EMAIL_ALERT_ADDR"
		log "Failure notification sent to $EMAIL_ALERT_ADDR"
	fi
}

# --- Port Check Helpers ---
check_port_in_use() {
	local port="$1" proto="${2:-tcp}"
	if [[ "$proto" == "udp" ]]; then
		ss -lun | grep -q -E ":$port\b"
	else
		ss -ltn | grep -q -E ":$port\b"
	fi
}
show_port_usage() {
	local port="$1"
	lsof -i :"$port" 2>/dev/null || ss -lntup | grep ":$port" || true
}

# --- Apply ENV Overrides (for scripts that support ENV_OVERRIDE_VARS) ---
apply_env_overrides() {
	for var in "${ENV_OVERRIDE_VARS[@]}"; do # Removed :- from array expansion
		export "$var=${!var}"
	done
}

# --- Cleanup on Exit (trap this in your script if you want it) ---
cleanup() {
    local exit_code=$?
    
    if [[ "$exit_code" -eq 0 ]]; then
        log "Script exited successfully. Cleaning up any temp files."
    else
        warn "Script interrupted or failed. Cleaning up partial files."
    fi
    
    # Script-specific cleanup hook (if function exists)
    if declare -f script_specific_cleanup >/dev/null 2>&1; then
        log "Running script-specific cleanup..."
        script_specific_cleanup "$exit_code" || true
    fi
    
    # Save any in-progress configuration (if CONFIG_FILE and save_config exist)
    if [[ -n "${CONFIG_FILE:-}" ]] && [[ -f "${CONFIG_FILE}" ]] && declare -f save_config >/dev/null 2>&1; then
        save_config 2>/dev/null || true
    fi
    
    # Release file locks (if they exist)
    # File descriptor 200 is commonly used for locks
    exec 200>&- 2>/dev/null || true
    
    # Clean up temp files (if CFG_ROOT exists)
    if [[ -n "${CFG_ROOT:-}" ]]; then
        find "$CFG_ROOT" -name "*.tmp" -type f -delete 2>/dev/null || true
    fi
    
    # Exit with original code
    exit "$exit_code"
}

# --- Error Trap ---
trap_error() {
	local status=$?
	fail "Script failed at line $1 (exit code $status)"
	exit "$status"
}
set -uE
trap 'trap_error $LINENO' ERR

set -uo pipefail

# If running in CI, skip privileged actions or mock them
# But don't exit when being sourced for tests
if [[ "${CI:-false}" == "true" && "$EUID" -ne 0 ]]; then
	# Only exit if this script is being executed directly, not sourced
	if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
		echo "[CI] Skipping root-required actions."
		exit 0
	else
		echo "[CI] Sourcing clinic-lib.sh in test mode - root actions will be mocked"
	fi
fi

# --- USAGE: Source this file at the top of your script after config block ---
# Example:
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "${SCRIPT_DIR}/clinic-lib.sh"

# --- Confirmation Helper ---
confirm() {
	[[ "$FORCE" == true ]] && return 0
	read -rp "❓ $1 Continue? [y/N] " CONFIRM
	[[ "$CONFIRM" =~ ^[Yy]$ ]] || exit 1
}

# --- Docker Socket Check ---
check_docker_socket() {
	local sock="$DOCKER_SOCKET"
	if [ -S "$sock" ]; then
		local perm
		perm=$(stat -c '%a' "$sock" 2>/dev/null || echo "")
		if [ -n "$perm" ] && [ "$perm" -gt 660 ]; then
			warn "Docker socket $sock is world-writable! This is a security risk."
		fi
	fi
}

# --- UUID Validation ---
validate_uuid() {
        local uuid="$1"
        [[ -n "$uuid" ]] && blkid -U "$uuid" >/dev/null 2>&1
}

# --- CIDR Validation ---
# Returns success if the provided string is a valid IPv4 CIDR.
validate_cidr() {
        local cidr="$1"
        [[ "$cidr" =~ ^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(3[0-2]|[12]?[0-9]|[0-9])$ ]]
}

# --- CI or Virtual Environment Check ---
# Returns success if running under Codex, CI, or a Python virtual environment.
# Checks CODEX_ENV_PYTHON_VERSION, CODEX_PROXY_CERT, CI, and VIRTUAL_ENV.
# Usage: if is_ci_or_virtual_env; then ...; fi
is_ci_or_virtual_env() {
        local var
        for var in CODEX_ENV_PYTHON_VERSION CODEX_PROXY_CERT CI VIRTUAL_ENV; do
                case "$var" in
                        CI)
                                [[ ${CI:-false} == "true" ]] && return 0
                                ;;
                        *)
                                [[ -n ${!var:-} ]] && return 0
                                ;;
                esac
        done
        return 1
}
