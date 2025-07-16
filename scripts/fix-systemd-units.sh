#!/usr/bin/env bash
set -euo pipefail

# fix-systemd-units.sh - Fix systemd service files to include required directives
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/Intelluxe-AI/intelluxe-core

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="${SCRIPT_DIR}/../systemd"

fix_service_file() {
  local service_file="$1"
  
  echo "Fixing $service_file..."
  
  # Check if StandardOutput/StandardError exist
  if ! grep -qE 'Standard(Output|Error)=' "$service_file"; then
    # Add them before the [Install] section or at end of [Service] section
    if grep -q '\[Install\]' "$service_file"; then
      sed -i '/\[Install\]/i StandardOutput=journal\nStandardError=journal' "$service_file"
    else
      # Add before the last line
      sed -i '$i StandardOutput=journal\nStandardError=journal' "$service_file"
    fi
    echo "  Added Standard directives to $service_file"
  fi
  
  # Check if SyslogIdentifier exists
  if ! grep -q 'SyslogIdentifier=' "$service_file"; then
    # Get service name from filename
    local service_name=$(basename "$service_file" .service)
    # Add before the [Install] section or at end of [Service] section
    if grep -q '\[Install\]' "$service_file"; then
      sed -i "/\[Install\]/i SyslogIdentifier=${service_name}" "$service_file"
    else
      # Add before the last line
      sed -i "\$i SyslogIdentifier=${service_name}" "$service_file"
    fi
    echo "  Added SyslogIdentifier to $service_file"
  fi
  
  # Fix EnvironmentFile path if it uses ${CFG_ROOT}
  if grep -q 'EnvironmentFile=.*\${CFG_ROOT}' "$service_file"; then
    sed -i 's|EnvironmentFile=-\${CFG_ROOT}|EnvironmentFile=-/opt/intelluxe/stack|g' "$service_file"
    echo "  Fixed EnvironmentFile path in $service_file"
  fi
  
  # Fix EnvironmentFile path if it uses relative paths
  if grep -q 'EnvironmentFile=-/etc/default/clinic.conf' "$service_file"; then
    sed -i 's|EnvironmentFile=-/etc/default/clinic.conf|EnvironmentFile=-/opt/intelluxe/stack/clinic.conf|g' "$service_file"
    echo "  Fixed clinic.conf path in $service_file"
  fi
  
  # Ensure file isn't executable
  chmod 644 "$service_file"
  echo "  Set correct permissions (644) on $service_file"
}

echo "Fixing systemd service files in $SYSTEMD_DIR"
for file in "$SYSTEMD_DIR"/*.service; do
  if [ -f "$file" ]; then
    fix_service_file "$file"
  fi
done

# Also fix timer files permissions
for file in "$SYSTEMD_DIR"/*.timer; do
  if [ -f "$file" ]; then
    chmod 644 "$file"
    echo "Set correct permissions (644) on $file"
  fi
done

echo "All systemd service files updated"
