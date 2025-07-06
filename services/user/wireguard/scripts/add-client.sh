#!/bin/bash
# WireGuard Client Management Script
# Part of CLINIC homelab infrastructure

set -euo pipefail

WG_DIR="${WG_DIR:-/etc/wireguard}"
VPN_SUBNET="${VPN_SUBNET:-10.8.0.0/24}"
WG_SERVER_ENDPOINT="${WG_SERVER_ENDPOINT:-$(curl -s ipinfo.io/ip):51820}"

add_client() {
    local client_name="$1"
    
    if [[ -z "$client_name" ]]; then
        echo "Usage: $0 <client-name>"
        exit 1
    fi
    
    # Validate client name
    if [[ ! "$client_name" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        echo "Error: Client name must contain only letters, numbers, hyphens, and underscores"
        exit 1
    fi
    
    # Check if client already exists
    if [[ -f "$WG_DIR/clients/${client_name}.conf" ]]; then
        echo "Error: Client '$client_name' already exists"
        exit 1
    fi
    
    # Get next available IP
    local client_ip
    client_ip=$(get_next_client_ip)
    
    # Generate client keys
    local client_private
    local client_public
    client_private=$(wg genkey)
    client_public=$(echo "$client_private" | wg pubkey)
    
    # Read server keys
    local server_public
    local preshared_key
    server_public=$(cat "$WG_DIR/wg0-server.public")
    preshared_key=$(cat "$WG_DIR/wg0-preshared.key")
    
    # Generate client configuration
    mkdir -p "$WG_DIR/clients"
    cat > "$WG_DIR/clients/${client_name}.conf" <<CLIENTEOF
[Interface]
PrivateKey = $client_private
Address = $client_ip/32
DNS = ${WG_CLIENT_DNS:-8.8.8.8}

[Peer]
PublicKey = $server_public
PresharedKey = $preshared_key
AllowedIPs = 0.0.0.0/0
Endpoint = $WG_SERVER_ENDPOINT
PersistentKeepalive = 25
CLIENTEOF
    
    # Add peer to server configuration
    cat >> "$WG_DIR/wg0.conf" <<SERVEREOF

# Client: $client_name
[Peer]
PublicKey = $client_public
PresharedKey = $preshared_key
AllowedIPs = $client_ip/32
SERVEREOF
    
    echo "✅ Client '$client_name' added successfully"
    echo "📄 Configuration: $WG_DIR/clients/${client_name}.conf"
    echo "📱 To generate QR code: qrencode -t ansiutf8 < $WG_DIR/clients/${client_name}.conf"
    
    # Reload WireGuard if running
    if systemctl is-active wg-quick@wg0 >/dev/null 2>&1; then
        systemctl reload wg-quick@wg0 || true
    fi
}

get_next_client_ip() {
    local base_ip="${VPN_SUBNET%/*}"
    local base="${base_ip%.*}"
    local used_ips=()
    
    # Extract used IPs from existing client configs
    if [[ -d "$WG_DIR/clients" ]]; then
        while IFS= read -r ip; do
            used_ips+=("$ip")
        done < <(grep -h "Address = " "$WG_DIR/clients"/*.conf 2>/dev/null | awk '{print $3}' | cut -d'/' -f1 || true)
    fi
    
    # Find next available IP (starting from .2, .1 is server)
    for i in $(seq 2 254); do
        local test_ip="${base}.${i}"
        local found=false
        
        for used in "${used_ips[@]}"; do
            if [[ "$used" == "$test_ip" ]]; then
                found=true
                break
            fi
        done
        
        if ! $found; then
            echo "$test_ip"
            return 0
        fi
    done
    
    echo "Error: No available IP addresses in subnet $VPN_SUBNET" >&2
    exit 1
}

add_client "$@"
