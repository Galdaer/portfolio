#!/bin/bash
# WireGuard Client Removal Script

set -euo pipefail

WG_DIR="${WG_DIR:-/etc/wireguard}"

remove_client() {
    local client_name="$1"
    
    if [[ -z "$client_name" ]]; then
        echo "Usage: $0 <client-name>"
        exit 1
    fi
    
    local client_file="$WG_DIR/clients/${client_name}.conf"
    
    if [[ ! -f "$client_file" ]]; then
        echo "Error: Client '$client_name' not found"
        exit 1
    fi
    
    # Get client public key for removal from server config
    local client_public
    client_public=$(grep "PublicKey = " "$client_file" | head -n1 | awk '{print $3}')
    
    # Remove client configuration
    rm -f "$client_file"
    
    # Remove peer from server configuration (simplified - in production, use wg command)
    # This is a basic implementation
    echo "⚠️  Manual step required: Remove peer with public key $client_public from server"
    echo "   Use: wg set wg0 peer $client_public remove"
    
    echo "✅ Client '$client_name' removed"
}

remove_client "$@"
