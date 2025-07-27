#!/usr/bin/env bash
set -euo pipefail
# systemd-verify.sh - Verify SystemD service configurations
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
# Purpose: Validate that all referenced scripts and environment files in the systemd directory exist and are secure.
#          Also checks for recommended systemd logging and status directives, and
#          verifies units using `systemd-analyze verify` when available.
# Usage: ./systemd-verify.sh [--details]
#
# Requirements: find, systemctl
#
# Usage: ./systemd-verify.sh [--no-color] [--dry-run] [--log-file PATH] [--export-json] [--help]
#   --no-color        Disable colorized output
#   --dry-run         Simulate the audit without executing commands
#   --log-file PATH   Specify the log file (default: /var/log/systemd-verify.log)
#   --export-json     Write results as JSON to /tmp/systemd-verify.json
#   --help            Show this help and exit
#
# Dependency note: This script requires bash, coreutils, systemctl, find, and standard Unix tools.
# For CI, log files are written to $PWD/logs/ if possible.

SCRIPT_VERSION="1.0.0"
: "${COLOR:=true}"
: "${DRY_RUN:=false}"
: "${EXPORT_JSON:=false}"
: "${CI:=false}"
# Root directory for configuration and logs. Override to relocate
# .bootstrap.conf and the logs directory.
: "${CFG_ROOT:=/opt/intelluxe/stack}"

# In CI, use a writable logs directory
if [[ "${CI:-false}" == "true" ]]; then
    LOG_DIR="${LOG_DIR:-${PWD}/logs}"
    mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp/intelluxe-logs"
else
    LOG_DIR="${LOG_DIR:-${CFG_ROOT}/logs}"
fi

mkdir -p "$LOG_DIR" 2>/dev/null || true
LOG_FILE="$LOG_DIR/systemd-verify.log"
: "${SYSLOG_TAG:=systemd-verify}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib.sh
source "${SCRIPT_DIR}/lib.sh"
trap cleanup SIGINT SIGTERM ERR EXIT

# shellcheck disable=SC2034
USAGE="Usage: $0 [--no-color] [--dry-run] [--log-file PATH] [--export-json] [--help]
Runs systemd-analyze verify on each unit when available.
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
        --export-json)
            EXPORT_JSON=true
            shift
            ;;
        --)
            shift
            break
            ;;
        *) break ;;
    esac
done

require_deps find systemctl

rotate_log_if_needed
touch "$LOG_FILE"
if ! chown "$(whoami)" "$LOG_FILE" 2>/dev/null; then
    true
fi

log "🔍 Checking for dangling symlinks..."
run find /etc/systemd/system/ -name "intelluxe-*" -xtype l

log "🔍 Checking for proper file ownership (development: user:intelluxe, system: root/intelluxe)..."
run find /etc/systemd/system/ -name "intelluxe-*" ! -user root -ls

log "🔍 Checking for incorrect permissions (development: 644/755 for systemd, 660/664/755 for configs)..."
run find /etc/systemd/system/ -name "intelluxe-*" -type f \( ! -perm 644 -a ! -perm 755 \) -ls

log "🔍 Checking for failed systemd unit dependencies..."
if ! run systemctl list-dependencies --failed; then
    warn "No failed dependencies found."
fi

SYSTEMD_DIR="$(dirname "$0")/../systemd"
SCRIPTS_DIR="$(dirname "$0")"
DETAILS=false

for arg in "$@"; do
    [[ "$arg" == "--details" ]] && DETAILS=true
    [[ "$arg" == "-d" ]] && DETAILS=true
    [[ "$arg" == "-h" || "$arg" == "--help" ]] && {
        echo "Usage: $0 [--details]"
        exit 0
    }
done

failures=0
warns=0
tmp_fail="$(mktemp)"
tmp_warn="$(mktemp)"
declare -a FAILURES_ARRAY=()
declare -a WARNINGS_ARRAY=()
declare -a VERIFY_ARRAY=()

# Helper: Check if a file exists and is secure (development permissions: 660/664 for configs, 755 for scripts, justin:intelluxe ownership)
check_file_secure() {
    local f="$1" type="$2"
    if [[ ! -e "$f" ]]; then
        msg="[FAIL] Missing: $f ($type)"
        echo "$msg" | tee -a "$tmp_fail"
        FAILURES_ARRAY+=("$msg")
        return 1
    fi
    local perm owner
    perm=$(stat -L -c '%a' "$f")
    owner=$(stat -L -c '%U' "$f")
    if [[ "$type" == "script" ]]; then
        # Development: 775 (rwxrwxr-x) for collaborative group access
        [[ "$perm" =~ ^0?775$ ]] || {
            msg="[WARN] $f is $perm, should be 775 (development)"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
        [[ -x "$f" ]] || {
            msg="[WARN] $f is not executable"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
    elif [[ "$type" == "env" ]]; then
        # Development: 660 (rw-rw----) or 664 (rw-rw-r--) for group collaboration
        [[ "$perm" =~ ^0?66[04]$ ]] || {
            msg="[WARN] $f is $perm, should be 660/664 (development)"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
    fi

    # System binaries should be owned by root
    if [[ "$f" =~ ^/(bin|sbin|usr/(s?bin|local/bin))/ ]]; then
        [[ "$owner" == "root" ]] || {
            msg="[WARN] System binary $f is owned by $owner, should be root"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
    # Development mode: check for current user ownership (justin:intelluxe)
    elif [[ "$f" =~ ^(/home/intelluxe|/opt/intelluxe/(scripts|stack)) ]]; then
        # Development files should be owned by justin (1000) with intelluxe group (1001)
        local uid gid
        uid=$(stat -L -c '%u' "$f")
        gid=$(stat -L -c '%g' "$f")
        [[ "$uid" == "1000" && "$gid" == "1001" ]] || {
            msg="[WARN] Development file $f is $uid:$gid, should be 1000:1001 (justin:intelluxe)"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
    else
        # Other system files should be owned by intelluxe
        [[ "$owner" == "intelluxe" ]] || {
            msg="[WARN] $f is owned by $owner, should be intelluxe"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
    fi
}

# Helper: Check for systemd logging/status directives
check_systemd_logging() {
    local file="$1"

    # Skip logging checks for timer files - they don't execute commands directly
    if [[ "$file" == *.timer ]]; then
        return 0
    fi

    # Only check service files for logging directives
    if [[ "$file" == *.service ]]; then
        grep -qE 'Standard(Output|Error)=' "$file" || {
            msg="[WARN] $file missing StandardOutput/StandardError"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
        grep -q SyslogIdentifier= "$file" || {
            msg="[WARN] $file missing SyslogIdentifier (optional but recommended)"
            echo "$msg" | tee -a "$tmp_warn"
            WARNINGS_ARRAY+=("$msg")
        }
    fi
}

# If running in CI, skip privileged actions or mock them
if [[ "$CI" == "true" && "$EUID" -ne 0 ]]; then
    echo "[CI] Skipping root-required actions."
    exit 0
fi

# Main: Scan all .service and .timer files from installed location, fall back to source
INSTALLED_UNITS=$(ls /etc/systemd/system/intelluxe-*.service /etc/systemd/system/intelluxe-*.timer 2>/dev/null || true)
if [[ -n "$INSTALLED_UNITS" ]]; then
    log "Checking installed systemd units with intelluxe- prefix in /etc/systemd/system/"
    for unit in $INSTALLED_UNITS; do
        [[ -f "$unit" ]] || continue

        # Map installed unit back to source file (remove intelluxe- prefix)
        unit_basename=$(basename "$unit")
        source_unit_name="${unit_basename#intelluxe-}"
        source_unit_path="$SYSTEMD_DIR/$source_unit_name"

        # Verify the source file exists
        if [[ ! -f "$source_unit_path" ]]; then
            msg="[FAIL] Installed unit $unit has no corresponding source file $source_unit_path"
            echo "$msg" | tee -a "$tmp_fail"
            FAILURES_ARRAY+=("$msg")
            continue
        fi

        # Check ExecStart/ExecStartPre/ExecStartPost for scripts
        while read -r line; do
            script=$(echo "$line" | awk -F= '{print $2}' | awk '{print $1}')
            # Only check scripts in /usr/local/bin or scripts dir
            if [[ "$script" =~ ^/usr/local/bin/ ]]; then
                sname=$(basename "$script")
                if [[ -f "$SCRIPTS_DIR/$sname" ]]; then
                    check_file_secure "$SCRIPTS_DIR/$sname" script
                else
                    check_file_secure "$script" script
                fi
            elif [[ "$script" =~ ^/ ]]; then
                check_file_secure "$script" script
            fi
        done < <(grep -E 'ExecStart|ExecStartPre|ExecStartPost' "$source_unit_path")
        # Check EnvironmentFile for env files
        while read -r line; do
            envfile=$(echo "$line" | awk -F= '{print $2}' | awk '{print $1}')
            # Remove leading - (optional file indicator) from systemd EnvironmentFile paths
            envfile=${envfile#-}
            # Skip empty environment file paths
            [[ -n "$envfile" ]] || continue
            if [[ -f "$envfile" ]]; then
                check_file_secure "$envfile" env
            else
                msg="[FAIL] Missing env file: $envfile"
                echo "$msg" | tee -a "$tmp_fail"
                FAILURES_ARRAY+=("$msg")
            fi
        done < <(grep "EnvironmentFile=" "$source_unit_path" | grep -v "^#")
        # Check for logging/status
        check_systemd_logging "$source_unit_path"
        if command -v systemd-analyze >/dev/null 2>&1; then
            # Run systemd-analyze verify on the installed unit, but suppress expected warnings
            # about dependency name mismatches since we use intelluxe- prefix for installation
            verify_out=$(systemd-analyze verify "$unit" 2>&1 | grep -v "has different name" || true)
            status=$?
            if [[ -n "$verify_out" ]]; then
                while IFS= read -r line; do
                    if ((status != 0)); then
                        fail "[verify] $unit: $line"
                    else
                        warn "[verify] $unit: $line"
                    fi
                    VERIFY_ARRAY+=("$unit: $line")
                done <<<"$verify_out"
            fi
        else
            debug "systemd-analyze not found; skipping verify for $unit"
        fi
        $DETAILS && echo "Checked $unit (source: $source_unit_path)"
    done
else
    log "No installed units found, checking source systemd units in $SYSTEMD_DIR"
    for unit in "$SYSTEMD_DIR"/*.service "$SYSTEMD_DIR"/*.timer; do
        [[ -f "$unit" ]] || continue
        # Check ExecStart/ExecStartPre/ExecStartPost for scripts
        while read -r line; do
            script=$(echo "$line" | awk -F= '{print $2}' | awk '{print $1}')
            # Only check scripts in /usr/local/bin or scripts dir
            if [[ "$script" =~ ^/usr/local/bin/ ]]; then
                sname=$(basename "$script")
                if [[ -f "$SCRIPTS_DIR/$sname" ]]; then
                    check_file_secure "$SCRIPTS_DIR/$sname" script
                else
                    check_file_secure "$script" script
                fi
            elif [[ "$script" =~ ^/ ]]; then
                check_file_secure "$script" script
            fi
        done < <(grep -E 'ExecStart|ExecStartPre|ExecStartPost' "$unit")
        # Check EnvironmentFile for env files
        while read -r line; do
            envfile=$(echo "$line" | awk -F= '{print $2}' | awk '{print $1}')
            # Remove leading - (optional file indicator) from systemd EnvironmentFile paths
            envfile=${envfile#-}
            # Skip empty environment file paths
            [[ -n "$envfile" ]] || continue
            if [[ -f "$envfile" ]]; then
                check_file_secure "$envfile" env
            else
                msg="[FAIL] Missing env file: $envfile"
                echo "$msg" | tee -a "$tmp_fail"
                FAILURES_ARRAY+=("$msg")
            fi
        done < <(grep "EnvironmentFile=" "$unit" | grep -v "^#")
        # Check for logging/status
        check_systemd_logging "$unit"
        if command -v systemd-analyze >/dev/null 2>&1; then
            verify_out=$(systemd-analyze verify "$unit" 2>&1)
            status=$?
            if [[ -n "$verify_out" ]]; then
                while IFS= read -r line; do
                    if ((status != 0)); then
                        fail "[verify] $unit: $line"
                    else
                        warn "[verify] $unit: $line"
                    fi
                    VERIFY_ARRAY+=("$unit: $line")
                done <<<"$verify_out"
            fi
        else
            debug "systemd-analyze not found; skipping verify for $unit"
        fi
        $DETAILS && echo "Checked $unit"
    done
fi

failures=${#FAILURES_ARRAY[@]}
warns=${#WARNINGS_ARRAY[@]}
cat "$tmp_fail"
cat "$tmp_warn"
rm -f "$tmp_fail" "$tmp_warn"

echo "---"
if ((failures == 0)); then
    echo "[OK] All referenced scripts and env files exist."
else
    echo "[FAIL] $failures missing files."
fi
if ((warns == 0)); then
    echo "[OK] All permissions and logging directives look good."
else
    echo "[WARN] $warns warnings (see above)."
fi
if [[ "$EXPORT_JSON" == true ]]; then
    JSON_PATH="/tmp/systemd-verify.json"
    {
        echo '{'
        echo '  "timestamp": "'"$(date -Iseconds)"'",'
        echo '  "failures": ['
        for ((i = 0; i < ${#FAILURES_ARRAY[@]}; i++)); do
            [[ $i -lt $((${#FAILURES_ARRAY[@]} - 1)) ]] && sep=',' || sep=''
            printf '    "%s"%s\n' "${FAILURES_ARRAY[$i]//\"/\\\"}" "$sep"
        done
        echo '  ],'
        echo '  "warnings": ['
        for ((i = 0; i < ${#WARNINGS_ARRAY[@]}; i++)); do
            [[ $i -lt $((${#WARNINGS_ARRAY[@]} - 1)) ]] && sep=',' || sep=''
            printf '    "%s"%s\n' "${WARNINGS_ARRAY[$i]//\"/\\\"}" "$sep"
        done
        echo '  ],'
        echo '  "verify": ['
        for ((i = 0; i < ${#VERIFY_ARRAY[@]}; i++)); do
            [[ $i -lt $((${#VERIFY_ARRAY[@]} - 1)) ]] && sep=',' || sep=''
            printf '    "%s"%s\n' "${VERIFY_ARRAY[$i]//\"/\\\"}" "$sep"
        done
        echo '  ]'
        echo '}'
    } >"$JSON_PATH"
    log "Exported JSON to $JSON_PATH"
fi
exit $((failures > 0))
