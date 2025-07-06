#!/usr/bin/env bash
# Test service discovery functionality
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../scripts/clinic-lib.sh"

# Test service discovery
echo "Testing service discovery..."

# Simulate the service discovery logic
ALL_CONTAINERS=()
declare -A CONTAINER_DESCRIPTIONS=()
declare -A CONTAINER_PORTS=()

for confdir in "${SCRIPT_DIR}/../services/core" "${SCRIPT_DIR}/../services/user"; do
        for conf in "$confdir"/*.conf; do
                [ -f "$conf" ] || continue
                svc=$(basename "$conf" .conf)
                desc=$(grep -E '^description=' "$conf" | cut -d= -f2-)
                port=$(grep -E '^port=' "$conf" | cut -d= -f2-)
                [[ -n "$port" ]] && CONTAINER_PORTS[$svc]="$port"
                if grep -q '^image=' "$conf"; then
                        if [[ " ${ALL_CONTAINERS[*]} " != *" $svc "* ]]; then
                                ALL_CONTAINERS+=("$svc")
                        fi
                        [[ -n "$desc" ]] && CONTAINER_DESCRIPTIONS[$svc]="$desc"
                fi
        done
done

echo "Discovered ${#ALL_CONTAINERS[@]} services:"
for svc in "${ALL_CONTAINERS[@]}"; do
    echo "  - $svc: ${CONTAINER_DESCRIPTIONS[$svc]:-No description} (port: ${CONTAINER_PORTS[$svc]:-N/A})"
done

# Test get_service_config_value function
get_service_config_value() {
    local svc_file="$1"
    local key="$2"
    local default="${3:-}"
    
    if [[ -f "$svc_file" ]]; then
        local value
        value=$(grep -E "^${key}=" "$svc_file" | head -n1 | cut -d= -f2- || echo "$default")
        # Expand environment variables
        eval echo "$value"
    else
        echo "$default"
    fi
}

echo ""
echo "Testing configuration parsing..."
for svc in "${ALL_CONTAINERS[@]}"; do
    svc_file=""
    if [[ -f "${SCRIPT_DIR}/../services/core/${svc}.conf" ]]; then
        svc_file="${SCRIPT_DIR}/../services/core/${svc}.conf"
        echo "Core service: $svc"
    elif [[ -f "${SCRIPT_DIR}/../services/user/${svc}.conf" ]]; then
        svc_file="${SCRIPT_DIR}/../services/user/${svc}.conf"
        echo "User service: $svc"
    fi
    
    if [[ -n "$svc_file" ]]; then
        image=$(get_service_config_value "$svc_file" "image")
        port=$(get_service_config_value "$svc_file" "port")
        volumes=$(get_service_config_value "$svc_file" "volumes")
        echo "  Image: $image"
        echo "  Port: $port"
        echo "  Volumes: ${volumes:-none}"
        echo ""
    fi
done

echo "✅ Service discovery test completed successfully!"