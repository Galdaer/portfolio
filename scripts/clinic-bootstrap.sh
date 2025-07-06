#!/usr/bin/env bash
# clinic-bootstrap.sh version 1.0.0
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/galdaer/intelluxe
# Last Revised: 2025-07-05
#
# Robust, extensible, and persistent bootstrapper for self-hosted Docker stacks.
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
#
#──────────────────────────────────────────────────────────────────────────────
# Core Features:
#   - Dynamic service management via configuration files (services/user/)
#   - Interactive and non-interactive operation (supports headless automation)
#   - Configurable firewall restrictions for service access control (LAN/VPN only)
#   - Automated backup, restore, versioning, and health checks
#   - Optional automatic self-update from GitHub
#   - Extensive logging, QR code generation, and summary documentation
#   - SELinux, custom UID/GID, and environment override support
#
# Requirements: Docker, socat, iptables/ufw, curl, ss, lsof, jq
# Optional:     WireGuard (for VPN), mail (for alerts), qrencode (for QR codes), shellcheck (for lint)
#
# ── Service Architecture ──────────────────────────────────────────────────────
# This script uses a dynamic service discovery system:
#
# 🎯 Services (services/user/):
#     - Any Docker service can be added via configuration files
#     - Services are automatically discovered from .conf files in services/ directories
#     - Services are discovered and managed automatically
#
# 🌐 Domain Support:
#     - Local development (no domain)
#     - Dynamic DNS (DuckDNS, etc.)
#     - Local DNS with hosts file
#     - VPN-only with domain routing
#
# 🔒 Security Features:
#     - Configurable service access restrictions
#     - Support: UFW and iptables, LAN/VPN subnet detection
#     - Options: --restrict-all-services, --open-all-services
#
# Services are detected and managed dynamically from configuration files.
#
# Tested on: Pop!_OS 22.04 LTS
#
# How to update this script:
#   Run: sudo ./clinic-bootstrap.sh --self-update
#
# Contact / Support:
#   - Issues: https://github.com/Galdaer/Self-hosting-and-networking/issues
#   - Author: Justin Sue (@Galdaer)
#
# For detailed usage, run: ./clinic-bootstrap.sh --help

set -euo pipefail

SCRIPT_VERSION="1.0.0"
# Self-update URL for automatic updates feature
SELF_UPDATE_URL="https://raw.githubusercontent.com/Galdaer/Self-hosting-and-networking/main/scripts/clinic-bootstrap.sh"
DEFAULT_UID=1000
DEFAULT_GID=1000

# ----------------- Configuration -----------------
: "${CFG_ROOT:=/opt/intelluxe/clinic-stack}"
: "${MEDIA_ROOT:=/media/homelab}"
: "${CFG_UID:=$DEFAULT_UID}"
: "${CFG_GID:=$DEFAULT_GID}"

CONFIG_FILE="${CFG_ROOT}/.clinic-bootstrap.conf"
BACKUP_DIR="${CFG_ROOT}/backups"
LOG_DIR="${CFG_ROOT}/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/clinic-bootstrap.log"

# Summary file for service documentation
SUMMARY_FILE="${CFG_ROOT}/SUMMARY.md"
COMPOSE_FILE="${CFG_ROOT}/docker-compose.yml"
RUNTIME_REPO_DIR="${RUNTIME_REPO_DIR:-/opt/intelluxe/infra-runtime/intelluxe}"
QR_DIR="${CFG_ROOT}/qrcodes"
WG_DIR="/etc/wireguard"
WG_KEYS_ENV="/etc/wireguard/wg-keys.env"
WG_CLIENTS_DIR="/etc/wireguard/clients"
MEDIA_BASE_PATH="${MEDIA_BASE_PATH:-/media/homelab}"
MERGERFS_POOL_NAME="${MERGERFS_POOL_NAME:-Media}"
MERGERFS_DISK_PREFIX="${MERGERFS_DISK_PREFIX:-/opt/intelluxe/storage/disk}"
DRY_RUN=false
DEBUG=${DEBUG:-false}
NON_INTERACTIVE=${NON_INTERACTIVE:-false}
FORCE_DEFAULTS=${FORCE_DEFAULTS:-false}
VALIDATE_ONLY=${VALIDATE_ONLY:-false}
EMAIL_ALERT_ENABLED=${EMAIL_ALERT_ENABLED:-false}
EMAIL_ALERT_ADDR=${EMAIL_ALERT_ADDR:-""}
RESTORE_BACKUP_FILE=${RESTORE_BACKUP_FILE:-""}
RESET_WG_KEYS=${RESET_WG_KEYS:-false}
WG_DOWN=${WG_DOWN:-false}
STOP_SERVICE="${STOP_SERVICE:-}"
SKIP_DOCKER_CHECK="${SKIP_DOCKER_CHECK:-false}"

# Network configuration
DOCKER_NETWORK_NAME="${DOCKER_NETWORK_NAME:-intelluxe-net}"
DOCKER_NETWORK_SUBNET="${DOCKER_NETWORK_SUBNET:-172.20.0.0/16}"
LAN_SUBNET="${LAN_SUBNET:-192.168.0.0/16}"

# Default container IP assignments - these will be used when services are added
WG_CONTAINER_IP="${WG_CONTAINER_IP:-172.20.0.2}"
TRAEFIK_CONTAINER_IP="${TRAEFIK_CONTAINER_IP:-172.20.0.4}"
PORTAINER_CONTAINER_IP="${PORTAINER_CONTAINER_IP:-172.20.0.8}"
# <SERVICE_IPS>

# Service configuration
WG_CLIENT_DNS="${WG_CLIENT_DNS:-8.8.8.8}"
DNS_FALLBACK="${DNS_FALLBACK:-1.1.1.1}"
BACKUP_RETENTION="${BACKUP_RETENTION:-10}"
MEDIA_SUBDIR="${MEDIA_SUBDIR:-Media}"

# Dynamic service-specific configuration (set during service setup)
# Service-specific configurations are now handled in individual service .conf files

# Container-specific UIDs can be defined in service configuration files
# Services that require specific UIDs/GIDs should define them in their .conf files

# VPN subnet for firewall rules (matches client IP allocation in get_next_available_ip)
VPN_SUBNET="${VPN_SUBNET:-10.8.0.0/24}"
VPN_SUBNET_BASE="${VPN_SUBNET_BASE:-10.8.0}"

# Firewall restriction configuration
FIREWALL_RESTRICT_MODE="ask" # "ask", "restrict", "open"
RESTRICTED_SERVICES=()

# Vaultwarden integration
VAULTWARDEN_URL="${VAULTWARDEN_URL:-http://localhost:8081}"
VAULTWARDEN_TOKEN="${VAULTWARDEN_TOKEN:-}"
STORE_WG_IN_VAULT="${STORE_WG_IN_VAULT:-false}"

# Container port configuration array
declare -A CONTAINER_PORTS

# Default variable initializations to avoid unset errors
: "${ACTION_FLAG:=}"
: "${ACTION_CONTAINER:=}"
: "${reply:=}"
: "${ans:=}"
: "${choice:=}"
: "${dup_choice:=}"
: "${clientname:=}"
: "${clientdir:=}"
: "${client_ip:=}"
: "${client_dns:=}"
: "${server_pub:=}"
: "${server_endpoint:=}"
: "${preshared:=}"
: "${delname:=}"

# Pre-parse arguments for flags needed before full parsing
for arg in "$@"; do
    case "$arg" in
        --skip-docker-check|--skip-docker-check=*)
            SKIP_DOCKER_CHECK=true
            break
            ;;
    esac
done

# --- Ensure Docker is installed and running early ---
if [[ "$SKIP_DOCKER_CHECK" != true ]]; then
    if ! command -v docker &>/dev/null; then
        echo "Error: Docker is not installed. Please install Docker and try again."
        exit 127
    fi
    if ! docker info >/dev/null 2>&1; then
        echo "Error: Docker daemon is not running. Start it with 'sudo systemctl start docker' and try again."
        exit 128
    fi
fi

set -uo pipefail

# ----------------- Lockfile: Prevent concurrent runs -----------------
# Use user-writable location instead of /var/lock (which requires root)
LOCK_FILE="${HOME}/.cache/clinic-bootstrap.lock"
mkdir -p "$(dirname "$LOCK_FILE")"
exec 200>"$LOCK_FILE"
flock -n 200 || {
	echo "Another instance of clinic-bootstrap.sh is running. Exiting."
	exit 1
}

# ----------------- Banner -----------------
print_banner() {
	cat <<BANNER
─────────────────────────────────────────────────────────────
  Robust Docker Homelab Bootstrapper    v${SCRIPT_VERSION}
  https://github.com/Galdaer/Self-hosting-and-networking
─────────────────────────────────────────────────────────────
BANNER
}

# --- VPN Network Configuration ---

# --- Container and Domain Configuration Defaults ---
# Traefik domain configuration
TRAEFIK_DOMAIN_MODE="${TRAEFIK_DOMAIN_MODE:-local}" # local|ddns|hostfile
TRAEFIK_DOMAIN_NAME="${TRAEFIK_DOMAIN_NAME:-}"
TRAEFIK_ACME_EMAIL="${TRAEFIK_ACME_EMAIL:-}"

# Service domain routing is now handled dynamically per service
# Individual services can define supports_domain_routing=true in their .conf files

# --- Dynamic Path: Source clinic-lib.sh ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"

# --- Load Universal Service Runner ---
# shellcheck source=scripts/universal-service-runner.sh
source "${SCRIPT_DIR}/universal-service-runner.sh"

# Get server IP for services that need it
get_server_ip() {
    # Try to get the main network interface IP
    local server_ip
    server_ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+' | head -n1)
    if [[ -z "$server_ip" ]]; then
        # Fallback to hostname -I
        server_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    if [[ -z "$server_ip" ]]; then
        # Last resort fallback
        server_ip="localhost"
    fi
    echo "$server_ip"
}

# Validate LAN subnet after sourcing helper functions
if ! validate_cidr "$LAN_SUBNET"; then
    die "Invalid LAN_SUBNET '$LAN_SUBNET'. Must be CIDR notation." 1
fi

# --- Bootstrap-specific cleanup function ---
script_specific_cleanup() {
    local exit_code="$1"

    log "Bootstrap-specific cleanup running (exit code: $exit_code)..."

    # Ensure any running docker operations are cleaned up gracefully
    # This is particularly important if containers were being started/stopped
    if [[ -n "${SELECTED_CONTAINERS:-}" ]]; then
        for container in "${SELECTED_CONTAINERS[@]}"; do
            if docker ps -q --filter "name=$container" >/dev/null 2>&1; then
                log "Container $container still running - cleanup will leave it as-is"
            fi
        done
    fi

    # Log the final configuration state for debugging
    if [[ -n "${CONFIG_FILE:-}" ]] && [[ -f "${CONFIG_FILE}" ]]; then
        log "Configuration file preserved at: $CONFIG_FILE"
    fi

    # Log any important bootstrap-specific state
    log "Bootstrap cleanup completed successfully"

    return 0
}

# Save current configuration state
save_config() {
    log "Saving configuration to $CONFIG_FILE..."
    
    # Create config directory if needed
    mkdir -p "$(dirname "$CONFIG_FILE")"
    
    # Write configuration with timestamp
    cat > "$CONFIG_FILE" << EOF
# CLINIC Bootstrap Configuration
# Generated: $(date)
# Version: $SCRIPT_VERSION

# Core paths
CFG_ROOT="$CFG_ROOT"
MEDIA_ROOT="$MEDIA_ROOT"
CFG_UID="$CFG_UID"
CFG_GID="$CFG_GID"

# Selected services
SELECTED_CONTAINERS=(${SELECTED_CONTAINERS[@]})

# Network configuration
DOCKER_NETWORK_NAME="$DOCKER_NETWORK_NAME"
DOCKER_NETWORK_SUBNET="$DOCKER_NETWORK_SUBNET"
LAN_SUBNET="$LAN_SUBNET"
VPN_SUBNET="$VPN_SUBNET"
VPN_SUBNET_BASE="$VPN_SUBNET_BASE"

# DNS configuration
WG_CLIENT_DNS="$WG_CLIENT_DNS"
DNS_FALLBACK="$DNS_FALLBACK"

# Security configuration
FIREWALL_RESTRICT_MODE="$FIREWALL_RESTRICT_MODE"
RESTRICTED_SERVICES=(${RESTRICTED_SERVICES[@]})

# Traefik configuration
TRAEFIK_DOMAIN_MODE="$TRAEFIK_DOMAIN_MODE"
TRAEFIK_DOMAIN_NAME="$TRAEFIK_DOMAIN_NAME"
TRAEFIK_ACME_EMAIL="$TRAEFIK_ACME_EMAIL"

# Media drive configuration
MEDIA_DRIVES_ENABLED="${MEDIA_DRIVES_ENABLED:-false}"
MEDIA_MOUNT_MODE="${MEDIA_MOUNT_MODE:-mergerfs}"
EOF

    # Save media drive UUIDs
    for i in {1..10}; do
        local var_name="MEDIA_DISK${i}_UUID"
        if [[ -n "${!var_name:-}" ]]; then
            echo "${var_name}=\"${!var_name}\"" >> "$CONFIG_FILE"
        fi
    done

    # Save custom port mappings
    echo "" >> "$CONFIG_FILE"
    echo "# Custom port mappings" >> "$CONFIG_FILE"
    for svc in "${!CONTAINER_PORTS[@]}"; do
        local sanitized
        sanitized=$(echo "$svc" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
        echo "${sanitized}_PORT=\"${CONTAINER_PORTS[$svc]}\"" >> "$CONFIG_FILE"
    done

    # Save container IP assignments
    echo "" >> "$CONFIG_FILE"
    echo "# Container IP assignments" >> "$CONFIG_FILE"
    for container in "${ALL_CONTAINERS[@]}"; do
        local sanitized="${container//-/_}"
        local ip_var="${sanitized^^}_CONTAINER_IP"
        if [[ -n "${!ip_var:-}" ]]; then
            echo "${ip_var}=\"${!ip_var}\"" >> "$CONFIG_FILE"
        fi
    done

    # WireGuard configuration
    {
        echo ""
        echo "# WireGuard configuration"
        echo "WG_DIR=\"$WG_DIR\""
        echo "STORE_WG_IN_VAULT=\"$STORE_WG_IN_VAULT\""
    } >> "$CONFIG_FILE"

    # Vaultwarden configuration
    {
        echo ""
        echo "# Vaultwarden configuration"
        echo "VAULTWARDEN_URL=\"$VAULTWARDEN_URL\""
        [[ -n "${VAULTWARDEN_TOKEN:-}" ]] && echo "VAULTWARDEN_TOKEN=\"$VAULTWARDEN_TOKEN\""
    } >> "$CONFIG_FILE"

    chmod 600 "$CONFIG_FILE"
    set_ownership "$CONFIG_FILE"
    
    log "Configuration saved successfully"
    return 0
}

trap cleanup SIGINT SIGTERM ERR EXIT

SERVICE_LIST=$(for f in "${SCRIPT_DIR%/scripts}/services/user"/*.conf; do
    [ -e "$f" ] || continue
    basename "$f" .conf
done | paste -sd ',' -)

USAGE="Usage: $0 [options]

Bootstrap self-hosted Docker Intelluxe environment.

Options:
  --no-color                    Disable color output
  --debug                       Enable debug logging
  --dry-run                     Show what would be done without making changes
  --validate                    Validate configuration and dependencies only
  --help                        Show this help and exit
  --version                     Show version and exit
  --reset-wg-keys               Regenerate WireGuard server keys and update clients
  --stop-service NAME           Stop the specified service or container
  --wg-down                     Bring down the WireGuard interface and exit (deprecated)
  --skip-docker-check           Skip Docker availability checks (useful in CI)

Firewall Security Options:
  --restrict-all-services       Restrict all services to LAN + VPN access only
  --open-all-services          Allow all services to be accessed from anywhere (default)
  --restrict-services SERVICES  Restrict specific services (comma-separated list)
                               Valid services: ${SERVICE_LIST}

Examples:
  $0                                    # Interactive setup with security prompts
  $0 --restrict-all-services           # Restrict all services to LAN + VPN
  $0 --restrict-services svc1,svc2     # Restrict only specific services
  $0 --open-all-services --dry-run     # Show what would be configured

Environment Variables:
    LAN_SUBNET                 CIDR for LAN firewall rules (default 192.168.0.0/16, must be valid)
    SKIP_DOCKER_CHECK          Set to true to bypass Docker checks (CI use)

Version: $SCRIPT_VERSION
"

# Parse standard/common flags (and --help)
parse_basic_flags "$@"

# Script-specific flags
while [[ $# -gt 0 ]]; do
	case "$1" in
	--restrict-all-services)
		FIREWALL_RESTRICT_MODE="restrict"
		shift
		;;
	--open-all-services)
		FIREWALL_RESTRICT_MODE="open"
		shift
		;;
        --restrict-services)
                FIREWALL_RESTRICT_MODE="custom"
                IFS=',' read -ra RESTRICTED_SERVICES <<<"$2"
                shift 2
                ;;
        --reset-wg-keys)
                RESET_WG_KEYS=true
                shift
                ;;
        --stop-service)
                STOP_SERVICE="$2"
                shift 2
                ;;
        --wg-down)
                WG_DOWN=true
                shift
                ;;
        --skip-docker-check)
                SKIP_DOCKER_CHECK=true
                shift
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

# ----------------- Dependency Checks and Auto-Install -----------------
auto_install_deps() {
	# Auto-install missing dependencies unless --validate-only
	local missing_deps=()
	local deps=(ip iptables docker socat curl ss wg-quick lsof jq stat less)

  # Add qrencode to required deps if WireGuard is selected
    if [[ " ${SELECTED_CONTAINERS[*]} " == *" wireguard "* ]]; then
        deps+=(qrencode)
        [[ "$STORE_WG_IN_VAULT" == "true" ]] && deps+=(vaultwarden-cli)
    fi

	for dep in "${deps[@]}"; do
		if ! command -v "$dep" &>/dev/null; then
			missing_deps+=("$dep")
		fi
	done

	if [[ ${#missing_deps[@]} -gt 0 ]]; then
		warn "Missing dependencies: ${missing_deps[*]}"

		if [[ "$VALIDATE_ONLY" == "true" ]]; then
			die "Dependencies missing. Install them and re-run: ${missing_deps[*]}" 25
		fi

		if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
			log "Auto-installing missing dependencies: ${missing_deps[*]}"
		else
			echo "Missing dependencies detected: ${missing_deps[*]}"
			if [[ -t 0 ]]; then
				read -rp "Install missing dependencies automatically? [Y/n]: " ans
			else
				log "Non-interactive mode detected. Defaulting to 'Yes'."
				ans="y"
			fi
			if [[ ! "${ans,,}" =~ ^(y|yes|)$ ]]; then
				die "Dependencies required. Please install: ${missing_deps[*]}" 25
			fi
		fi

		# Map dependencies to packages
		local packages=()
		for dep in "${missing_deps[@]}"; do
			case "$dep" in
			socat) packages+=("socat") ;;
			wg-quick) packages+=("wireguard-tools") ;;
			jq) packages+=("jq") ;;
			ss) packages+=("iproute2") ;;
			ip) packages+=("iproute2") ;;
			lsof) packages+=("lsof") ;;
			curl) packages+=("curl") ;;
			iptables) packages+=("iptables") ;;
			stat) packages+=("coreutils") ;;
			less) packages+=("less") ;;
			qrencode) packages+=("qrencode") ;;
			docker)
				warn "Docker installation requires special handling. Please install Docker manually."
				die "Visit https://docs.docker.com/engine/install/ for Docker installation instructions." 26
				;;
			esac
		done

		# Install packages
		if [[ ${#packages[@]} -gt 0 ]]; then
			# Remove duplicates
			mapfile -t unique_packages < <(printf "%s\n" "${packages[@]}" | sort -u)
			log "Installing packages: ${unique_packages[*]}"

			if [[ $DRY_RUN == true ]]; then
				log "[DRY-RUN] Would install packages: ${unique_packages[*]}"
			else
				for pkg in "${unique_packages[@]}"; do
					install_package "$pkg" || warn "Failed to install $pkg"
				done
			fi
		fi

		# Verify installation
		for dep in "${missing_deps[@]}"; do
			if [[ "$dep" != "docker" && ! "$DRY_RUN" == "true" ]]; then
				if ! command -v "$dep" &>/dev/null; then
					warn "Failed to install dependency: $dep"
				else
					log "Successfully installed: $dep"
				fi
			fi
		done
	fi
}

# ----------------- Traefik Integration Functions -----------------

# Generate Traefik labels for service domain routing
get_traefik_labels() {
    local service_name="$1"
    local service_port="$2"
    local labels=""
    
    # Check if this service supports domain routing
    local svc_file=""
    if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${service_name}.conf" ]]; then
        svc_file="${SCRIPT_DIR%/scripts}/services/user/${service_name}.conf"
    fi
    
    local supports_routing
    supports_routing=$(get_service_config_value "$svc_file" "supports_domain_routing")
    if [[ "$supports_routing" != "true" ]]; then
        return 0
    fi
    
    # Generate labels based on domain mode
    case "${TRAEFIK_DOMAIN_MODE:-local}" in
        "ddns"|"hostfile")
            if [[ -n "${TRAEFIK_DOMAIN_NAME:-}" ]]; then
                labels+="--label traefik.enable=true "
                labels+="--label traefik.http.routers.${service_name}.rule=Host(\`${service_name}.${TRAEFIK_DOMAIN_NAME}\`) "
                labels+="--label traefik.http.routers.${service_name}.entrypoints=websecure "
                labels+="--label traefik.http.routers.${service_name}.tls.certresolver=letsencrypt "
                labels+="--label traefik.http.services.${service_name}.loadbalancer.server.port=${service_port} "
                
                # Add HTTP redirect for DDNS mode
                if [[ "${TRAEFIK_DOMAIN_MODE}" == "ddns" ]]; then
                    labels+="--label traefik.http.routers.${service_name}-insecure.rule=Host(\`${service_name}.${TRAEFIK_DOMAIN_NAME}\`) "
                    labels+="--label traefik.http.routers.${service_name}-insecure.entrypoints=web "
                    labels+="--label traefik.http.routers.${service_name}-insecure.middlewares=redirect-to-https "
                fi
            fi
            ;;
        "vpn-only")
            if [[ -n "${TRAEFIK_DOMAIN_NAME:-}" ]]; then
                labels+="--label traefik.enable=true "
                labels+="--label traefik.http.routers.${service_name}.rule=Host(\`${service_name}.${TRAEFIK_DOMAIN_NAME}\`) "
                labels+="--label traefik.http.routers.${service_name}.entrypoints=web "
                labels+="--label traefik.http.services.${service_name}.loadbalancer.server.port=${service_port} "
                # VPN-only mode uses HTTP since it's internal
            fi
            ;;
        "local"|*)
            # No Traefik labels for local mode - direct port access
            ;;
    esac
    
    echo "$labels"
}

# ----------------- Container Definitions -----------------
# <AUTOGEN-CONTAINER-DEFINITIONS-START>
declare -A CONTAINER_DESCRIPTIONS=(
        # <SERVICE_DESCRIPTIONS>
)
declare -A CONTAINER_PORTS=(
        # <SERVICE_PORTS>
)

# ----------------- Source Persistent Config -----------------
# shellcheck source=/opt/intelluxe/clinic-stack/.clinic-bootstrap.conf
if [[ -f "$CONFIG_FILE" ]]; then
	# Check if config file contains old problematic syntax and remove it
	if grep -q "CONTAINER_PORTS\[" "$CONFIG_FILE" 2>/dev/null; then
		warn "Found old config format in $CONFIG_FILE. Removing and will regenerate with new format."
		cp "$CONFIG_FILE" "${CONFIG_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
		rm -f "$CONFIG_FILE"
		log "Old config backed up and removed. Will regenerate with new format."
	elif [[ -f "$CONFIG_FILE" ]]; then
		# Only source if file exists and doesn't have problematic syntax
		# shellcheck source=/dev/null
		source "$CONFIG_FILE"



# User port overrides
# The following comments preserve line numbers for bats tests.
#
# <USER_PORT_ENV_OVERRIDES>

                # Apply any saved ports for user-defined services
                for svc in "${!CONTAINER_PORTS[@]}"; do
                        sanitized="${svc//-/_}"
                        var="${sanitized^^}_PORT"
                        if [[ -n "${!var:-}" ]]; then
                                CONTAINER_PORTS[$svc]="${!var}"
                        fi
                done
# </USER_PORT_ENV_OVERRIDES>

                # Docker network and DNS settings are persisted via self-assignments
                # in save_config() and restored automatically when this file is sourced
        
                # Security/firewall configuration is already restored when sourcing the config file
                # No additional assignment needed - variables are set during source operation
        fi
fi

# Check if config file exists after potential cleanup
if [[ ! -f "$CONFIG_FILE" ]]; then
	log "Config file $CONFIG_FILE not found. This is normal on first run; it will be created after setup."
fi

# Show all port bindings for CLI
show_ports() {
    echo "Current port bindings:"
    printf "%-12s %-8s %-6s %-8s\n" "Service" "HostPort" "Proto" "ContainerPort"
    for c in "${!CONTAINER_PORTS[@]}"; do
        proto="tcp"
        cport=""
        
        # Check service config for port and protocol information
        local svc_file=""
        if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${c}.conf" ]]; then
            svc_file="${SCRIPT_DIR%/scripts}/services/user/${c}.conf"
        fi
        
        if [[ -n "$svc_file" ]]; then
            cport=$(get_service_config_value "$svc_file" "port")
            # Check if service uses UDP (typically VPN services)
            if [[ "$c" == "wireguard" ]] || grep -q "udp" "$svc_file" 2>/dev/null; then
                proto="udp"
            fi
        fi
        
        printf "%-12s %-8s %-6s %-8s\n" "$c" "${CONTAINER_PORTS[$c]}" "$proto" "${cport:-N/A}"
    done
    
    # Display service-specific port notes from configuration files
    for c in "${!CONTAINER_PORTS[@]}"; do
        local svc_file="${SCRIPT_DIR%/scripts}/services/user/$c.conf"
        if [[ -f "$svc_file" ]]; then
            local port_notes
            port_notes=$(get_service_config_value "$svc_file" "port_notes")
            if [[ -n "$port_notes" ]]; then
                echo "Note: $port_notes"
            fi
        fi
    done
}
# Reset ports to defaults for CLI
# <AUTOGEN-RESET-PORTS-START>
reset_ports() {
        confdir="${SCRIPT_DIR%/scripts}/services/user"
        for conf in "$confdir"/*.conf; do
                [ -f "$conf" ] || continue
                svc=$(basename "$conf" .conf)
                port=$(grep -E '^port=' "$conf" | cut -d= -f2-)
                [[ -n "$port" ]] && CONTAINER_PORTS[$svc]="$port"
        done
        # <SERVICE_RESET_PORTS>
        log "Ports reset to defaults."
}
# <AUTOGEN-RESET-PORTS-END>

# <SERVICE_SET>
# Dynamic service discovery from config files
ALL_CONTAINERS=()
confdir="${SCRIPT_DIR%/scripts}/services/user"

# First, discover services from .conf files
for conf in "$confdir"/*.conf; do
        [ -f "$conf" ] || continue
        svc=$(basename "$conf" .conf)
        desc=$(grep -E '^description=' "$conf" 2>/dev/null | cut -d= -f2- || echo "")
        port=$(grep -E '^port=' "$conf" 2>/dev/null | cut -d= -f2- || echo "")
        [[ -n "$port" ]] && CONTAINER_PORTS[$svc]="$port"
        if grep -q '^image=' "$conf" 2>/dev/null; then
                if [[ " ${ALL_CONTAINERS[*]} " != *" $svc "* ]]; then
                        ALL_CONTAINERS+=("$svc")
                fi
                [[ -n "$desc" ]] && CONTAINER_DESCRIPTIONS[$svc]="$desc"
        fi
done

# Also discover services from nested directories
for service_dir in "$confdir"/*; do
        [ -d "$service_dir" ] || continue
        svc=$(basename "$service_dir")
        conf="$service_dir/$svc.conf"
        
        # Skip if already processed from flat .conf files
        [[ " ${ALL_CONTAINERS[*]} " == *" $svc "* ]] && continue
        
        if [[ -f "$conf" ]]; then
                desc=$(grep -E '^description=' "$conf" 2>/dev/null | cut -d= -f2- || echo "")
                port=$(grep -E '^port=' "$conf" 2>/dev/null | cut -d= -f2- || echo "")
                [[ -n "$port" ]] && CONTAINER_PORTS[$svc]="$port"
                if grep -q '^image=' "$conf" 2>/dev/null; then
                        ALL_CONTAINERS+=("$svc")
                        [[ -n "$desc" ]] && CONTAINER_DESCRIPTIONS[$svc]="$desc"
                fi
        fi
done



SELECTED_CONTAINERS=()
# <AUTOGEN-CONTAINER-DEFINITIONS-END>

# ----------------- Service Configuration Parser -----------------
parse_service_config() {
    local svc_file="$1"
    local config=()
    
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        config+=("$key=$value")
    done < "$svc_file"
    
    printf '%s\n' "${config[@]}"
}

get_service_config_value() {
    local svc_file="$1"
    local key="$2"
    local default="${3:-}"
    
    if [[ -f "$svc_file" ]]; then
        local value
        value=$(grep -E "^${key}=" "$svc_file" | head -n1 | cut -d= -f2- || echo "$default")
        # Expand environment variables if the value contains $
        # Avoid expanding volume mount paths (typically key=value format with host:container paths)
        if [[ "$value" == *'$'* ]]; then
            if [[ "$key" == "volumes" && "$value" == *':'* && "$value" == *'/'* ]]; then
                # This is likely a volume mount path, don't expand
                echo "$value"
            else
                # Safe to expand environment variables, but handle unbound variables gracefully
                set +u  # Temporarily allow unbound variables
                expanded_value=$(eval echo "\"$value\"" 2>/dev/null || echo "$value")
                set -u  # Re-enable unbound variable checking
                echo "$expanded_value"
            fi
        else
            echo "$value"
        fi
    else
        echo "$default"
    fi
}

# ----------------- Generic Container Runner -----------------
# <AUTOGEN-ENSURE-CONTAINER-START>
ensure_container_running() {
    local container_name="$1"
    local svc_file=""
    
    log "Ensuring service $container_name is running..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY-RUN] Would ensure service $container_name is running."
        return 0
    fi

    # Find service configuration file
    if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container_name}/${container_name}.conf" ]]; then
        svc_file="${SCRIPT_DIR%/scripts}/services/user/${container_name}/${container_name}.conf"
    elif [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container_name}.conf" ]]; then
        svc_file="${SCRIPT_DIR%/scripts}/services/user/${container_name}.conf"
    else
        warn "No service configuration found for: $container_name"
        return 1
    fi

    # Check service type to determine how to run it
    local service_type
    service_type=$(get_service_config_value "$svc_file" "service_type" "docker")
    
    case "$service_type" in
        "systemd")
            log "🔧 Running systemd service: $container_name"
            run_systemd_service "$container_name" "$svc_file"
            ;;
        "docker"|*)
            # Universal configuration mode - use universal service runner
            log "🌟 Using universal configuration mode for $container_name"
            
            # Remove existing container
            docker rm -f "$container_name" >/dev/null 2>&1 || true
            
            # Run with universal service runner
            run_universal_service "$container_name" "$svc_file"
            ;;
    esac
}

# Function to handle systemd services
run_systemd_service() {
    local service_name="$1"
    local svc_file="$2"
    
    # For systemd services, we need to enable and start the systemd service
    local systemd_service_name
    systemd_service_name=$(get_service_config_value "$svc_file" "systemd_service_name" "${service_name}.service")
    
    log "Starting systemd service: $systemd_service_name"
    
    # Enable the service to start on boot
    if ! systemctl enable "$systemd_service_name" 2>/dev/null; then
        warn "Failed to enable systemd service: $systemd_service_name"
        return 1
    fi
    
    # Start the service
    if ! systemctl start "$systemd_service_name" 2>/dev/null; then
        warn "Failed to start systemd service: $systemd_service_name"
        return 1
    fi
    
    # Check if the service is running
    if systemctl is-active --quiet "$systemd_service_name"; then
        log "✅ Systemd service $systemd_service_name is running"
        return 0
    else
        warn "❌ Systemd service $systemd_service_name failed to start"
        return 1
    fi
}

# Remove all service-specific setup functions
# Add a generic environment variable setup function
setup_service_env_vars() {
    local container_name="$1"
    local svc_file=""
    if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container_name}.conf" ]]; then
        svc_file="${SCRIPT_DIR%/scripts}/services/user/${container_name}.conf"
    else
        return 0
    fi
    local envs
    envs=$(get_service_config_value "$svc_file" "env")
    [[ -z "$envs" ]] && return 0
    IFS=';' read -ra env_array <<< "$envs"
    for env in "${env_array[@]}"; do
        [[ -z "$env" ]] && continue
        local var_name var_value
        var_name="${env%%=*}"
        var_value="${env#*=}"
        # Compute dynamic values for common variables if needed
        case "$var_name" in
            ADVERTISE_IP)
                # Use generic advertise IP logic
                if [[ -n "${TRAEFIK_DOMAIN_MODE:-}" && "${TRAEFIK_DOMAIN_MODE}" != "local" && -n "${TRAEFIK_DOMAIN_NAME:-}" ]]; then
                    export "${var_name}"="https://${container_name}.${TRAEFIK_DOMAIN_NAME}/"
                else
                    local server_ip
                    server_ip=$(get_server_ip)
                    export "${var_name}"="http://${server_ip}:${CONTAINER_PORTS[$container_name]:-}"/
                fi
                ;;
            HOSTNAME)
                if [[ -n "${TRAEFIK_DOMAIN_MODE:-}" && "${TRAEFIK_DOMAIN_MODE}" != "local" && -n "${TRAEFIK_DOMAIN_NAME:-}" ]]; then
                    export "${var_name}"="${container_name}.${TRAEFIK_DOMAIN_NAME}"
                else
                    export "${var_name}"="${container_name}-server"
                fi
                ;;
            ALLOWED_NETWORKS)
                export "${var_name}"="${LAN_SUBNET},${VPN_SUBNET},${DOCKER_NETWORK_SUBNET}"
                ;;
            *)
                # Expand value with env var substitution
                eval "export \"${var_name}\"=\"$var_value\""
                ;;
        esac
    done
}

# ----------------- Data Drive Configuration Functions -----------------
detect_available_drives() {
	# Detect available storage drives and return their info
	local drives=()

	# Find drives with ext4, ntfs, or unformatted partitions
	while IFS= read -r line; do
		if [[ -n "$line" ]]; then
			drives+=("$line")
		fi
	done < <(lsblk -no NAME,SIZE,FSTYPE,UUID,MOUNTPOINT | awk '
		BEGIN { print "# Available storage drives:" }
		$3 ~ /^(ext4|ntfs|)$/ && $1 !~ /^(loop|sr|dm-)/ && $2 ~ /[GT]B?$/ && length($1) <= 4 {
			if ($4 == "") { uuid = "UNFORMATTED" } else { uuid = $4 }
			if ($5 == "") { mount = "UNMOUNTED" } else { mount = $5 }
			printf "/dev/%s (%s, %s, %s, %s)\n", $1, $2, $3 ? $3 : "unformatted", uuid, mount
		}')

	if [[ ${#drives[@]} -gt 1 ]]; then # More than just the header
		printf '%s\n' "${drives[@]}"
		return 0
	else
		echo "# No suitable storage drives detected"
		return 1
	fi
}

get_drive_uuid() {
	# Get UUID for a device path
	local device="$1"
	blkid -o value -s UUID "$device" 2>/dev/null || echo ""
}

prompt_for_media_drive() {
	# Prompt for a media drive UUID with validation
	local var_name="$1" prompt_text="$2" current_uuid="${3:-}"

	if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
		eval "$var_name='$current_uuid'"
		return
	fi

	while true; do
		if [[ -n "$current_uuid" ]]; then
			if [[ -t 0 ]]; then
				read -rp "$prompt_text (current: $current_uuid, press Enter to keep): " new_uuid
			else
				log "Non-interactive mode detected. Keeping current UUID."
				new_uuid="$current_uuid"
			fi
			new_uuid="${new_uuid/#\~/$HOME}" # Expand ~ to home directory
		else
			if [[ -t 0 ]]; then
				read -rp "$prompt_text (leave empty to skip): " new_uuid
			else
				log "Non-interactive mode detected. Skipping UUID input."
				new_uuid=""
			fi
		fi

		if [[ -z "$new_uuid" ]]; then
			eval "$var_name=''"
			return
		fi

		if validate_uuid "$new_uuid"; then
			eval "$var_name='$new_uuid'"
			log "✅ UUID $new_uuid validated successfully"
			return
		else
			warn "UUID '$new_uuid' not found on system. Please check and try again."
			echo "Available drives:"
			detect_available_drives
			echo ""
		fi
       done
}

reset_wireguard_keys() {
        if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
                read -rp "Reset WireGuard server keys? Existing client configs will be invalid. [y/N]: " ans
                [[ "${ans,,}" =~ ^(y|yes)$ ]] || return 0
        fi

        backup_wireguard || warn "Failed to back up existing WireGuard config"

        umask 077
        WG_SERVER_PRIVATE_KEY=$(wg genkey)
        WG_SERVER_PUBLIC_KEY=$(echo "$WG_SERVER_PRIVATE_KEY" | wg pubkey)
        WG_PRESHARED_KEY=$(wg genpsk)
        {
                echo "WG_SERVER_PRIVATE_KEY=$WG_SERVER_PRIVATE_KEY"
                echo "WG_SERVER_PUBLIC_KEY=$WG_SERVER_PUBLIC_KEY"
                echo "WG_PRESHARED_KEY=$WG_PRESHARED_KEY"
        } >"$WG_KEYS_ENV"
        chmod 0600 "$WG_KEYS_ENV"
        set_ownership "$WG_KEYS_ENV"
        log "WireGuard server keys reset in $WG_KEYS_ENV"

        for conf in "$WG_CLIENTS_DIR"/*/*.conf; do
                [[ -f "$conf" ]] || continue
                sed -i "s|^PublicKey = .*|PublicKey = $WG_SERVER_PUBLIC_KEY|" "$conf"
                sed -i "s|^PresharedKey = .*|PresharedKey = $WG_PRESHARED_KEY|" "$conf"
                clientdir="$(dirname "$conf")"
                clientname="$(basename "$conf" .conf)"
                generate_wg_qr "$clientdir" "$clientname"
        done
}

stop_wireguard() {
        local iface="wg0"
        log "Bringing down $iface and removing firewall rules..."
        run systemctl stop "wg-quick@$iface" || true
        run ip link set dev "$iface" down || true
        run iptables -D FORWARD -i "$iface" -j ACCEPT || true
        run iptables -D FORWARD -o "$iface" -j ACCEPT || true
        run iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE || true
        if ss -lun | grep -q ':51820'; then
                warn "$iface UDP 51820 still listening!"
        else
                ok "$iface UDP 51820 listener is down."
        fi
        ok "$iface brought down and firewall rules removed."
}

stop_service() {
        local svc="$1"
        log "Stopping service $svc..."
        case "$svc" in
        wireguard)
                stop_wireguard
                run docker stop wireguard >/dev/null 2>&1 || true
                ;;
        *)
                if docker ps -a --format '{{.Names}}' | grep -Fxq "$svc"; then
                        run docker stop "$svc" >/dev/null 2>&1 || true
                else
                        run systemctl stop "$svc" >/dev/null 2>&1 || true
                fi
                ;;
        esac
        ok "$svc stopped."
}

configure_media_drives() {
	# Interactive media drive configuration similar to port configuration
	log "Configuring media drives for mergerFS..."

	# Check if user has selected containers that would benefit from media drives
	local needs_media=false
	for container in "${SELECTED_CONTAINERS[@]}"; do
		# Check service configuration for media services
		local svc_file=""
		if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
			svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
		fi
		
		if [[ -n "$svc_file" ]]; then
			local desc
			desc=$(get_service_config_value "$svc_file" "description")
			local requires_media
			requires_media=$(get_service_config_value "$svc_file" "requires_media")
			
			# Check if service requires media or has media-related keywords
			if [[ "$requires_media" == "true" ]] || [[ "$desc" == *"media"* ]] || [[ "$desc" == *"healthcare data processing"* ]]; then
				needs_media=true
				break
			fi
		fi
	done

	if ! $needs_media; then
		if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
			log "No media services selected. Skipping media drive configuration in non-interactive mode."
			MEDIA_DRIVES_ENABLED="false"
			return
		else
			echo ""
			echo "No media services are currently selected."
			read -rp "Would you still like to configure media drives? [y/N]: " ans
			if [[ ! "${ans,,}" =~ ^(y|yes)$ ]]; then
				log "Skipping media drive configuration."
				MEDIA_DRIVES_ENABLED="false"
				return
			fi
		fi
	fi

	# Check if media drives are already configured
	local config_exists=false
	if [[ -f "$CONFIG_FILE" ]] && grep -q "MEDIA_DRIVES_ENABLED" "$CONFIG_FILE" 2>/dev/null; then
		config_exists=true
	fi

	if [[ "$config_exists" == "true" ]]; then
		if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
			echo ""
			echo "========================================"
			echo "      CURRENT MEDIA DRIVE CONFIG"
			echo "========================================"
			echo ""

			if [[ "${MEDIA_DRIVES_ENABLED:-false}" == "true" ]]; then
				echo "✅ Media drives currently enabled:"
				# Show all configured drives
				for ((i = 1; i <= 10; i++)); do
					local var_name="MEDIA_DISK${i}_UUID"
					local drive_uuid="${!var_name:-}"
					[[ -n "$drive_uuid" ]] && echo "   Disk $i: $drive_uuid"
				done
				echo "   Mount mode: ${MEDIA_MOUNT_MODE:-mergerfs}"
			else
				echo "❌ Media drives currently disabled"
			fi

			echo ""
			read -rp "Would you like to update media drive configuration? [y/N]: " ans
			if [[ ! "${ans,,}" =~ ^(y|yes)$ ]]; then
				log "Using existing media drive configuration."
				return
			fi
		else
			log "Using existing media drive configuration from $CONFIG_FILE"
			return
		fi
	fi

	# Show available drives
	echo ""
	echo "========================================"
	echo "       MEDIA DRIVE CONFIGURATION"
	echo "========================================"
	echo ""

	if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
		echo "📀 Detecting available storage drives..."
		echo ""

		if detect_available_drives; then
			echo ""
			echo "💡 Tips:"
			echo "   • Use 'lsblk -f' to see all drives with UUIDs"
			echo "   • Use 'blkid' to see detailed filesystem information"
			echo "   • ext4 format is recommended for best performance"
			echo ""
		fi

		# Ask if user wants to enable media drives
		read -rp "Enable media drive configuration? [Y/n]: " enable_media
		if [[ "${enable_media,,}" =~ ^(n|no)$ ]]; then
			log "Media drives disabled by user choice."
			MEDIA_DRIVES_ENABLED="false"
			return
		fi

		# Ask if user wants individual drive management
		echo ""
		echo "Configuration options:"
		echo "1) Quick setup  - Configure drives in bulk (recommended for new setups)"
		echo "2) Individual   - Manage drives one by one (recommended for existing setups)"
		echo ""
		read -rp "Choose configuration method [1-2] (press Enter for '1'): " config_method
		config_method="${config_method:-1}"

		if [[ "$config_method" == "2" ]]; then
			# Use individual drive management
			MEDIA_DRIVES_ENABLED="true"
			manage_drives_individually
			save_config || {
				fail "save_config failed (after individual drive management)"
				exit 1
			}
			return
		fi
	fi

	MEDIA_DRIVES_ENABLED="true"

	# Configure mount mode
	if ! $NON_INTERACTIVE; then
		echo ""
		echo "Mount mode options:"
		echo "1) mergerfs     - Pool multiple drives into single location (recommended for 2+ drives)"
		echo "2) independent  - Multiple drives mounted separately (Movies, TV, Music, etc.)"
		echo "3) single       - Use single drive mount"
		echo ""
		read -rp "Mount mode [1-3] (press Enter for '1'): " mode_choice
		mode_choice="${mode_choice:-1}"

		case "$mode_choice" in
		1) MEDIA_MOUNT_MODE="mergerfs" ;;
		2) MEDIA_MOUNT_MODE="independent" ;;
		3) MEDIA_MOUNT_MODE="single" ;;
		*) MEDIA_MOUNT_MODE="mergerfs" ;;
		esac
	else
		MEDIA_MOUNT_MODE="${MEDIA_MOUNT_MODE:-mergerfs}"
	fi

	log "Using mount mode: $MEDIA_MOUNT_MODE"

	# Configure drives based on mount mode
	if [[ "$MEDIA_MOUNT_MODE" == "single" ]]; then
		prompt_for_media_drive "MEDIA_DISK1_UUID" "Primary media drive UUID" "${MEDIA_DISK1_UUID:-}"
		MEDIA_DISK2_UUID=""
		MEDIA_DISK3_UUID=""
	elif [[ "$MEDIA_MOUNT_MODE" == "independent" ]]; then
		# Independent mode - ask how many drives and what purpose
		if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
			echo ""
			echo "Independent mode: Configure drives for separate mount points"
			echo "💡 Each drive will be mounted separately (e.g., /opt/intelluxe/data/Movies, /opt/intelluxe/data/TV)"
			echo ""

			local num_drives=2
			while true; do
				read -rp "Number of drives [2-10] (press Enter for '2'): " num_drives_input
				num_drives="${num_drives_input:-2}"

				if [[ "$num_drives" =~ ^[2-9]$|^10$ ]]; then
					break
				else
					warn "Please enter a number between 2 and 10"
				fi
			done

			log "Configuring $num_drives independent drives"
		else
			# Non-interactive: use existing configuration or default to 2
			local num_drives=2
			[[ -n "${MEDIA_DISK1_UUID:-}" ]] && num_drives=1
			[[ -n "${MEDIA_DISK2_UUID:-}" ]] && num_drives=2
			[[ -n "${MEDIA_DISK3_UUID:-}" ]] && num_drives=3
			# Count any additional drives from environment
			for i in {4..10}; do
				var_name="MEDIA_DISK${i}_UUID"
				if [[ -n "${!var_name:-}" ]]; then
					num_drives=$i
				fi
			done
		fi

		# Configure the drives with suggested purposes
		local drive_purposes=(
			    "${DRIVE_PURPOSE_1:-Movies}"
				"${DRIVE_PURPOSE_2:-TV Shows}"
				"${DRIVE_PURPOSE_3:-Music}"
				"${DRIVE_PURPOSE_4:-Photos}"
				"${DRIVE_PURPOSE_5:-Downloads}"
				"${DRIVE_PURPOSE_6:-Backups}"
				"${DRIVE_PURPOSE_7:-Archive}"
				"${DRIVE_PURPOSE_8:-Games}"
				"${DRIVE_PURPOSE_9:-Documents}"
				"${DRIVE_PURPOSE_10:-Other}"
				)
		for ((i = 1; i <= num_drives; i++)); do
			local var_name="MEDIA_DISK${i}_UUID"
			local current_value="${!var_name:-}"
			local purpose="${drive_purposes[$((i - 1))]:-Drive $i}"
			local prompt_text="$purpose drive UUID"

			if [[ $i -le 2 ]]; then
				prompt_for_media_drive "$var_name" "$prompt_text" "$current_value"
			else
				prompt_for_media_drive "$var_name" "$prompt_text (optional)" "$current_value"
			fi
		done

		# Clear any drives beyond the configured number
		for ((i = num_drives + 1; i <= 10; i++)); do
			local var_name="MEDIA_DISK${i}_UUID"
			eval "$var_name=''"
		done
	else
		# mergerfs mode - ask how many drives user wants to configure
		if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
			echo ""
			echo "How many drives would you like to configure for mergerFS?"
			echo "💡 You can configure 2-10 drives (mergerFS works best with 2+ drives)"
			echo ""

			local num_drives=2
			while true; do
				read -rp "Number of drives [2-10] (press Enter for '2'): " num_drives_input
				num_drives="${num_drives_input:-2}"

				if [[ "$num_drives" =~ ^[2-9]$|^10$ ]]; then
					break
				else
					warn "Please enter a number between 2 and 10"
				fi
			done

			log "Configuring $num_drives drives for mergerFS"
		else
			# Non-interactive: use existing configuration or default to 2
			local num_drives=2
			[[ -n "${MEDIA_DISK2_UUID:-}" ]] && num_drives=2
			[[ -n "${MEDIA_DISK3_UUID:-}" ]] && num_drives=3
			# Count any additional drives from environment
			for i in {4..10}; do
				var_name="MEDIA_DISK${i}_UUID"
				if [[ -n "${!var_name:-}" ]]; then
					num_drives=$i
				fi
			done
		fi

		# Configure the drives
		for ((i = 1; i <= num_drives; i++)); do
			local var_name="MEDIA_DISK${i}_UUID"
			local current_value="${!var_name:-}"
			local prompt_text="Drive $i UUID"

			if [[ $i -eq 1 ]]; then
				prompt_text="First drive UUID"
			elif [[ $i -eq 2 ]]; then
				prompt_text="Second drive UUID"
			elif [[ $i -eq 3 ]]; then
				prompt_text="Third drive UUID"
			else
				prompt_text="Drive $i UUID (optional)"
			fi

			# Make first two drives required, others optional
			if [[ $i -le 2 ]]; then
				prompt_for_media_drive "$var_name" "$prompt_text" "$current_value"
			else
				prompt_for_media_drive "$var_name" "$prompt_text (optional)" "$current_value"
			fi
		done

		# Clear any drives beyond the configured number
		for ((i = num_drives + 1; i <= 10; i++)); do
			local var_name="MEDIA_DISK${i}_UUID"
			eval "$var_name=''"
		done
	fi

	# Validate configuration
	local configured_drives=0
	for ((i = 1; i <= 10; i++)); do
		local var_name="MEDIA_DISK${i}_UUID"
		[[ -n "${!var_name:-}" ]] && ((configured_drives++))
	done

	if [[ $configured_drives -eq 0 ]]; then
		warn "No drives configured. Disabling media drives."
		MEDIA_DRIVES_ENABLED="false"
	elif [[ $configured_drives -eq 1 && "$MEDIA_MOUNT_MODE" == "mergerfs" ]]; then
		if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
			echo ""
			warn "Only one drive configured for mergerFS mode."
			read -rp "Switch to single drive mode? [Y/n]: " switch_mode
		else
			log "Non-interactive mode detected. Defaulting to 'Yes'."
			switch_mode="y"
		fi
		if [[ "${switch_mode,,}" =~ ^(y|yes)$ ]]; then
			MEDIA_MOUNT_MODE="single"
			log "Switched to single drive mode."
		elif [[ "${switch_mode,,}" =~ ^(n|no)$ ]]; then
			log "Keeping mergerFS mode with single drive."
			# Logic to retain mergerFS mode
		fi
	fi

	# Summary
	if [[ "${MEDIA_DRIVES_ENABLED:-false}" == "true" ]]; then
		echo ""
		echo "✅ Media drive configuration summary:"
		echo "   Mode: $MEDIA_MOUNT_MODE"
		echo "   Drives configured: $configured_drives"

		# Show all configured drives
		for ((i = 1; i <= 10; i++)); do
			local var_name="MEDIA_DISK${i}_UUID"
			local drive_uuid="${!var_name:-}"
			[[ -n "$drive_uuid" ]] && echo "   Disk $i: $drive_uuid"
		done

		echo ""

		if [[ "$MEDIA_MOUNT_MODE" == "mergerfs" ]]; then
			log "Drives will be mounted at /opt/intelluxe/storage/disk1, /opt/intelluxe/storage/disk2, etc. and pooled at /opt/intelluxe/data/Media"
		elif [[ "$MEDIA_MOUNT_MODE" == "independent" ]]; then
			log "Drives will be mounted independently at /opt/intelluxe/data/Movies, /opt/intelluxe/data/TV, etc."
		else
			log "Drive will be mounted at /opt/intelluxe/data/Media"
		fi
	else
		log "Media drives disabled."
	fi
}

# ----------------- Individual Drive Management -----------------
manage_drives_individually() {
	# Allow users to add/remove drives one by one
	while true; do
		echo ""
		echo "========================================"
		echo "     INDIVIDUAL DRIVE MANAGEMENT"
		echo "========================================"
		echo ""

		# Show current drive configuration
		local configured_drives=0
		echo "📀 Current drive configuration:"
		for ((i = 1; i <= 10; i++)); do
			local var_name="MEDIA_DISK${i}_UUID"
			local drive_uuid="${!var_name:-}"
			if [[ -n "$drive_uuid" ]]; then
				echo "   Slot $i: $drive_uuid"
				((configured_drives++))
			else
				echo "   Slot $i: [empty]"
			fi
		done

		echo ""
		echo "Options:"
		echo "  1) Add a drive to empty slot"
		echo "  2) Remove a drive from slot"
		echo "  3) Replace drive in slot"
		echo "  4) View available drives"
		echo "  5) Done managing drives"
		echo ""

		read -rp "Choice [1-5]: " choice
		case "$choice" in
		1)
			add_drive_to_slot
			;;
		2)
			remove_drive_from_slot
			;;
		3)
			replace_drive_in_slot
			;;
		4)
			echo ""
			echo "📀 Available drives:"
			detect_available_drives || echo "   No additional drives detected"
			echo ""
			read -rp "Press Enter to continue..."
			;;
		5)
			break
			;;
		*)
			warn "Invalid choice. Please select 1-5."
			;;
		esac
	done
}

add_drive_to_slot() {
	# Add a drive to the first available slot
	local empty_slot=""
	for ((i = 1; i <= 10; i++)); do
		local var_name="MEDIA_DISK${i}_UUID"
		if [[ -z "${!var_name:-}" ]]; then
			empty_slot=$i
			break
		fi
	done

	if [[ -z "$empty_slot" ]]; then
		warn "All drive slots (1-10) are currently occupied."
		return
	fi

	echo ""
	echo "Adding drive to slot $empty_slot"
	echo "Available drives:"
	detect_available_drives || echo "   No additional drives detected"
	echo ""

	local var_name="MEDIA_DISK${empty_slot}_UUID"
	prompt_for_media_drive "$var_name" "Drive UUID for slot $empty_slot" ""

	if [[ -n "${!var_name:-}" ]]; then
		log "✅ Added drive ${!var_name} to slot $empty_slot"
	fi
}

remove_drive_from_slot() {
	# Remove a drive from a specific slot
	local occupied_slots=()
	for ((i = 1; i <= 10; i++)); do
		local var_name="MEDIA_DISK${i}_UUID"
		if [[ -n "${!var_name:-}" ]]; then
			occupied_slots+=("$i")
		fi
	done

	if [[ ${#occupied_slots[@]} -eq 0 ]]; then
		warn "No drives configured to remove."
		return
	fi

	echo ""
	echo "Occupied slots:"
	for slot in "${occupied_slots[@]}"; do
		local var_name="MEDIA_DISK${slot}_UUID"
		echo "   Slot $slot: ${!var_name}"
	done
	echo ""

	read -rp "Enter slot number to remove [1-10]: " slot_to_remove

	if [[ ! "$slot_to_remove" =~ ^[1-9]$|^10$ ]]; then
		warn "Invalid slot number. Must be 1-10."
		return
	fi

	local var_name="MEDIA_DISK${slot_to_remove}_UUID"
	if [[ -z "${!var_name:-}" ]]; then
		warn "Slot $slot_to_remove is already empty."
		return
	fi

	echo "⚠️  About to remove drive from slot $slot_to_remove: ${!var_name}"
	if [[ -t 0 ]]; then
		read -rp "Are you sure? This will not delete data, just remove from config [y/N]: " confirm
	else
		log "Non-interactive mode detected. Defaulting to 'No'."
		confirm="n"
	fi

	if [[ "${confirm,,}" =~ ^(y|yes)$ ]]; then
		eval "$var_name=''"
		log "✅ Removed drive from slot $slot_to_remove"
	else
		log "Operation cancelled."
	fi
}

replace_drive_in_slot() {
	# Replace a drive in a specific slot
	echo ""
	echo "Current drive configuration:"
	for ((i = 1; i <= 10; i++)); do
		local var_name="MEDIA_DISK${i}_UUID"
		local drive_uuid="${!var_name:-}"
		if [[ -n "$drive_uuid" ]]; then
			echo "   Slot $i: $drive_uuid"
		fi
	done
	echo ""

	read -rp "Enter slot number to replace [1-10]: " slot_to_replace

	if [[ ! "$slot_to_replace" =~ ^[1-9]$|^10$ ]]; then
		warn "Invalid slot number. Must be 1-10."
		return
	fi

	local var_name="MEDIA_DISK${slot_to_replace}_UUID"
	local current_uuid="${!var_name:-}"

	if [[ -z "$current_uuid" ]]; then
		warn "Slot $slot_to_replace is empty. Use 'Add drive' option instead."
		return
	fi

	echo "Current drive in slot $slot_to_replace: $current_uuid"
	echo "Available drives:"
	detect_available_drives || echo "   No additional drives detected"
	echo ""

	prompt_for_media_drive "$var_name" "New drive UUID for slot $slot_to_replace" "$current_uuid"

	if [[ "${!var_name}" != "$current_uuid" ]]; then
		log "✅ Replaced drive in slot $slot_to_replace: $current_uuid → ${!var_name}"
	fi
}

# ----------------- Logging -----------------
backup_compose_yml() {
	# Backup the docker-compose.yml file.
	if [[ $DRY_RUN == true ]]; then
		log "[DRY-RUN] Would back up docker-compose.yml"
		return
	fi
	if [[ -f "$COMPOSE_FILE" ]]; then
		local ts
		ts="$(date +"%Y%m%d-%H%M%S")"
		cp -a "$COMPOSE_FILE" "$BACKUP_DIR/docker-compose-${ts}.yml"
		chmod 0600 "$BACKUP_DIR/docker-compose-${ts}.yml"
		log "Backed up docker-compose.yml to $BACKUP_DIR/docker-compose-${ts}.yml"
		prune_backups "docker-compose-*.yml"
	fi
}

prune_backups() {
	# Prune old backup files, keeping only BACKUP_RETENTION.
	local pattern="$1"
	local files
	mapfile -t files < <(ls -1t "$BACKUP_DIR"/"${pattern}" 2>/dev/null || true)
	if ((${#files[@]} > BACKUP_RETENTION)); then
		for i in "${files[@]:$BACKUP_RETENTION}"; do
			log "Deleted old backup: $i"
			rm -f "$i"
		done
	fi
}

backup_wireguard() {
	# Backup the WireGuard config directory.
	if [[ $DRY_RUN == true ]]; then
		log "[DRY-RUN] Would back up WireGuard config"
		return
	fi
	mkdir -p "$BACKUP_DIR"
	local ts backup_file
	ts="$(date +"%Y%m%d-%H%M%S")"
	backup_file="${BACKUP_DIR}/wg-backup-${ts}.tar.gz"
	if tar czf "$backup_file" -C "$(dirname "$WG_DIR")" "$(basename "$WG_DIR")"; then
		log "Backed up WireGuard config to $backup_file"
		prune_backups "wg-backup-*.tar.gz"
	else
		warn "Failed to back up WireGuard config."
		return 1
	fi
}

restore_backup() {
	# Restore from a WireGuard backup archive and restart containers.
	local bfile="$1"
	[[ ! -f "$bfile" ]] && die "Backup file not found: $bfile" 2
	tar xzf "$bfile" -C /
	log "Restored backup from $bfile"
	backup_integrity_check
	# Restart Docker containers to ensure restored state is live
	log "Restarting all selected containers after restore..."
	for c in "${SELECTED_CONTAINERS[@]}"; do
		docker restart "$c" || warn "Could not restart container $c after restore"
	done
}

verify_backup() {
	# Verify that a backup archive is valid.
	local bfile="$1"
	if tar tzf "$bfile" &>/dev/null; then
		ok "Backup $bfile is valid."
		return 0
	else
		fail "Backup $bfile is invalid or corrupted."
		return 1
	fi
}

backup_integrity_check() {
	# Check that restored backup has expected files.
	[[ -d "$WG_DIR" ]] || warn "Restored WireGuard directory missing: $WG_DIR"
	[[ -f "$WG_KEYS_ENV" ]] || warn "Restored WireGuard keys missing: $WG_KEYS_ENV"
}

prompt_for_path() {
	# Prompt for a directory path, with default.
	local var="$1" default="$2" prompt="$3"
	if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
		eval "$var='$default'"
		return
	fi
	if [[ -t 0 ]]; then
		read -rp "$prompt (press Enter for '$default'): " val
	else
		log "Non-interactive mode detected. Defaulting to '$default'."
		val="$default"
	fi
	val="${val/#\~/$HOME}" # Expand ~ to home directory
	eval "$var=\"\$val\""
}

prompt_for_port() {
	# Prompt for a port, with default.
	local var="$1" default="$2" proto="$3"
	if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
		CONTAINER_PORTS[$var]="$default"
		return
	fi
	if [[ -t 0 ]]; then
		read -rp "Port for $var ($proto) (press Enter for '$default'): " val
	else
		log "Non-interactive mode detected. Defaulting to '$default'."
		val="$default"
	fi
	val="${val/#\~/$HOME}" # Expand ~ to home directory
	CONTAINER_PORTS[$var]="$val"
}

# ----------------- Health Check Command Generator -----------------
# <AUTOGEN-HEALTH-CMD-START>
get_health_cmd() {
    local cname="$1"
    
    # First check for health check in service config files
    local svc_file=""
    if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${cname}.conf" ]]; then
        svc_file="${SCRIPT_DIR%/scripts}/services/user/${cname}.conf"
    fi
    
    if [[ -n "$svc_file" ]]; then
        local healthcheck
        healthcheck=$(get_service_config_value "$svc_file" "healthcheck")
        if [[ -n "$healthcheck" ]]; then
            echo "$healthcheck"
            return 0
        fi
    fi
    
    # No hardcoded health checks - services should define healthcheck in their .conf files
    # Return empty if no health check is configured for this service
    echo ""
}
# <AUTOGEN-HEALTH-CMD-END>

container_menu() {
        # Present a menu for interactive container management.
        if [[ ${#ALL_CONTAINERS[@]} -eq 0 ]]; then
                log "No configured containers found."
                return
        fi
        local user_quit_menu=false
	while true; do
		echo "Container Management Menu"
		echo "---------------------------------"
		for i in "${!ALL_CONTAINERS[@]}"; do
			cname="${ALL_CONTAINERS[$i]}"
			local description="${CONTAINER_DESCRIPTIONS[$cname]:-No description available}"
			status=$(docker ps --filter "name=^/${cname}$" --format '{{.Status}}' | head -n1 || echo "not running")
			printf "%d) %-10s %-30s %-10s\n" "$((i + 1))" "$cname" "$description" "$status"
		done
		echo "a) Start/Recreate All"
		echo "s) Stop All"
		echo "q) Continue setup with defaults"
		echo "Select a container by number, or an action (a/s/q):"
		if $FORCE_DEFAULTS; then
			echo "[FORCE-DEFAULTS] Skipping interactive container management."
			break
		fi
		read -rp "Choice: " choice
		case "$choice" in
		[1-9] | 1[0-9])
			idx=$((choice - 1))
			[[ -z "${ALL_CONTAINERS[$idx]:-}" ]] && continue
			menu_container_action "${ALL_CONTAINERS[$idx]}"
			;;
		a | A)
			log "Starting/Recreating all containers..."
			for c in "${ALL_CONTAINERS[@]}"; do
				ensure_container_running "$c"
			done
			;;
		s | S)
			for c in "${ALL_CONTAINERS[@]}"; do				container_action --stop "$c"
			done
			;;
		q | Q)
			user_quit_menu=true
			break
			;;
		*)
			warn "Unknown choice: $choice"
			;;
		esac
	done
	# Set a global flag to skip container selection
    if [[ "$user_quit_menu" == "true" ]]; then
        SKIP_CONTAINER_SELECTION=true
    fi
    log "Exited container menu, continuing with default setup."
}

menu_container_action() {
	# Menu for actions on a single container.
	local cname="$1"
	echo "Actions for $cname:"
	select action in "Start/Recreate" "Stop" "Restart/Recreate" "Remove" "Status" "Back"; do
		case $REPLY in
		1) # Start/Recreate
			ensure_container_running "$cname"
			break
			;;
		2) # Stop
			container_action --stop "$cname"
			break
			;;
		3) # Restart/Recreate
			ensure_container_running "$cname"
			break
			;;
		4) # Remove
			container_action --remove "$cname"
			break
			;;
		5) # Status
			container_action --status "$cname"
			break
			;;
		6) break ;;
		*) warn "Invalid selection" ;;
		esac
	done
}

choose_containers() {
        # Prompt user to select containers to (re)start.
        if [[ ${#ALL_CONTAINERS[@]} -eq 0 ]]; then
                log "No containers available for selection."
                SELECTED_CONTAINERS=()
                return
        fi
        if $NON_INTERACTIVE || ($FORCE_DEFAULTS && [[ -n "${SELECTED_CONTAINERS[*]:-}" ]]); then
		# If no containers are selected in non-interactive mode, use all containers
		if [[ -z "${SELECTED_CONTAINERS[*]:-}" ]]; then
			SELECTED_CONTAINERS=("${ALL_CONTAINERS[@]}")
			log "No previous selection found. Using all containers in non-interactive mode: ${SELECTED_CONTAINERS[*]}"
		else
			log "Using previously selected containers: ${SELECTED_CONTAINERS[*]}"
		fi
		return
	fi
	log "Select containers to (re)start."
	for i in "${!ALL_CONTAINERS[@]}"; do
		local container_name="${ALL_CONTAINERS[$i]}"
		local description="${CONTAINER_DESCRIPTIONS[$container_name]:-No description available}"
		echo "  $((i + 1))) ${container_name} - ${description}"
	done
	echo "Enter numbers separated by spaces (or press Enter for all):"
	if $FORCE_DEFAULTS; then
		SELECTED_CONTAINERS=("${ALL_CONTAINERS[@]}")
		log "[FORCE-DEFAULT] All containers selected."
		return
	fi
	read -rp "Choice: " choices
	if [[ -z "$choices" ]]; then
		SELECTED_CONTAINERS=("${ALL_CONTAINERS[@]}")
	else
		SELECTED_CONTAINERS=()
		for idx in $choices; do
			# Validate that idx is a number
			if [[ "$idx" =~ ^[0-9]+$ ]]; then
				SEL="${ALL_CONTAINERS[$((idx - 1))]}"
				[[ -n "$SEL" ]] && SELECTED_CONTAINERS+=("$SEL")
			else
				warn "Invalid input '$idx' - only numbers are allowed"
			fi
		done
	fi
	log "Selected containers: ${SELECTED_CONTAINERS[*]}"
}

container_action() {
	# Start/stop/restart/remove/status for a given container.
	local action="$1" cname="$2"
	if ! docker container inspect "$cname" &>/dev/null; then
		echo "Container $cname does not exist."
		return 1
	fi
	case "$action" in
	--start) docker start "$cname" >/dev/null ;;
	--stop) docker stop "$cname" >/dev/null ;;
	--restart) docker restart "$cname" >/dev/null ;;
	--remove) docker rm -f "$cname" >/dev/null ;;
	--status) docker ps -a --filter name="^${cname}$" ;;
        *) warn "Unknown action $action" ;;
        esac
}

# --- Configuration Web UI Service Management ---
enable_config_web_ui() {
	log "Enabling config-web-ui.service"
	run systemctl enable --now config-web-ui.service
}

install_package() {
	# Install a package via the detected package manager.
	local pkg="$1"
	if command -v apt-get &>/dev/null; then
		sudo apt-get update && sudo apt-get install -y "$pkg"
	elif command -v dnf &>/dev/null; then
		sudo dnf install -y "$pkg"
	elif command -v yum &>/dev/null; then
		sudo yum install -y "$pkg"
	elif command -v pacman &>/dev/null; then
		sudo pacman -Sy --noconfirm "$pkg"
	elif command -v apk &>/dev/null; then
		sudo apk add "$pkg"
	else
		warn "No known package manager found. Please install $pkg manually."
		return 1
	fi
}

ensure_docker_image() {
	# Ensure a Docker image is present, pull if not.
	local image="$1" description="$2"
	if ! docker image inspect "$image" &>/dev/null; then
		warn "Image '$image' is not present."
		echo "$description"
		if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
		
			log "Non-interactive: Pulling '$image' automatically."
			$DRY_RUN && log "[DRY-RUN] Would pull $image" && return 0
			docker pull "$image"
		else
			read -rp "Would you like to install (docker pull) '$image'? [Y/n]: " ans
			if [[ "${ans,,}" =~ ^(y|yes|)$ ]]; then
				log "Pulling Docker image '$image'..."
				docker pull "$image"
			else
				warn "Skipping container $image. It will not be started."
				return 1
			fi
		fi
	fi
	return 0
}

ensure_directories() {
        # Ensure all required directories exist and are owned correctly.
        [[ $DRY_RUN == true ]] && log "[DRY-RUN] Would ensure directories" && return
        mkdir -p "$CFG_ROOT" "$BACKUP_DIR" "$QR_DIR"
        set_ownership "$CFG_ROOT" "$BACKUP_DIR" "$QR_DIR"

        # WireGuard directories are needed for validation even if the container
        # isn't launched yet
        mkdir -p "$WG_DIR" "$WG_CLIENTS_DIR"
        set_ownership "$WG_DIR" "$WG_CLIENTS_DIR"

        # Container-specific directories - dynamically create based on services
        for c in "${ALL_CONTAINERS[@]}"; do
            # Check service config for volume requirements
            local svc_file=""
            if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${c}.conf" ]]; then
                svc_file="${SCRIPT_DIR%/scripts}/services/user/${c}.conf"
            fi
            
            if [[ -n "$svc_file" ]]; then
                local volumes
                volumes=$(get_service_config_value "$svc_file" "volumes")
                
                # Create data directories based on volume patterns
                if [[ -n "$volumes" ]]; then
                    if [[ "$volumes" == *"-data:"* ]]; then
                        mkdir -p "$CFG_ROOT/${c}-data"
                        set_ownership "$CFG_ROOT/${c}-data"
                    fi
                    if [[ "$volumes" == *"-config:"* ]]; then
                        mkdir -p "$CFG_ROOT/${c}-config"
                        set_ownership "$CFG_ROOT/${c}-config"
                    fi
                fi
            fi
            
            # Special handling for services with additional directory needs
            case "$c" in
                traefik)
                    mkdir -p "$CFG_ROOT/traefik-config" "$CFG_ROOT/traefik-data"
                    set_ownership "$CFG_ROOT/traefik-config" "$CFG_ROOT/traefik-data"
                    ;;
            esac
        done
}

ensure_docker_network() {
	# Ensure the named Docker network exists.
	local netname="$1" subnet="$2"
	if docker network inspect "$netname" &>/dev/null; then
		log "Docker network $netname already exists."
	else
		if ! docker network create --subnet="$subnet" "$netname"; then
			die "Failed to create Docker network $netname with subnet $subnet."
		fi
		log "Docker network $netname created with subnet $subnet."
	fi
}

get_next_available_ip() {
    # Use configurable VPN subnet base
    local base="${VPN_SUBNET_BASE:-10.8.0}"
    local used_ips=()
    local ip
    for d in "$WG_CLIENTS_DIR"/*; do
        [[ -d "$d" ]] || continue
        if [[ -f "$d/ip" ]]; then
            used_ips+=("$(<"$d/ip")")
        fi
    done
    for i in {2..254}; do
        ip="${base}.${i}"
        if [[ ! " ${used_ips[*]} " =~ ${ip} ]]; then
            echo "$ip"
            return
        fi
    done
    die "No available IP addresses left for clients."
}

get_server_ip() {
    # Get the actual server IP for display purposes
    ip route get 8.8.8.8 | awk '/src/ {print $NF; exit}' 2>/dev/null || echo "your-server-ip"
}
delete_client() {
	# Remove a WireGuard client and backup before deleting.
	local clientname="$1"
	local clientdir="$WG_CLIENTS_DIR/$clientname"
	[[ ! -d "$clientdir" ]] && {
		warn "No client directory found for $clientname"
		return 1
	}
	backup_wireguard
	rm -rf "$clientdir"
	rm -f "$QR_DIR/${clientname}.png"
	log "Deleted client $clientname and associated configs."
}

generate_wg_qr() {
    local clientdir="$1" clientname="$2"
    local conf="$clientdir/${clientname}.conf"
    [[ ! -f "$conf" ]] && return

    # Primary location: client directory
    local qrfile_client="${clientdir}/${clientname}.png"
    # Optional: central location for convenience
    local qrfile_central="${QR_DIR}/${clientname}.png"

    if command -v qrencode >/dev/null 2>&1; then
        qrencode -o "$qrfile_client" <"$conf"
        set_ownership "$qrfile_client"

        # Also save to central location
        mkdir -p "$QR_DIR"
        cp "$qrfile_client" "$qrfile_central"
        set_ownership "$qrfile_central"

        log "QR code for $clientname saved to $qrfile_client (and copied to $qrfile_central)"
    else
        warn "qrencode not found; skipping QR code for $clientname"
    fi
}

vault_login() {
    if [[ -z "${VAULTWARDEN_TOKEN:-}" ]]; then
        warn "VAULTWARDEN_TOKEN not set; skipping Vaultwarden upload"
        return 1
    fi
    if ! command -v bw >/dev/null 2>&1; then
        warn "vaultwarden-cli (bw) not installed"
        return 1
    fi
    export BW_SESSION="$VAULTWARDEN_TOKEN"
    bw config server "$VAULTWARDEN_URL" >/dev/null 2>&1 || true
    if ! bw sync >/dev/null 2>&1; then
        err "Vaultwarden authentication failed"
        return 1
    fi
    log "Authenticated with Vaultwarden"
    return 0
}

vault_upload_client_files() {
    local clientdir="$1" clientname="$2"
    local conf="$clientdir/${clientname}.conf"
    local priv="$clientdir/private.key"
    local qrfile="${QR_DIR}/${clientname}.png"

    vault_login || return 1

    local item_json item_id
    item_json=$(jq -n --arg name "WireGuard ${clientname}" --arg notes "Auto uploaded by clinic-bootstrap" '{type:2,name:$name,notes:$notes}')
    item_id=$(echo "$item_json" | bw create item 2>/dev/null | jq -r '.id')
    [[ -z "$item_id" ]] && { err "Failed to create Vaultwarden item"; return 1; }
    bw create attachment --file "$conf" --itemid "$item_id" >/dev/null
    bw create attachment --file "$priv" --itemid "$item_id" >/dev/null
    [[ -f "$qrfile" ]] && bw create attachment --file "$qrfile" --itemid "$item_id" >/dev/null
    log "Uploaded $clientname configuration to Vaultwarden"
}

suggest_new_clientname() {
	# Suggest a new client name based on base name.
	local base="$1" n=2
	while [[ -d "$WG_CLIENTS_DIR/${base}-${n}" ]]; do n=$((n + 1)); done
	echo "${base}-${n}"
}

load_wg_keys_env() {
	# Load WireGuard server keys from wg-keys.env file.
	if [[ ! -f "$WG_KEYS_ENV" ]]; then
		die "wg-keys.env missing at $WG_KEYS_ENV. Please create it with required keys before running this script." 23
	fi
	# shellcheck disable=SC1090
	source "$WG_KEYS_ENV"
	if [[ -z "${WG_SERVER_PRIVATE_KEY:-}" || -z "${WG_SERVER_PUBLIC_KEY:-}" || -z "${WG_PRESHARED_KEY:-}" ]]; then
		die "Missing required variables in $WG_KEYS_ENV. Required: WG_SERVER_PRIVATE_KEY, WG_SERVER_PUBLIC_KEY, WG_PRESHARED_KEY" 24
	fi
}

setup_wireguard_keys() {
	# Setup WireGuard keys using wg-keys.env (safer for public sharing).
	mkdir -p "$WG_DIR" "$WG_CLIENTS_DIR"
	set_ownership "$WG_DIR" "$WG_CLIENTS_DIR"
	if [[ ! -f "$WG_KEYS_ENV" ]]; then
		if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
			log "Generating server keypair in wg-keys.env."
			umask 077
			WG_SERVER_PRIVATE_KEY=$(wg genkey)
			WG_SERVER_PUBLIC_KEY=$(echo "$WG_SERVER_PRIVATE_KEY" | wg pubkey)
			WG_PRESHARED_KEY=$(wg genpsk)
			{
				echo "WG_SERVER_PRIVATE_KEY=$WG_SERVER_PRIVATE_KEY"
				echo "WG_SERVER_PUBLIC_KEY=$WG_SERVER_PUBLIC_KEY"
				echo "WG_PRESHARED_KEY=$WG_PRESHARED_KEY"
			} >"$WG_KEYS_ENV"
			chmod 0600 "$WG_KEYS_ENV"
			set_ownership "$WG_KEYS_ENV"
			log "Server keys generated and saved in $WG_KEYS_ENV."
		else
			read -rp "wg-keys.env not found in $WG_DIR. Generate new server keys? [Y/n]: " ans
			if [[ "${ans,,}" =~ ^(y|yes|)$ ]]; then
				umask 077
				WG_SERVER_PRIVATE_KEY=$(wg genkey)
				WG_SERVER_PUBLIC_KEY=$(echo "$WG_SERVER_PRIVATE_KEY" | wg pubkey)
				WG_PRESHARED_KEY=$(wg genpsk)
				{
					echo "WG_SERVER_PRIVATE_KEY=$WG_SERVER_PRIVATE_KEY"
					echo "WG_SERVER_PUBLIC_KEY=$WG_SERVER_PUBLIC_KEY"
					echo "WG_PRESHARED_KEY=$WG_PRESHARED_KEY"
				} >"$WG_KEYS_ENV"
				chmod 0600 "$WG_KEYS_ENV"
				set_ownership "$WG_KEYS_ENV"
				log "Server keys generated in $WG_KEYS_ENV."
			else
				die "Server keys are required. Please provide them in $WG_KEYS_ENV."
			fi
		fi
		backup_wireguard
	fi
	load_wg_keys_env

	while true; do
		if $NON_INTERACTIVE || $FORCE_DEFAULTS; then
			break
		fi
		echo "WireGuard Clients:"
		for d in "$WG_CLIENTS_DIR"/*; do
			[[ -d "$d" ]] || continue
			echo "  - $(basename "$d") (IP: $(cat "$d/ip" 2>/dev/null || echo 'n/a'))"
		done
		echo "Options:"
		echo "  1) Add client"
		echo "  2) Delete client"
		echo "  3) Done"
		read -rp "Choice [1-3] (press Enter for '3'): " choice
		choice="${choice:-3}"
		case "$choice" in
		1)
			read -rp "Client name (e.g., phone, laptop): " clientname
			[[ -z "$clientname" ]] && {
				warn "No client name entered, skipping."
				continue
			}
			local clientdir="$WG_CLIENTS_DIR/$clientname"
			if [[ -d "$clientdir" ]]; then
				echo "Client '$clientname' already exists."
				local suggested
				suggested=$(suggest_new_clientname "$clientname")
				echo "Options:"
				echo "  1) Overwrite existing client"
				echo "  2) Enter a new name"
				echo "  3) Use suggested name: $suggested"
				echo "  4) Cancel"
				read -rp "Choice [1-4]: " dup_choice
				case "$dup_choice" in
				1) rm -rf "$clientdir" ;;
				2)
					read -rp "New client name: " clientname
					[[ -z "$clientname" ]] && continue
					clientdir="$WG_CLIENTS_DIR/$clientname"
					;;
				3)
					clientname="$suggested"
					clientdir="$WG_CLIENTS_DIR/$clientname"
					;;
				4) continue ;;
				*) continue ;;
				esac
			fi
			mkdir -p "$clientdir"
			set_ownership "$clientdir"
			local client_ip
			client_ip=$(get_next_available_ip)
			echo "$client_ip" >"$clientdir/ip"
			local client_private client_public
			client_private=$(wg genkey)
			client_public=$(echo "$client_private" | wg pubkey)
			echo "$client_private" >"$clientdir/private.key"
			echo "$client_public" >"$clientdir/public.key"
			chmod 0600 "$clientdir"/*.key
			set_ownership "$clientdir"/*.key
			read -rp "Client DNS (press Enter for '${WG_CLIENT_DNS}'): " client_dns
			client_dns="${client_dns:-$WG_CLIENT_DNS}"
			read -rp "Server endpoint (e.g., your.domain.com:${CONTAINER_PORTS[wireguard]}); " server_endpoint
			server_endpoint="${server_endpoint:-localhost:${CONTAINER_PORTS[wireguard]}}"
			[[ "$server_endpoint" == "localhost:${CONTAINER_PORTS[wireguard]}" ]] && \
			warn "Using default endpoint $server_endpoint"
			cat >"$clientdir/${clientname}.conf" <<EOF
[Interface]
PrivateKey = $client_private
Address = $client_ip/32
DNS = $client_dns

[Peer]
PublicKey = $WG_SERVER_PUBLIC_KEY
PresharedKey = $WG_PRESHARED_KEY
AllowedIPs = 0.0.0.0/0
Endpoint = $server_endpoint
EOF
			set_ownership "$clientdir/${clientname}.conf"
			log "Created client config for $clientname at $clientdir/${clientname}.conf"
                        generate_wg_qr "$clientdir" "$clientname"

                        if [[ "$STORE_WG_IN_VAULT" == "true" ]]; then
                            ans="y"
                        elif $NON_INTERACTIVE || $FORCE_DEFAULTS; then
                            ans="n"
                        else
                            read -rp "Store this client in Vaultwarden? [y/N]: " ans
                        fi
                        if [[ "${ans,,}" == "y" ]]; then
                            if ! is_container_running vaultwarden; then
                                echo "Vaultwarden container is not running."
                                echo "Consider using Vaultwarden to securely store secrets."
                                read -rp "Start Vaultwarden container now? [y/N]: " start_vault
                                if [[ "${start_vault,,}" == "y" ]]; then
                                    ensure_container_running "vaultwarden"
                                else
                                    log "Skipping Vaultwarden upload."
                                    ans="n"
                                fi
                            fi
                        fi
                        if [[ "${ans,,}" == "y" ]]; then
                            vault_upload_client_files "$clientdir" "$clientname"
                        fi

                        backup_wireguard
			;;
		2)
			read -rp "Client name to delete: " delname
			[[ -z "$delname" ]] && continue
			delete_client "$delname"
			;;
		3) break ;;
		*) echo "Invalid choice." ;;
		esac
	done
}

get_container_health() {
        # Get the health status of a Docker container.
        local container="$1"
        docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown"
}

verify_container_ip() {
        local container="$1" expected_ip="$2"
        local actual_ip

        if ! docker inspect "$container" &>/dev/null; then
                log "Container $container not found; skipping IP verification."
                return 0
        fi

        actual_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container" 2>/dev/null || echo "")
        if [[ -z "$actual_ip" ]]; then
                warn "Could not determine IP for container $container"
                return 1
        fi

        if [[ "$actual_ip" != "$expected_ip" ]]; then
                warn "IP mismatch for $container: expected $expected_ip, got $actual_ip"
                return 1
        else
                log "$container IP verified as $actual_ip"
        fi

        return 0
}

is_container_running() {
        local cname="$1"
        docker ps -q --filter "name=^/${cname}$" | grep -q .
}

check_permissions() {
	# Warn if sensitive files are world-readable.
	for f in "$WG_KEYS_ENV" "$LOG_FILE" "$CONFIG_FILE"; do
		if [ -f "$f" ]; then
			local perm
			perm=$(stat -c '%a' "$f" 2>/dev/null || echo "")
			if [ -n "$perm" ] && [ "$perm" -gt 600 ]; then
				warn "File $f is more permissive than 0600. Consider tightening permissions."
			fi

			# Check ownership - should match CFG_UID:CFG_GID, not necessarily root
			local file_uid file_gid
			file_uid=$(stat -c '%u' "$f" 2>/dev/null || echo "")
			file_gid=$(stat -c '%g' "$f" 2>/dev/null || echo "")
			if [[ -n "$file_uid" && -n "$file_gid" ]]; then
				if [[ "$file_uid" != "$CFG_UID" || "$file_gid" != "$CFG_GID" ]]; then
					warn "File $f ownership ($file_uid:$file_gid) doesn't match expected ($CFG_UID:$CFG_GID). Consider running: sudo chown $CFG_UID:$CFG_GID $f"
				fi
			fi
		fi
	done
}

check_docker_socket() {
        local sock="$DOCKER_SOCKET"
	local perm=""
	if [ -S "$sock" ]; then
		if [ -e "$sock" ]; then
			if perm=$(stat -c '%a' "$sock" 2>/dev/null); then
				: # perm is set
			else
				perm=""
			fi
		else
			perm=""
		fi
		if [ -n "$perm" ] && [ "$perm" -gt 660 ]; then
			warn "Docker socket $sock is world-writable! This is a security risk."
		fi
	fi
	return 0
}

configure_firewall() {
	# Configure firewall rules for selected containers
	if [[ $DRY_RUN == true ]]; then
		log "[DRY-RUN] Would configure firewall rules"
		return
	fi

	local ports_to_open=()

	# Collect ports that need to be opened based on selected containers
	for container in "${SELECTED_CONTAINERS[@]}"; do
		local port=""
		local protocol="tcp"
		
		# Get port and protocol from service configuration
		local svc_file=""
		if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
			svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
		fi
		
		if [[ -n "$svc_file" ]]; then
			port=$(get_service_config_value "$svc_file" "port")
			# Check if service uses UDP (typically VPN services)
			if [[ "$container" == "wireguard" ]] || grep -q "udp" "$svc_file" 2>/dev/null; then
				protocol="udp"
			fi
		fi
		
		# Use configured port or fallback to CONTAINER_PORTS
		if [[ -z "$port" && -n "${CONTAINER_PORTS[$container]:-}" ]]; then
			port="${CONTAINER_PORTS[$container]}"
		fi
		
		if [[ -n "$port" ]]; then
			# Extract just the host port from port mappings like "3000:80"
			local host_port="${port%%:*}"
			ports_to_open+=("${host_port}/${protocol}")
			
			# Handle additional ports from service configuration
			local svc_file=""
			if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
				svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
			fi
			
			if [[ -n "$svc_file" ]]; then
				local additional_ports
				additional_ports=$(get_service_config_value "$svc_file" "additional_ports")
				if [[ -n "$additional_ports" ]]; then
					IFS=';' read -ra port_array <<< "$additional_ports"
					for port_mapping in "${port_array[@]}"; do
						if [[ -n "$port_mapping" ]]; then
							# Extract just the host port and protocol from port_mapping (format: host_port:container_port/protocol)
							local host_port_proto="${port_mapping%%:*}"
							if [[ "$host_port_proto" == *"/"* ]]; then
								ports_to_open+=("$host_port_proto")
							else
								# Default to TCP if no protocol specified
								ports_to_open+=("${host_port_proto}/tcp")
							fi
						fi
					done
				fi
				
				# Handle fixed additional ports (like HTTP/HTTPS for reverse proxies)
				local fixed_ports
				fixed_ports=$(get_service_config_value "$svc_file" "firewall_ports")
				if [[ -n "$fixed_ports" ]]; then
					IFS=';' read -ra fixed_array <<< "$fixed_ports"
					for fixed_port in "${fixed_array[@]}"; do
						[[ -n "$fixed_port" ]] && ports_to_open+=("$fixed_port")
					done
				fi
			fi
		else
			warn "No port configured for container: $container"
		fi
	done

	if [[ ${#ports_to_open[@]} -eq 0 ]]; then
		log "No firewall rules needed for selected containers."
		return
	fi

	# Check if ufw is available and active
	if command -v ufw &>/dev/null; then
		local ufw_status
		ufw_status=$(ufw status 2>/dev/null | head -n1 || echo "inactive")
		if [[ "$ufw_status" == *"active"* ]]; then
			log "Configuring UFW firewall rules..."
			for port in "${ports_to_open[@]}"; do
				if sudo ufw allow "$port" &>/dev/null; then
					log "Opened port $port in UFW"
				else
					warn "Failed to open port $port in UFW"
				fi
			done
			return
		fi
	fi

	# Fall back to iptables if ufw is not active
	if command -v iptables &>/dev/null; then
		log "Configuring iptables firewall rules..."
		for port_proto in "${ports_to_open[@]}"; do
			local port="${port_proto%/*}"
			local proto="${port_proto#*/}"

			# Check if rule already exists
			if ! sudo iptables -C INPUT -p "$proto" --dport "$port" -j ACCEPT 2>/dev/null; then
				if sudo iptables -A INPUT -p "$proto" --dport "$port" -j ACCEPT; then
					log "Opened port $port/$proto in iptables"
				else
					warn "Failed to open port $port/$proto in iptables"
				fi
			else
				log "Port $port/$proto already open in iptables"
			fi
		done

		# Save iptables rules if possible
		if command -v iptables-save &>/dev/null && command -v netfilter-persistent &>/dev/null; then
			sudo netfilter-persistent save || warn "Failed to save iptables rules"
		elif command -v iptables-save &>/dev/null && [[ -d /etc/iptables ]]; then
			sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null || warn "Could not save iptables rules - they may not persist after reboot"
		else
			warn "Could not save iptables rules - they may not persist after reboot"
		fi
	else
		warn "Neither ufw nor iptables found - firewall configuration skipped"
	fi
}

# Configure service access restrictions based on user preference
configure_service_restrictions() {
	local restrictable_services=()

	# Skip firewall configuration if no firewall tools are available
	if ! command -v ufw &>/dev/null && ! command -v iptables &>/dev/null; then
		log "No firewall tools (ufw/iptables) available - skipping service restrictions."
		return
	fi

	# Build list of restrictable services from selected containers with network ports
	for container in "${SELECTED_CONTAINERS[@]}"; do
		if [[ -n "${CONTAINER_PORTS[$container]:-}" ]]; then
			restrictable_services+=("$container")
		fi
	done

	if [[ ${#restrictable_services[@]} -eq 0 ]]; then
		log "No restrictable services selected - skipping firewall restrictions."
		return
	fi

	# Check if we have existing security configuration
	local config_exists=false
	if [[ -f "$CONFIG_FILE" ]] && grep -q "FIREWALL_RESTRICT_MODE" "$CONFIG_FILE" 2>/dev/null; then
		config_exists=true
	fi

	case "$FIREWALL_RESTRICT_MODE" in
	"ask")
		if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
			if [[ "$config_exists" == "true" ]]; then
				# Show current security configuration
				echo ""
				echo "========================================"
				echo "        CURRENT SECURITY SETTINGS"
				echo "========================================"
				echo ""

				case "$FIREWALL_RESTRICT_MODE" in
				"restrict")
					echo "🔒 Current: All services restricted to LAN + VPN only"
					;;
				"open")
					echo "🌐 Current: All services open to all networks"
					;;
				"custom")
					if [[ ${#RESTRICTED_SERVICES[@]} -gt 0 ]]; then
						echo "⚙️  Current: Custom restrictions applied to: ${RESTRICTED_SERVICES[*]}"
					else
						echo "🌐 Current: All services open to all networks"
					fi
					;;
				*)
					echo "🌐 Current: All services open to all networks"
					;;
				esac

				echo ""
				read -rp "Would you like to update your security settings? [y/N]: " ans
				if [[ ! "${ans,,}" =~ ^(y|yes)$ ]]; then
					log "Using existing security configuration."

					# Apply existing configuration
					case "$FIREWALL_RESTRICT_MODE" in
					"restrict")
						restrict_services_to_lan_vpn "${restrictable_services[@]}"
						;;
					"custom")
						if [[ ${#RESTRICTED_SERVICES[@]} -gt 0 ]]; then
							restrict_services_to_lan_vpn "${RESTRICTED_SERVICES[@]}"
						fi
						;;
					esac
					return
				fi
			fi

			# Show new configuration prompts
			echo ""
			echo "========================================"
			echo "          SECURITY CONFIGURATION"
			echo "========================================"
			echo ""
			echo "Configure network access restrictions for your services:"
			echo ""
			echo "  1) 🔒 Restrict all services to LAN + VPN only (RECOMMENDED)"
			echo "     └─ Services only accessible from your local network and VPN clients"
			echo "     └─ Blocks access from the public internet (most secure)"
			echo ""
			echo "  2) 🌐 Keep all services open to all networks"
			echo "     └─ Services accessible from anywhere on the internet"
			echo "     └─ Less secure, but convenient for remote access"
			echo ""
			echo "  3) ⚙️  Choose restrictions per service (ADVANCED)"
			echo "     └─ Configure each service individually"
			echo "     └─ Recommended for experienced users"
			echo ""
			read -rp "Choice [1-3] (press Enter for '1'): " choice
			choice="${choice:-1}"

			case "$choice" in
			1)
				FIREWALL_RESTRICT_MODE="restrict"
				log "Restricting all services to LAN + VPN access only."
				restrict_services_to_lan_vpn "${restrictable_services[@]}"
				;;
			2)
				FIREWALL_RESTRICT_MODE="open"
				log "Services will be open to all networks."
				;;
			3)
				FIREWALL_RESTRICT_MODE="custom"
				configure_per_service_restrictions "${restrictable_services[@]}"
				;;
			*)
				warn "Invalid choice. Using default (restrict all)."
				FIREWALL_RESTRICT_MODE="restrict"
				restrict_services_to_lan_vpn "${restrictable_services[@]}"
				;;
			esac
		else
			log "Non-interactive mode: Using existing or default security configuration."

			# Apply existing configuration in non-interactive mode
			case "$FIREWALL_RESTRICT_MODE" in
			"restrict")
				restrict_services_to_lan_vpn "${restrictable_services[@]}"
				;;
			"custom")
				if [[ ${#RESTRICTED_SERVICES[@]} -gt 0 ]]; then
					restrict_services_to_lan_vpn "${RESTRICTED_SERVICES[@]}"
				fi
				;;
			esac
		fi
		;;
	"restrict")
		log "Restricting all services to LAN + VPN access only (from command line option)."
		restrict_services_to_lan_vpn "${restrictable_services[@]}"
		;;
	"open")
		log "Services will be open to all networks (from command line option)."
		;;
	"custom")
		if [[ ${#RESTRICTED_SERVICES[@]} -gt 0 ]]; then
			log "Applying custom service restrictions (from command line option)."
			restrict_services_to_lan_vpn "${RESTRICTED_SERVICES[@]}"
		else
			warn "Custom restriction mode specified but no services listed. Using open mode."
		fi
		;;
	esac
}

# Configure restrictions for individual services interactively
configure_per_service_restrictions() {
	local services=("$@")
	local services_to_restrict=()

	echo ""
	echo "========================================"
	echo "     PER-SERVICE CONFIGURATION"
	echo "========================================"
	echo ""
	echo "Configure access restrictions for each selected service:"
	echo ""

	for service in "${services[@]}"; do
		local service_emoji="⚙️ "
		local recommendation=""
		local default_restrict="Y/n"  # Most services default to restricted
		
		# Get service description for better context
		local svc_file=""
		if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${service}.conf" ]]; then
			svc_file="${SCRIPT_DIR%/scripts}/services/user/${service}.conf"
		fi
		
		if [[ -n "$svc_file" ]]; then
			local desc
			desc=$(get_service_config_value "$svc_file" "description")
			if [[ -n "$desc" ]]; then
				recommendation=" ($desc)"
			fi
		fi
		
		# Check service configuration for access patterns
		local default_restrict="Y/n"  # Most services default to restricted
		local remote_access
		remote_access=$(get_service_config_value "$svc_file" "remote_access")
		local requires_media
		requires_media=$(get_service_config_value "$svc_file" "requires_media")
		
		# Services with remote_access=true or media services default to open
		if [[ "$remote_access" == "true" ]] || [[ "$requires_media" == "true" ]] || [[ "$desc" == *"media"* ]] || [[ "$desc" == *"healthcare data processing"* ]]; then
			default_restrict="y/N"  # Default to open for these services
			recommendation="${recommendation} (often accessed remotely)"
		fi

		read -rp "${service_emoji} Restrict ${service^} to LAN + VPN only? [${default_restrict}]${recommendation}: " ans

		if [[ "$default_restrict" == "y/N" ]]; then
			# Default to 'no' for media services since they're often accessed remotely
			if [[ "${ans,,}" =~ ^(y|yes)$ ]]; then
				services_to_restrict+=("$service")
				log "Will restrict $service to LAN + VPN access."
			else
				log "Will leave $service open to all networks."
			fi
		else
			# Default to 'yes' for other services (more secure)
			if [[ "${ans,,}" =~ ^(n|no)$ ]]; then
				log "Will leave $service open to all networks."
			else
				services_to_restrict+=("$service")
				log "Will restrict $service to LAN + VPN access."
			fi
		fi
	done

	echo ""
	echo "Note: WireGuard is skipped automatically (VPN entry point must remain publicly accessible)"
	echo ""

	# Save the selected restrictions to global array
	RESTRICTED_SERVICES=("${services_to_restrict[@]}")

	if [[ ${#services_to_restrict[@]} -gt 0 ]]; then
		restrict_services_to_lan_vpn "${services_to_restrict[@]}"
	fi
}

# Apply firewall restrictions to specified services
# <AUTOGEN-RESTRICT-SERVICES-START>
restrict_services_to_lan_vpn() {
	local services=("$@")

	if [[ $DRY_RUN == true ]]; then
		log "[DRY-RUN] Would restrict services to LAN + VPN: ${services[*]}"
		return
	fi

        # Define network subnets
        local lan_subnet="$LAN_SUBNET" # Broader LAN range to cover most home networks
        local vpn_subnet="$VPN_SUBNET"

	# Auto-detect physical LAN subnet (not Docker networks)
	if command -v ip &>/dev/null; then
		local detected_lan
		# Exclude Docker networks and focus on physical LAN interfaces
		detected_lan=$(ip route | grep -E '^192\.168\.|^10\.' | grep -v docker | grep -v "$vpn_subnet" | head -n1 | awk '{print $1}' 2>/dev/null || echo "")
		if [[ -n "$detected_lan" && "$detected_lan" != "$vpn_subnet" ]]; then
			lan_subnet="$detected_lan"
			log "Auto-detected LAN subnet: $lan_subnet"
		fi
	fi
	
	# Add Docker network subnet to allowed subnets for container-to-container communication
	local docker_subnet=""
	if [[ -n "${DOCKER_NETWORK_SUBNET:-}" ]]; then
		docker_subnet="$DOCKER_NETWORK_SUBNET"
		log "Using Docker network subnet: $docker_subnet"
	fi

	# Check firewall availability upfront
	local use_ufw=false
	local use_iptables=false
	
	if command -v ufw &>/dev/null; then
		# Use timeout to prevent hangs and more robust status check
		local ufw_status
		if ufw_status=$(timeout 10 sudo ufw status 2>/dev/null); then
			if [[ "$ufw_status" == *"Status: active"* ]]; then
				use_ufw=true
				log "UFW is active - will use UFW for firewall restrictions"
			else
				log "UFW is installed but inactive - falling back to iptables"
			fi
		else
			log "UFW status check failed or timed out - falling back to iptables"
		fi
	fi
	
	if [[ "$use_ufw" == "false" ]] && command -v iptables &>/dev/null; then
		use_iptables=true
		log "Using iptables for firewall restrictions"
	fi
	
	if [[ "$use_ufw" == "false" && "$use_iptables" == "false" ]]; then
		warn "Neither UFW nor iptables available - cannot apply firewall restrictions"
		return
	fi

	for service in "${services[@]}"; do
		local port=""
		local protocol="tcp"

		# Skip WireGuard - it must remain publicly accessible as VPN entry point
		if [[ "$service" == "wireguard" ]]; then
			log "Skipping firewall restrictions for $service (VPN entry point must remain accessible)"
			continue
		fi

		# Get port from service configuration dynamically
		if [[ -n "${CONTAINER_PORTS[$service]:-}" ]]; then
			port="${CONTAINER_PORTS[$service]}"
		else
			# Try to get port from service config file
			local svc_file="${SCRIPT_DIR%/scripts}/services/user/${service}.conf"
			if [[ -f "$svc_file" ]]; then
				port=$(get_service_config_value "$svc_file" "port")
			fi
		fi
		
		# Parse complex port formats (e.g., "3000:3000", "51820:51820/udp")
		if [[ "$port" =~ ^([0-9]+):([0-9]+)(/udp|/tcp)?$ ]]; then
			# Format: hostport:containerport[/protocol]
			port="${BASH_REMATCH[1]}"  # Use the host port
			if [[ -n "${BASH_REMATCH[3]}" ]]; then
				protocol="${BASH_REMATCH[3]#/}"  # Remove leading slash
			fi
		elif [[ "$port" =~ ^([0-9]+)(/udp|/tcp)?$ ]]; then
			# Format: port[/protocol]
			port="${BASH_REMATCH[1]}"
			if [[ -n "${BASH_REMATCH[2]}" ]]; then
				protocol="${BASH_REMATCH[2]#/}"  # Remove leading slash
			fi
		fi
		
		# Check if service uses UDP protocol (fallback check for service-specific config)
		if [[ "$protocol" == "tcp" ]] && [[ -n "$svc_file" && -f "$svc_file" ]] && grep -q "udp" "$svc_file" 2>/dev/null; then
			protocol="udp"
		fi

		if [[ -z "$port" || ! "$port" =~ ^[0-9]+$ ]]; then
			warn "No valid port configured for service: $service (got: ${CONTAINER_PORTS[$service]:-})"
			continue
		fi

		log "Restricting $service (port $port) to LAN ($lan_subnet) and VPN ($vpn_subnet) access only..."

		if [[ "$use_ufw" == "true" ]]; then
			# Use UFW (already confirmed active)
			# Remove any existing open rule for this port
			sudo ufw --force delete allow "$port/$protocol" 2>/dev/null || true

			# Add restricted rules
			if sudo ufw allow from "$lan_subnet" to any port "$port" proto "$protocol" 2>/dev/null; then
				log "Added UFW LAN rule for $service"
			else
				warn "Failed to add UFW LAN rule for $service"
			fi
			
			if sudo ufw allow from "$vpn_subnet" to any port "$port" proto "$protocol" 2>/dev/null; then
				log "Added UFW VPN rule for $service"
			else
				warn "Failed to add UFW VPN rule for $service"
			fi
			
			# Allow Docker network access if configured
			if [[ -n "$docker_subnet" ]]; then
				if sudo ufw allow from "$docker_subnet" to any port "$port" proto "$protocol" 2>/dev/null; then
					log "Added UFW Docker network rule for $service"
				else
					warn "Failed to add UFW Docker network rule for $service"
				fi
			fi

			log "Applied UFW restrictions for $service on port $port"
		elif [[ "$use_iptables" == "true" ]]; then
			# Use iptables
			# Remove any existing unrestricted ACCEPT rules for this port
			sudo iptables -D INPUT -p "$protocol" --dport "$port" -j ACCEPT 2>/dev/null || true

			# Allow LAN access
			if ! sudo iptables -C INPUT -p "$protocol" -s "$lan_subnet" --dport "$port" -j ACCEPT 2>/dev/null; then
				if sudo iptables -A INPUT -p "$protocol" -s "$lan_subnet" --dport "$port" -j ACCEPT 2>/dev/null; then
					log "Added iptables LAN rule for $service"
				else
					warn "Failed to add LAN iptables rule for $service"
				fi
			fi

			# Allow VPN access
			if ! sudo iptables -C INPUT -p "$protocol" -s "$vpn_subnet" --dport "$port" -j ACCEPT 2>/dev/null; then
				if sudo iptables -A INPUT -p "$protocol" -s "$vpn_subnet" --dport "$port" -j ACCEPT 2>/dev/null; then
					log "Added iptables VPN rule for $service"
				else
					warn "Failed to add VPN iptables rule for $service"
				fi
			fi

			# Allow Docker network access if configured
			if [[ -n "$docker_subnet" ]]; then
				if ! sudo iptables -C INPUT -p "$protocol" -s "$docker_subnet" --dport "$port" -j ACCEPT 2>/dev/null; then
					if sudo iptables -A INPUT -p "$protocol" -s "$docker_subnet" --dport "$port" -j ACCEPT 2>/dev/null; then
						log "Added iptables Docker network rule for $service"
					else
						warn "Failed to add Docker network iptables rule for $service"
					fi
				fi
			fi

			# Drop all other access to this port
			if ! sudo iptables -C INPUT -p "$protocol" --dport "$port" -j DROP 2>/dev/null; then
				if sudo iptables -A INPUT -p "$protocol" --dport "$port" -j DROP 2>/dev/null; then
					log "Added iptables DROP rule for $service"
				else
					warn "Failed to add DROP rule for $service"
				fi
			fi

			log "Applied iptables restrictions for $service on port $port"

			# Save iptables rules if possible
			if command -v netfilter-persistent &>/dev/null; then
				sudo netfilter-persistent save 2>/dev/null || warn "Failed to save iptables rules with netfilter-persistent"
			elif [[ -d /etc/iptables ]]; then
				sudo iptables-save | sudo tee /etc/iptables/rules.v4 >/dev/null 2>&1 || warn "Could not save iptables rules to /etc/iptables/rules.v4"
			fi
		fi
        done
}
# <AUTOGEN-RESTRICT-SERVICES-END>

# ----------------- Compose Lint Helper -----------------
lint_compose() {
        local cmd=(docker compose)
        if ! command -v docker &>/dev/null || ! docker compose version &>/dev/null; then
                if command -v docker-compose &>/dev/null; then
                        cmd=(docker-compose)
                else
                        warn "docker-compose not found; skipping compose lint"
                        return 0
                fi
        fi

        if "${cmd[@]}" -f "$COMPOSE_FILE" config -q; then
                log "Compose file syntax valid"
        else
                warn "Compose file syntax errors detected"
                return 1
        fi
        if command -v yamllint &>/dev/null; then
                yamllint -d relaxed "$COMPOSE_FILE" || warn "yamllint issues detected"
        fi
        return 0
}

# ----------------- Lint Myself: Use allowlist wrapper -----------------
lint_myself() {
	# Run ShellCheck with allowlist wrapper on this script (local linting).
	if ! command -v shellcheck &>/dev/null; then
		die "'shellcheck' not found. Please install to use --lint." 20
	fi
	if [[ -x "$SCRIPT_DIR/../.github/scripts/shellcheck-allowlist.sh" ]]; then
		if "$SCRIPT_DIR/../.github/scripts/shellcheck-allowlist.sh" "$0"; then
			log "ShellCheck passed."
		else
			die "ShellCheck failed." 21
		fi
	else
		if shellcheck -x "$0"; then
			log "ShellCheck passed."
		else
			die "ShellCheck failed." 21
		fi
	fi
	exit 0
}

# ----------------- Self-Update Function -----------------
self_update() {
	# Download and replace this script with the latest version from GitHub
	log "Checking for script updates..."

	if [[ -z "${SELF_UPDATE_URL:-}" ]]; then
		warn "SELF_UPDATE_URL not configured, skipping self-update"
		return 0
	fi

	local temp_script="/tmp/clinic-bootstrap-update.sh"
	local current_script="${BASH_SOURCE[0]}"

	if [[ "$DRY_RUN" == "true" ]]; then
		log "[DRY-RUN] Would download latest script from: $SELF_UPDATE_URL"
		log "[DRY-RUN] Would update: $current_script"
		return 0
	fi

	# Download the latest version
	if ! curl -sSf -o "$temp_script" "$SELF_UPDATE_URL"; then
		warn "Failed to download script update from $SELF_UPDATE_URL"
		return 1
	fi

	# Verify the downloaded script has a valid shebang
	if ! head -n1 "$temp_script" | grep -q "^#!/.*bash"; then
		warn "Downloaded script appears invalid (no bash shebang)"
		rm -f "$temp_script"
		return 1
	fi

	# Check if there's actually an update
	if cmp -s "$current_script" "$temp_script"; then
		log "Script is already up to date"
		rm -f "$temp_script"
		return 0
	fi

	# Create backup of current script
	local backup_script
	backup_script="${current_script}.backup.$(date +%Y%m%d-%H%M%S)"
	if ! cp "$current_script" "$backup_script"; then
		warn "Failed to create backup, aborting update"
		rm -f "$temp_script"
		return 1
	fi

	# Replace current script with updated version
	if chmod +x "$temp_script" && mv "$temp_script" "$current_script"; then
		log "✅ Script updated successfully!"
		log "Backup saved to: $backup_script"
		log "Restarting with updated script..."

		# Re-execute with the same arguments
		exec "$current_script" "$@"
	else
		warn "Failed to update script, restoring backup"
		mv "$backup_script" "$current_script" 2>/dev/null || true
		rm -f "$temp_script"
		return 1
	fi
}

generate_summary() {
	# Generate and display a summary of the deployed services
	# Ensure first-time setup logic is executed
	local summary_content=""

	summary_content+="# Homelab Bootstrap Summary\n\n"
	summary_content+="Generated on: $(date)\n"
	summary_content+="Script Version: $SCRIPT_VERSION\n\n"

	echo ""
	echo "🎉 Homelab Bootstrap Complete!"
	echo "================================"
	echo ""

	summary_content+="## Deployed Services\n\n"

	# Show container information
	echo "📦 Deployed Services:"
	for container in "${SELECTED_CONTAINERS[@]}"; do
		# Skip empty container names
		[[ -z "$container" ]] && continue

		local desc="${CONTAINER_DESCRIPTIONS[$container]:-Unknown service}"
		local port="${CONTAINER_PORTS[$container]:-N/A}"
		local status
		status="$(docker ps --filter "name=^/${container}$" --format '{{.Status}}' | head -n1 || echo "Not running")"

		echo "  • ${container^}: $desc"
		echo "    Port: $port | Status: $status"

		summary_content+="- **${container^}**: $desc\n"
		summary_content+="  - Port: $port\n"
		summary_content+="  - Status: $status\n"

		# Show domain access if configured
		if [[ "${TRAEFIK_DOMAIN_MODE:-local}" != "local" && -n "${TRAEFIK_DOMAIN_NAME:-}" ]]; then
			# Skip services that don't get Traefik routing
		case "${TRAEFIK_DOMAIN_MODE:-local}" in
		"local" | "vpn-only")
			if [[ "${TRAEFIK_DOMAIN_MODE:-local}" == "vpn-only" ]]; then
				echo "  Mode: VPN-only (dashboard access only)"
				echo "  Access: http://$(get_server_ip):port (LAN/VPN only)"  # Use function instead of hardcode
				summary_content+="- **Mode**: VPN-only (dashboard access only)\n"
				summary_content+="- **Access**: http://$(get_server_ip):port (LAN/VPN only)\n"
			else
				echo "  Mode: Local development (no domain routing)"
				echo "  Access: http://your-server-ip:port"
				summary_content+="- **Mode**: Local development (no domain routing)\n"
				summary_content+="- **Access**: http://your-server-ip:port\n"
			fi
			;;
			esac
		fi
		summary_content+="\n"
	done

	echo ""
	echo "🌐 Traefik Configuration:"
	summary_content+="\n## Traefik Configuration\n\n"

case "${TRAEFIK_DOMAIN_MODE:-local}" in
"local")
    echo "  Mode: Local development (no domain routing)"
    echo "  Access: http://your-server-ip:port"
    summary_content+="- **Mode**: Local development (no domain routing)\n"
    summary_content+="- **Access**: http://your-server-ip:port\n"
    ;;
	"vpn-only")
		echo "  Mode: VPN-only (dashboard access only)"
		echo "  Domain: ${TRAEFIK_DOMAIN_NAME:-Not configured}"
		echo "  Access: https://service.${TRAEFIK_DOMAIN_NAME:-yourdomain} (VPN clients only)"
		summary_content+="- **Mode**: VPN-only (dashboard access only)\n"
		summary_content+="- **Domain**: ${TRAEFIK_DOMAIN_NAME:-Not configured}\n"
		summary_content+="- **Access**: https://service.${TRAEFIK_DOMAIN_NAME:-yourdomain} (VPN clients only)\n"
		;;
	"ddns")
		echo "  Mode: Dynamic DNS"
		echo "  Domain: ${TRAEFIK_DOMAIN_NAME:-Not configured}"
		echo "  SSL: Automatic from Let's Encrypt"
		echo "  Access: https://service.${TRAEFIK_DOMAIN_NAME:-yourdomain}"
		summary_content+="- **Mode**: Dynamic DNS\n"
		summary_content+="- **Domain**: ${TRAEFIK_DOMAIN_NAME:-Not configured}\n"
		summary_content+="- **SSL**: Automatic from Let's Encrypt\n"
		summary_content+="- **Access**: https://service.${TRAEFIK_DOMAIN_NAME:-yourdomain}\n"
		;;
	"hostfile")
		echo "  Mode: Local DNS (hosts file)"
		echo "  Domain: ${TRAEFIK_DOMAIN_NAME:-Not configured}"
		echo "  SSL: Let's Encrypt (if publicly accessible)"
		echo "  Access: https://service.${TRAEFIK_DOMAIN_NAME:-yourdomain}"
		summary_content+="- **Mode**: Local DNS (hosts file)\n"
		summary_content+="- **Domain**: ${TRAEFIK_DOMAIN_NAME:-Not configured}\n"
		summary_content+="- **SSL**: Let's Encrypt (if publicly accessible)\n"
		summary_content+="- **Access**: https://service.${TRAEFIK_DOMAIN_NAME:-yourdomain}\n"
		;;
	esac

	if [[ "${TRAEFIK_DOMAIN_MODE:-local}" != "local" ]]; then
		echo "  Email: ${TRAEFIK_ACME_EMAIL:-Not configured}"
		summary_content+="- **Email**: ${TRAEFIK_ACME_EMAIL:-Not configured}\n"
	fi

	echo ""
	echo "🔧 Configuration saved to: $CONFIG_FILE"
	echo "📊 Traefik dashboard: http://localhost:${CONTAINER_PORTS[traefik]:-8080}"
	echo ""
	echo "💡 Next steps:"
	echo "  1. Configure your services through their web interfaces"
	echo "  2. Set up monitoring dashboards in Grafana"
	echo "  3. Add WireGuard clients for secure remote access"

	summary_content+="\n## Configuration\n\n"
	summary_content+="- **Config File**: $CONFIG_FILE\n"
	summary_content+="- **Traefik Dashboard**: http://localhost:${CONTAINER_PORTS[traefik]:-8080}\n"
	summary_content+="\n## Next Steps\n\n"
	summary_content+="1. Configure your services through their web interfaces\n"
	summary_content+="2. Set up monitoring dashboards in Grafana\n"
	summary_content+="3. Add WireGuard clients for secure remote access\n"

	if [[ "${TRAEFIK_DOMAIN_MODE:-local}" == "ddns" ]]; then
		echo "  4. Update your DNS provider to point to this server"
		summary_content+="4. Update your DNS provider to point to this server\n"
	fi

	# Write summary to file using SUMMARY_FILE variable
	if [[ -n "${SUMMARY_FILE:-}" ]]; then
		echo -e "$summary_content" >"$SUMMARY_FILE"
		log "📄 Summary documentation written to: $SUMMARY_FILE"
	fi

	echo ""
	return 0
}

# Setup Traefik configuration (called when requires_setup=traefik_config)
setup_traefik_config() {
	log "🔧 Setting up Traefik configuration..."
	
	# Basic traefik configuration
	local config_dir="${CFG_ROOT}/traefik-config"
	mkdir -p "$config_dir/dynamic"
	set_ownership "$config_dir"
	
	# Generate basic static configuration
	cat > "$config_dir/traefik.yml" <<EOF
# Basic Traefik Configuration
# Generated by CLINIC Bootstrap System

api:
  dashboard: true

entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: ${DOCKER_NETWORK_NAME:-intelluxe-net}
  file:
    directory: /etc/traefik/dynamic
    watch: true

log:
  level: INFO
EOF

	case "${TRAEFIK_DOMAIN_MODE:-local}" in
		"ddns"|"hostfile")
			cat >> "$config_dir/traefik.yml" <<EOF

# HTTPS and Let's Encrypt
certificatesResolvers:
  letsencrypt:
    acme:
      tlsChallenge: {}
      email: ${TRAEFIK_ACME_EMAIL:-admin@example.com}
      storage: /data/acme.json
      caServer: https://acme-v02.api.letsencrypt.org/directory

# HTTP to HTTPS redirect
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entrypoint:
          to: websecure
          scheme: https
          permanent: true
EOF
			;;
	esac
	
	log "📄 Generated Traefik configuration: $config_dir/traefik.yml"
	return 0
}

# Entry point for the script
main() {
	print_banner

	if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
		echo "Welcome to the Robust Docker Homelab Bootstrapper!"
		echo "For guided help, see the README or run ./clinic-bootstrap.sh --help"
	fi

	check_permissions || {
		fail "check_permissions failed"
		exit 1
	}
	check_docker_socket || {
		fail "check_docker_socket failed"
		exit 1
	}

	# Check for auto-install dependencies function
	if command -v auto_install_deps &>/dev/null; then
		auto_install_deps || {
			fail "auto_install_deps failed"
			exit 1
		}
	else
		warn "auto_install_deps function not found, continuing without dependency check"
	fi

        if ! docker info >/dev/null 2>&1; then
                fail "Docker daemon is not running. Please start Docker and try again."
                exit 110
        fi

        # Only require root for operations that actually need it
        local needs_root=false
        
        # Check if we need root for specific operations
        if [[ "${INSTALL_PACKAGES:-false}" == "true" ]] || \
           [[ "${SETUP_FIREWALL:-false}" == "true" ]] || \
           [[ "${MODIFY_HOSTS:-false}" == "true" ]] || \
           [[ ! -w "/etc/wireguard" && -d "/etc/wireguard" ]]; then
            needs_root=true
        fi
        
        if $needs_root && ((EUID != 0)) && [[ "$DRY_RUN" != "true" ]]; then
            fail "This operation requires root privileges. Please run with sudo."
            exit 100
        fi
        
        # For normal operations, just note we're running as user
        if ((EUID != 0)); then
            log "Running as user (recommended). Will request sudo only if needed for specific operations."
        fi

	rotate_log_if_needed || {
		fail "rotate_log_if_needed failed"
		exit 1
	}
	ensure_directories || {
		fail "ensure_directories failed"
		exit 1
	}
        apply_env_overrides || {
                fail "apply_env_overrides failed"
                exit 1
        }

        if [[ -n "$STOP_SERVICE" ]]; then
                stop_service "$STOP_SERVICE"
                exit 0
        fi

        if [[ "$WG_DOWN" == "true" ]]; then
                # Handle --wg-down flag to disable the WireGuard interface
                stop_wireguard
                exit 0
        fi

        if [[ "$RESET_WG_KEYS" == "true" ]]; then
                reset_wireguard_keys
                exit 0
        fi

	if [[ -n "${RESTORE_BACKUP_FILE:-}" ]]; then
		verify_backup "$RESTORE_BACKUP_FILE" || {
			fail "verify_backup failed"
			exit 1
		}
		restore_backup "$RESTORE_BACKUP_FILE" || {
			fail "restore_backup failed"
			exit 1
		}
		ok "Restored from backup $RESTORE_BACKUP_FILE. Exiting."
		exit 0
	fi

        if [[ "${VALIDATE_ONLY:-false}" == "true" ]]; then
                validate_config
                exit 0
        fi

	backup_compose_yml || {
		fail "backup_compose_yml failed"
		exit 1
	}

	# Port configuration - only prompt if first run or user wants to change
	local config_exists=false
	if [[ -f "$CONFIG_FILE" ]] && grep -q "SELECTED_CONTAINERS" "$CONFIG_FILE" 2>/dev/null; then
		config_exists=true
	fi

	if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
		echo "Current port configuration:"
		show_ports
		echo ""
		read -rp "Would you like to update any ports? [y/N]: " ans
		if [[ "${ans,,}" =~ ^(y|yes)$ ]]; then
			# Dynamic port configuration for all discovered services
			for c in "${!CONTAINER_PORTS[@]}"; do
				proto="tcp"
				# Check if service uses UDP protocol
				local svc_file=""
				if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${c}.conf" ]]; then
					svc_file="${SCRIPT_DIR%/scripts}/services/user/${c}.conf"
				fi
				
				if [[ "$c" == "wireguard" ]] || [[ -n "$svc_file" && -f "$svc_file" ]] && grep -q "udp" "$svc_file" 2>/dev/null; then
					proto="udp"
				fi
				
				prompt_for_port "$c" "${CONTAINER_PORTS[$c]}" "$proto"
			done
		else
			log "Using existing port configuration."
		fi
	else
		log "Using existing port configuration in non-interactive mode."
	fi

	# Configure media drives after port configuration but before container selection
	configure_media_drives || {
		fail "configure_media_drives failed"
		exit 1
	}

	save_config || {
		fail "save_config failed (after port and media configuration)"
		exit 1
	}

	if [[ -n "${ACTION_FLAG:-}" && -n "${ACTION_CONTAINER:-}" ]]; then
		container_action "$ACTION_FLAG" "$ACTION_CONTAINER"
		exit 0
	fi

	if ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
		echo "Would you like to manage containers interactively? [y/N]"  # Changed default
		if [[ -t 0 ]]; then
			read -r reply
		else
			log "Non-interactive mode detected. Defaulting to 'No'."
			reply="n"
		fi
		# Changed logic - default is now 'no'
		if [[ "${reply,,}" =~ ^(y|yes)$ ]]; then
			container_menu
		fi
	else
		log "Skipping interactive container management in non-interactive mode."
	fi

	if [[ "${SKIP_CONTAINER_SELECTION:-false}" != "true" ]]; then
		choose_containers || {
			fail "choose_containers failed"
			exit 1
		}
	else
		log "Skipping container selection (user quit menu)"
		# Use existing selection or all containers
		if [[ -z "${SELECTED_CONTAINERS[*]:-}" ]]; then
			SELECTED_CONTAINERS=("${ALL_CONTAINERS[@]}")
			log "No previous selection found. Using all containers."
		fi
	fi

	# Configure domain settings for services that support it
	local has_domain_services=false
	for container in "${SELECTED_CONTAINERS[@]}"; do
		local svc_file=""
		if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
			svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
		fi
		
		if [[ -n "$svc_file" ]]; then
			local supports_domains
			supports_domains=$(get_service_config_value "$svc_file" "supports_domains")
			if [[ "$supports_domains" == "true" ]]; then
				has_domain_services=true
				break
			fi
		fi
	done
	
	if $has_domain_services; then
		configure_traefik_domain || {
			fail "configure_traefik_domain failed"
			exit 1
		}
	fi
	# Handle pre-start container cleanup and port conflict resolution
	for container in "${SELECTED_CONTAINERS[@]}"; do
		# Clean up existing containers to avoid port conflicts
		local svc_file=""
		if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
			svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
		fi
		
		# Always cleanup containers to avoid port conflicts during restart
		if docker ps -q --filter "name=^/${container}$" | grep -q .; then
			log "Stopping existing $container container to avoid port conflicts..."
			docker stop "$container" >/dev/null 2>&1 || true
		fi
		if docker ps -aq --filter "name=^/${container}$" | grep -q .; then
			docker rm "$container" >/dev/null 2>&1 || true
			log "Removed existing $container container"
		fi
		
		# Basic port conflict warning (simplified for now)
		local conflict_port
		conflict_port=$(get_service_config_value "$svc_file" "conflict_port")
		if [[ -n "$conflict_port" ]] && check_port_in_use "$conflict_port" tcp; then
			warn "Port $conflict_port is in use. $container may fail to start."
			show_port_usage "$conflict_port"
		fi
	done

	# Check for services using host networking on non-Linux systems
	if [[ "$(uname)" != "Linux" ]]; then
		for container in "${SELECTED_CONTAINERS[@]}"; do
			local svc_file=""
			if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
				svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
			fi
			
			if [[ -n "$svc_file" ]]; then
				local network_mode
				network_mode=$(get_service_config_value "$svc_file" "network_mode")
				if [[ "$network_mode" == "host" ]]; then
					warn "$container uses host networking, which is only fully supported on Linux. Health checks may be skipped."
				fi
			fi
		done
	fi

	# Handle services that require special setup
	for container in "${SELECTED_CONTAINERS[@]}"; do
		local svc_file=""
		if [[ -f "${SCRIPT_DIR%/scripts}/services/user/${container}.conf" ]]; then
			svc_file="${SCRIPT_DIR%/scripts}/services/user/${container}.conf"
		fi
		
		if [[ -n "$svc_file" ]]; then
			local requires_setup
			requires_setup=$(get_service_config_value "$svc_file" "requires_setup")
			
			case "$requires_setup" in
				wireguard_keys)
					# WireGuard-specific setup logic
					if [[ -z "$WG_DIR" || "$WG_DIR" == *"directory"* ]]; then
						WG_DIR="/etc/wireguard"
						log "Setting WG_DIR to default: $WG_DIR"
					else
						log "Using existing WG_DIR: $WG_DIR"
					fi

					# Ensure directories exist
					mkdir -p "$WG_DIR"
					WG_CLIENTS_DIR="${WG_DIR}/clients"
					mkdir -p "$WG_CLIENTS_DIR"
					set_ownership "$WG_DIR" "$WG_CLIENTS_DIR"
					log "WireGuard directories set up: $WG_DIR and $WG_CLIENTS_DIR"

					# Check if this is first-time WG_DIR configuration
					local wg_config_exists=false
					if [[ -f "$CONFIG_FILE" ]] && grep -q "WG_DIR=" "$CONFIG_FILE"; then
						wg_config_exists=true
						log "WG_DIR already configured in $CONFIG_FILE."
					fi

					# Prompt for WG_DIR path in interactive mode (first time only)
					if ! $wg_config_exists && ! $NON_INTERACTIVE && ! $FORCE_DEFAULTS; then
						prompt_for_path WG_DIR "/etc/wireguard" "WireGuard key directory"
						WG_CLIENTS_DIR="${WG_DIR}/clients"
						mkdir -p "$WG_DIR" "$WG_CLIENTS_DIR"
						set_ownership "$WG_DIR" "$WG_CLIENTS_DIR"
						log "Updated WireGuard directories: $WG_DIR and $WG_CLIENTS_DIR"
					fi

					# Setup WireGuard keys and configuration
					setup_wireguard_keys || {
						fail "setup_wireguard_keys failed"
						exit 1
					}
					;;
				traefik_config)
					setup_traefik_config || {
						fail "setup_traefik_config failed"
						exit 1
					}
					;;
				*)
					# No special setup required
					;;
			esac
		fi
	done

		ensure_docker_network "$DOCKER_NETWORK_NAME" "$DOCKER_NETWORK_SUBNET" || {
		fail "ensure_docker_network failed"
		exit 1
	}

	for container in "${SELECTED_CONTAINERS[@]}"; do
		ensure_container_running "$container" || {
			fail "ensure_container_running $container failed"
			exit 1
		}
	done

	# Configure firewall rules for the containers
	configure_firewall || {
		fail "configure_firewall failed"
		exit 1
	}

	# Configure service restrictions based on user choice
	configure_service_restrictions

	save_config || {
		fail "save_config failed (final)"
		exit 1
	}
        generate_summary || {
                fail "generate_summary failed"
                exit 1
        }

        if [[ "$DRY_RUN" != true ]]; then
                enable_config_web_ui
        fi

        # Force mount setup if no configuration exists
        if [[ ! -f "$CONFIG_FILE" ]]; then
		log "No configuration file found. Forcing mount setup."
		configure_media_drives
	elif ! grep -q "MEDIA_DRIVES_ENABLED" "$CONFIG_FILE"; then
		log "No saved configuration for media drives. Forcing mount setup."
		configure_media_drives
	fi

	ok "Setup completed successfully. Version $SCRIPT_VERSION."

	# Inform user about available commands
	echo ""
	echo "🔧 To see available management commands, run: make help"
	echo ""
}

# Ensure the script's main function is called
# Run main only when executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
