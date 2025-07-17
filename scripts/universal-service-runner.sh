#!/bin/bash
# Universal Service Runner for CLINIC Bootstrap System
# This script can run ANY Docker service using only configuration files
# No service-specific code required!

# Source required libraries (only if not already sourced)
if ! command -v log_error >/dev/null 2>&1; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/lib.sh" 2>/dev/null || {
        # Fallback logging functions if lib.sh is not available
        log_error() { echo "[ERROR] $*" >&2; }
        log_warning() { echo "[WARNING] $*" >&2; }
        log_info() { echo "[INFO] $*" >&2; }
        log_success() { echo "[SUCCESS] $*" >&2; }
    }
    
    # Create function aliases for consistent naming
    if command -v log >/dev/null 2>&1; then
        log_info() { log "$@"; }
        log_error() { fail "$@"; }
        log_warning() { warn "$@"; }
        log_success() { ok "$@"; }
    fi
else
    # Functions already available, no need to source again
    true
fi

# Universal configuration-to-Docker argument mapping
# This data structure defines how config keys translate to Docker arguments
if [[ -z "${DOCKER_ARG_MAP:-}" ]]; then
declare -gA DOCKER_ARG_MAP=(
    # Basic container options
    ["image"]="direct"                    # Goes directly as the image name
    ["command"]="--"                      # Container command
    ["entrypoint"]="--entrypoint"
    ["working_dir"]="--workdir"
    ["user"]="--user"
    ["hostname"]="--hostname"
    
    # Network options
    ["network_mode"]="--network"
    ["static_ip"]="--ip"
    ["mac_address"]="--mac-address"
    ["link"]="--link"
    ["add_host"]="--add-host"
    ["dns"]="--dns"
    ["dns_search"]="--dns-search"
    ["dns_opt"]="--dns-opt"
    ["dns_option"]="--dns-option"
    ["enable_discovery"]="discovery_setup"
    ["discovery_ports"]="ignore"
    ["discovery_protocol"]="ignore"
    ["multicast_relay"]="ignore"
    
    # Port mappings
    ["port"]="port_mapping"               # Special handling for port mappings
    ["additional_ports"]="port_mapping"   # Special handling for additional port mappings
    ["expose"]="--expose"
    
    # Volume and storage
    ["volumes"]="volume_mapping"          # Special handling for volumes
    ["bind_mounts"]="volume_mapping"      # Bind mounts handled like volumes
    ["tmpfs"]="--tmpfs"
    ["mount"]="--mount"
    
    # Environment and labels
    ["env"]="env_mapping"                 # Special handling for environment variables
    ["env_file"]="--env-file"
    ["label"]="label_mapping"             # Special handling for labels
    ["labels"]="label_mapping"            # Special handling for labels (plural form)
    
    # Resource limits
    ["memory"]="--memory"
    ["memory_limit"]="--memory"           # Alternative name for memory
    ["memory_swap"]="--memory-swap"
    ["memory_reservation"]="--memory-reservation"
    ["cpus"]="--cpus"
    ["cpu_limit"]="--cpus"                # Alternative name for cpus
    ["cpu_shares"]="--cpu-shares"
    ["cpu_period"]="--cpu-period"
    ["cpu_quota"]="--cpu-quota"
    ["cpu_rt_period"]="--cpu-rt-period"
    ["cpu_rt_runtime"]="--cpu-rt-runtime"
    ["cpuset_cpus"]="--cpuset-cpus"
    ["cpuset_mems"]="--cpuset-mems"
    
    # Security options
    ["privileged"]="--privileged"
    ["security_opt"]="--security-opt"
    ["cap_add"]="--cap-add"
    ["cap_drop"]="--cap-drop"
    ["user_ns"]="--userns"
    ["group_add"]="--group-add"
    ["sysctls"]="sysctl_mapping"             # Special handling for sysctls
    
    # Runtime options
    ["runtime"]="--runtime"
    ["restart"]="--restart"
    ["restart_policy"]="--restart"           # Alternative name for restart
    ["rm"]="--rm"
    ["detach"]="--detach"
    ["interactive"]="--interactive"
    ["tty"]="--tty"
    ["init"]="--init"
    ["sig_proxy"]="--sig-proxy"
    
    # Health and logging
    ["health_cmd"]="--health-cmd"
    ["health_interval"]="--health-interval"
    ["health_timeout"]="--health-timeout"
    ["health_retries"]="--health-retries"
    ["health_start_period"]="--health-start-period"
    ["health_start_interval"]="--health-start-interval"
    ["healthcheck"]="healthcheck_mapping"     # Special handling for healthcheck commands
    ["log_driver"]="--log-driver"
    ["log_opt"]="--log-opt"
    
    # Documentation and metadata (ignored by Docker but useful for config)
    ["description"]="ignore"                 # Human-readable description - not passed to Docker
    ["port_notes"]="ignore"                  # Port documentation - not passed to Docker
    ["supports_domains"]="ignore"            # Domain routing support - not passed to Docker
    ["domain_routing"]="traefik_labels"      # Generate Traefik labels for domain routing
    ["extra_args"]="extra_args_mapping"      # Special handling for extra Docker arguments
    ["requires_setup"]="ignore"              # Setup requirements - not passed to Docker
    ["post_start_hook"]="ignore"             # Post-start hooks - handled separately, not passed to Docker
    
    # Device and hardware
    ["device"]="--device"
    ["device_cgroup_rule"]="--device-cgroup-rule"
    ["gpus"]="--gpus"
    ["ipc"]="--ipc"
    ["pid"]="--pid"
    ["uts"]="--uts"
    
    # Network and VPN options
    ["network"]="--network"
    ["net"]="--net"                       # Legacy network option
    ["publish"]="--publish"               # Alternative to port mapping
    ["publish_all"]="--publish-all"
    ["expose"]="--expose"
    ["network_alias"]="--network-alias"
    ["ip"]="--ip"
    ["ip6"]="--ip6"
    ["link_local_ip"]="--link-local-ip"
    
    # VPN and tunnel specific
    ["vpn"]="vpn_mapping"                 # Special VPN handling
    ["tun"]="--device=/dev/net/tun"       # Special handling for VPN containers
    ["net_admin"]="--cap-add=NET_ADMIN"   # Required for most VPN containers
    ["sys_module"]="--cap-add=SYS_MODULE" # Sometimes needed for VPN
    ["privileged_vpn"]="--privileged"     # Some VPN containers need full privileges
    
    # Storage and filesystem
    ["volumes_from"]="--volumes-from"
    ["read_only"]="boolean_flag:--read-only"
    ["storage_opt"]="--storage-opt"
    ["stop_signal"]="--stop-signal"
    ["stop_timeout"]="--stop-timeout"
    
    # Process and signal handling
    ["init"]="--init"
    ["sig_proxy"]="--sig-proxy"
    ["pid_file"]="--pidfile"
    ["cgroup_parent"]="--cgroup-parent"
    ["cgroup_ns"]="--cgroupns"
    
    # Advanced options
    ["ulimit"]="--ulimit"
    ["sysctl"]="--sysctl"
    ["shm_size"]="--shm-size"
    ["platform"]="--platform"
    ["pull"]="--pull"
    ["quiet"]="--quiet"
    ["annotation"]="--annotation"
    ["attach"]="--attach"
    ["cidfile"]="--cidfile"
    ["detach_keys"]="--detach-keys"
    ["disable_content_trust"]="--disable-content-trust"
    ["kernel_memory"]="--kernel-memory"
    ["oom_kill_disable"]="--oom-kill-disable"
    ["oom_score_adj"]="--oom-score-adj"
    ["pids_limit"]="--pids-limit"
    ["no_healthcheck"]="--no-healthcheck"
    ["isolation"]="--isolation"
    ["volume_driver"]="--volume-driver"
    ["volumes_from"]="--volumes-from"
    
    # Docker Compose compatibility
    ["depends_on"]="compose_depends"      # Special handling for depends_on
    ["external_links"]="--link"           # External container links
    
    # Swarm and orchestration
    ["replicas"]="--replicas"
    ["constraint"]="--constraint"
    ["placement_pref"]="--placement-pref"
    ["update_delay"]="--update-delay"
    ["update_failure_action"]="--update-failure-action"
    ["update_max_failure_ratio"]="--update-max-failure-ratio"
    ["update_monitor"]="--update-monitor"
    ["update_parallelism"]="--update-parallelism"
    ["rollback_delay"]="--rollback-delay"
    ["rollback_failure_action"]="--rollback-failure-action"
    ["rollback_max_failure_ratio"]="--rollback-max-failure-ratio"
    ["rollback_monitor"]="--rollback-monitor"
    ["rollback_parallelism"]="--rollback-parallelism"
    
    # Specialized container options
    ["autoremove"]="--rm"                 # Auto-remove container when it exits
    ["stdin_open"]="--interactive"        # Keep STDIN open
    ["pseudo_tty"]="--tty"               # Allocate a pseudo-TTY
    ["workdir"]="--workdir"              # Working directory inside container
    ["domainname"]="--domainname"        # Container domain name
    ["mac_address"]="--mac-address"      # Container MAC address
    ["memory_swappiness"]="--memory-swappiness"
    ["blkio_weight"]="--blkio-weight"
    ["blkio_weight_device"]="--blkio-weight-device"
    ["device_read_bps"]="--device-read-bps"
    ["device_read_iops"]="--device-read-iops"
    ["device_write_bps"]="--device-write-bps"
    ["device_write_iops"]="--device-write-iops"
)
fi

# Special handling functions for complex mappings
handle_port_mapping() {
    local port_spec="$1"
    local domain_routing="${2:-false}"
    local -a port_args=()
    
    # For services with domain_routing=true, skip ports 80 and 443 to avoid conflicts with Traefik
    if [[ "$domain_routing" == "true" ]]; then
        # Extract the host port from the specification
        local host_port=""
        if [[ "$port_spec" =~ ^[0-9]+$ ]]; then
            host_port="$port_spec"
        elif [[ "$port_spec" =~ ^([0-9]+):[0-9]+$ ]]; then
            host_port="${BASH_REMATCH[1]}"
        elif [[ "$port_spec" =~ ^[0-9.]+:([0-9]+):[0-9]+$ ]]; then
            host_port="${BASH_REMATCH[1]}"
        fi
        
        # Skip ports 80 and 443 for domain routing services
        if [[ "$host_port" == "80" || "$host_port" == "443" ]]; then
            return 0
        fi
    fi
    
    # Handle different port specification formats
    if [[ "$port_spec" =~ ^[0-9]+$ ]]; then
        # Simple port: "8080" -> "-p 8080:8080"
        port_args+=("-p" "$port_spec:$port_spec")
    elif [[ "$port_spec" =~ ^[0-9]+:[0-9]+$ ]]; then
        # Host:container: "8080:80" -> "-p 8080:80"
        port_args+=("-p" "$port_spec")
    elif [[ "$port_spec" =~ ^[0-9.]+:[0-9]+:[0-9]+$ ]]; then
        # IP:host:container: "127.0.0.1:8080:80" -> "-p 127.0.0.1:8080:80"
        port_args+=("-p" "$port_spec")
    else
        # Complex specification, pass as-is
        port_args+=("-p" "$port_spec")
    fi
    
    # Only print if we have arguments
    if [[ ${#port_args[@]} -gt 0 ]]; then
        printf '%s\n' "${port_args[@]}"
    fi
}

handle_volume_mapping() {
    local volume_spec="$1"
    local -a vol_args=()
    
    # Expand variables in volume specification
    local expanded_spec
    set +u  # Temporarily allow unbound variables for expansion
    expanded_spec=$(eval echo "\"$volume_spec\"" 2>/dev/null || echo "$volume_spec")
    set -u  # Re-enable unbound variable checking
    
    # Skip empty specs
    [[ -z "$expanded_spec" ]] && return 0
    
    # Handle different volume specification formats
    if [[ "$expanded_spec" =~ ^[^:]+:[^:]+$ ]]; then
        # host:container -> "-v host:container"
        vol_args+=("-v" "$expanded_spec")
    elif [[ "$expanded_spec" =~ ^[^:]+:[^:]+:[^:]+$ ]]; then
        # host:container:options -> "-v host:container:options"
        vol_args+=("-v" "$expanded_spec")
    elif [[ "$expanded_spec" =~ ^[^/].*$ ]]; then
        # Named volume -> "-v volume_name:container_path"
        vol_args+=("-v" "$expanded_spec")
    else
        # Pass as-is for other formats
        vol_args+=("-v" "$expanded_spec")
    fi
    
    # Only print if we have arguments
    if [[ ${#vol_args[@]} -gt 0 ]]; then
        printf '%s\n' "${vol_args[@]}"
    fi
}

handle_env_mapping() {
    local env_spec="$1"
    local -a env_args=()
    
    # Expand variables in environment specification
    local expanded_spec
    set +u  # Temporarily allow unbound variables for expansion
    expanded_spec=$(eval echo "\"$env_spec\"" 2>/dev/null || echo "$env_spec")
    set -u  # Re-enable unbound variable checking
    
    # Handle environment variable formats
    if [[ "$expanded_spec" =~ ^[A-Za-z_][A-Za-z0-9_]*=.*$ ]]; then
        # KEY=value format
        env_args+=("-e" "$expanded_spec")
    else
        # Just the key name (Docker will get value from host environment)
        env_args+=("-e" "$expanded_spec")
    fi
    
    # Only print if we have arguments
    if [[ ${#env_args[@]} -gt 0 ]]; then
        printf '%s\n' "${env_args[@]}"
    fi
}

handle_label_mapping() {
    local label_spec="$1"
    local -a label_args=()
    
    # Handle label formats
    if [[ "$label_spec" =~ ^[^=]+=.*$ ]]; then
        # key=value format
        label_args+=("--label" "$label_spec")
    else
        # Just the key
        label_args+=("--label" "$label_spec")
    fi
    
    # Only print if we have arguments
    if [[ ${#label_args[@]} -gt 0 ]]; then
        printf '%s\n' "${label_args[@]}"
    fi
}

handle_vpn_mapping() {
    local vpn_spec="$1"
    local -a vpn_args=()
    
    # Handle VPN-specific configurations
    case "$vpn_spec" in
        "true"|"yes"|"1")
            # Enable common VPN requirements
            vpn_args+=("--cap-add" "NET_ADMIN")
            vpn_args+=("--device" "/dev/net/tun")
            ;;
        "privileged")
            # Full privileged mode for complex VPN setups
            vpn_args+=("--privileged")
            vpn_args+=("--device" "/dev/net/tun")
            ;;
        *)
            # Custom VPN specification
            vpn_args+=("--cap-add" "NET_ADMIN")
            vpn_args+=("--device" "/dev/net/tun")
            ;;
    esac
    
    # Only print if we have arguments
    if [[ ${#vpn_args[@]} -gt 0 ]]; then
        printf '%s\n' "${vpn_args[@]}"
    fi
}

handle_compose_depends() {
    local depends_spec="$1"
    local -a depends_args=()
    
    # Docker run doesn't have direct depends_on equivalent
    # But we can add links to approximate the behavior
    if [[ "$depends_spec" =~ , ]]; then
        # Multiple dependencies
        IFS=',' read -ra dep_array <<< "$depends_spec"
        for dep in "${dep_array[@]}"; do
            depends_args+=("--link" "$dep:$dep")
        done
    else
        # Single dependency
        depends_args+=("--link" "$depends_spec:$depends_spec")
    fi
    
    # Only print if we have arguments
    if [[ ${#depends_args[@]} -gt 0 ]]; then
        printf '%s\n' "${depends_args[@]}"
    fi
}

handle_traefik_labels() {
    local domain_routing="$1"
    local service_name="$2"
    local service_port="$3"
    
    # Extract container port from port mapping (e.g., "3000:3000" -> "3000")
    if [[ "$service_port" =~ : ]]; then
        service_port="${service_port##*:}"  # Get everything after the last colon
    fi
    local -a label_args=()
    
    # Only generate labels if domain routing is enabled
    if [[ "$domain_routing" != "true" ]]; then
        return 0
    fi
    
    # Get Traefik configuration from environment or defaults
    local traefik_domain_mode="${TRAEFIK_DOMAIN_MODE:-local}"
    local traefik_domain_name="${TRAEFIK_DOMAIN_NAME:-}"
    
    # Generate labels based on domain mode
    case "$traefik_domain_mode" in
        "domain"|"ddns"|"hostfile")
            if [[ -n "$traefik_domain_name" ]]; then
                label_args+=("--label" "traefik.enable=true")
                label_args+=("--label" "traefik.http.routers.${service_name}.rule=Host(\`${service_name}.${traefik_domain_name}\`)")
                label_args+=("--label" "traefik.http.routers.${service_name}.entrypoints=web")
                label_args+=("--label" "traefik.http.services.${service_name}.loadbalancer.server.port=${service_port}")
                
                # Add LAN+VPN restriction middleware for all services
                label_args+=("--label" "traefik.http.routers.${service_name}.middlewares=lan-vpn-only")
            fi
            ;;
        "vpn-only")
            if [[ -n "$traefik_domain_name" ]]; then
                label_args+=("--label" "traefik.enable=true")
                label_args+=("--label" "traefik.http.routers.${service_name}.rule=Host(\`${service_name}.${traefik_domain_name}\`)")
                label_args+=("--label" "traefik.http.routers.${service_name}.entrypoints=web")
                label_args+=("--label" "traefik.http.services.${service_name}.loadbalancer.server.port=${service_port}")
                
                # Add LAN+VPN restriction middleware for all services
                label_args+=("--label" "traefik.http.routers.${service_name}.middlewares=lan-vpn-only")
                # VPN-only mode uses HTTP since it's internal
            fi
            ;;
        "local"|*)
            # No Traefik labels for local mode - direct port access
            ;;
    esac
    
    # Only print if we have arguments
    if [[ ${#label_args[@]} -gt 0 ]]; then
        printf '%s\n' "${label_args[@]}"
    fi
}

# Handle discovery protocols for healthcare AI servers and local network services
handle_discovery_setup() {
    local enable_discovery="${CONFIG[enable_discovery]:-false}"
    local discovery_ports="${CONFIG[discovery_ports]:-}"
    local discovery_protocol="${CONFIG[discovery_protocol]:-both}"
    local multicast_relay="${CONFIG[multicast_relay]:-false}"
    
    if [[ "$enable_discovery" != "true" ]]; then
        return
    fi
    
    log_info "Configuring discovery protocols for ${CONFIG[service_name]:-unknown}"
    
    # Auto-detect discovery ports based on service type if not specified
    if [[ -z "$discovery_ports" ]]; then
        local image="${CONFIG[image]:-}"
        case "$image" in
            *ollama*)
                discovery_ports="11434/tcp"
                ;;
            *agentcare*|*mcp*)
                discovery_ports="3000/tcp"
                ;;
            *homeassistant*|*hass*)
                discovery_ports="5353/udp,21063/tcp"
                ;;
            *)
                discovery_ports="1900/udp,5353/udp"
                ;;
        esac
        log_info "Auto-detected discovery ports: $discovery_ports"
    fi
    
    # Parse and add discovery ports to Docker command
    if [[ -n "$discovery_ports" ]]; then
        IFS=',' read -ra DPORTS <<< "$discovery_ports"
        for dport in "${DPORTS[@]}"; do
            dport=$(echo "$dport" | xargs)  # Trim whitespace
            # Check if port is already mapped
            local port_already_mapped=false
            for existing_arg in "${DOCKER_COMMAND[@]}"; do
                if [[ "$existing_arg" == "-p" ]] || [[ "$existing_arg" == "--publish" ]]; then
                    continue
                fi
                if [[ "$existing_arg" == *":$dport" ]] || [[ "$existing_arg" == "$dport:$dport" ]]; then
                    port_already_mapped=true
                    break
                fi
            done
            
            if [[ "$port_already_mapped" == "false" ]]; then
                DOCKER_COMMAND+=("-p" "$dport:$dport")
                log_info "Added discovery port mapping: $dport:$dport"
            fi
        done
    fi
    
    # Add host gateway for discovery protocols
    DOCKER_COMMAND+=("--add-host" "host.docker.internal:host-gateway")
    
    # Add capabilities for multicast relay if enabled
    if [[ "$multicast_relay" == "true" ]]; then
        DOCKER_COMMAND+=("--cap-add" "NET_ADMIN")
        DOCKER_COMMAND+=("--cap-add" "NET_RAW")
        log_info "Added multicast relay capabilities"
    fi
    
    log_info "Discovery configuration completed"
}

handle_extra_args_mapping() {
    local extra_args_spec="$1"
    local -a extra_args_array=()
    
    # Split extra args by spaces, being careful with quoted arguments
    # For now, use simple space splitting - can be enhanced later if needed
    IFS=' ' read -ra args_array <<< "$extra_args_spec"
    
    for arg in "${args_array[@]}"; do
        # Skip empty arguments
        [[ -z "$arg" ]] && continue
        
        # Add each argument to the Docker command
        extra_args_array+=("$arg")
    done
    
    printf '%s\n' "${extra_args_array[@]}"
}

# Auto-generate entrypoint.sh for Python services if missing
generate_default_entrypoint() {
    local app_dir="$1"
    local entrypoint_path="$app_dir/entrypoint.sh"
    local main_py="$app_dir/app.py"
    
    if [[ ! -f "$entrypoint_path" ]]; then
        if [[ -f "$main_py" ]]; then
            echo "#!/bin/bash" > "$entrypoint_path"
            echo "exec python3 app.py \"$@\"" >> "$entrypoint_path"
            chmod +x "$entrypoint_path"
            log_info "Auto-generated entrypoint.sh for Python service at $entrypoint_path"
        else
            log_warning "No app.py found in $app_dir; cannot generate entrypoint.sh"
        fi
    fi
}

# Auto-generate entrypoint.sh for Python services if missing
generate_default_entrypoint() {
    local app_dir="$1"
    local entrypoint_path="$app_dir/entrypoint.sh"
    local main_py="$app_dir/app.py"
    if [[ ! -f "$entrypoint_path" ]]; then
        if [[ -f "$main_py" ]]; then
            echo "#!/bin/bash" > "$entrypoint_path"
            echo "exec python3 app.py \"$@\"" >> "$entrypoint_path"
            chmod +x "$entrypoint_path"
            log_info "Auto-generated entrypoint.sh for Python service at $entrypoint_path"
        else
            log_warning "No app.py found in $app_dir; cannot generate entrypoint.sh"
        fi
    fi
}

# Universal service configuration parser
parse_universal_service_config() {
    local service_name="$1"
    local config_file="$2"
    
    # Check if config file exists
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi
    
    # Initialize configuration array
    declare -gA SERVICE_CONFIG
    # Clear any previous configuration
    unset SERVICE_CONFIG
    declare -gA SERVICE_CONFIG
    
    # Parse configuration file - simply store all key=value pairs
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        
        # Remove leading/trailing whitespace
        key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Store in associative array
        SERVICE_CONFIG[$key]="$value"
    done < "$config_file"
    
    # Validate required fields
    if [[ -z "${SERVICE_CONFIG[image]:-}" ]]; then
        log_error "Required field 'image' not found in $config_file"
        return 1
    fi
    
    return 0
}

# Universal Docker command builder
build_docker_command() {
    local service_name="$1"
    
    # Temporarily disable unbound variable checking for this function
    # since we're doing dynamic key lookups that can trigger false positives
    set +u
    
    # Initialize Docker command array
    declare -ga DOCKER_COMMAND
    DOCKER_COMMAND=("run" "-d" "--name" "$service_name")
    
    # Add default network if not specified and DOCKER_NETWORK_NAME is available
    if [[ -z "${SERVICE_CONFIG[network_mode]:-}" && -n "${DOCKER_NETWORK_NAME:-}" ]]; then
        DOCKER_COMMAND+=("--network" "${DOCKER_NETWORK_NAME}")
    fi
    
    # Set default restart policy if not specified
    if [[ -z "${SERVICE_CONFIG[restart]:-}" ]]; then
        DOCKER_COMMAND+=("--restart" "unless-stopped")
    fi
    
    # Process all configuration options dynamically
    for config_key in "${!SERVICE_CONFIG[@]}"; do
        local config_value="${SERVICE_CONFIG[$config_key]}"
        
        # Skip empty values
        [[ -z "$config_value" ]] && continue
        
        # Skip the image key (handled specially at the end)
        [[ "$config_key" == "image" ]] && continue
        
        # Get the Docker argument mapping for this key
        local docker_arg="${DOCKER_ARG_MAP[$config_key]:-}"
        
        if [[ -n "$docker_arg" ]]; then
            case "$docker_arg" in
                "direct")
                    # Direct mapping - just add the value
                    DOCKER_COMMAND+=("$config_value")
                    ;;
                "port_mapping")
                    # Special port handling
                    local domain_routing="${SERVICE_CONFIG[domain_routing]:-false}"
                    if [[ "$config_value" =~ , ]]; then
                        # Multiple ports
                        IFS=',' read -ra port_array <<< "$config_value"
                        for port in "${port_array[@]}"; do
                            while IFS= read -r port_arg; do
                                DOCKER_COMMAND+=("$port_arg")
                            done < <(handle_port_mapping "$port" "$domain_routing")
                        done
                    else
                        # Single port
                        while IFS= read -r port_arg; do
                            DOCKER_COMMAND+=("$port_arg")
                        done < <(handle_port_mapping "$config_value" "$domain_routing")
                    fi
                    ;;
                "volume_mapping")
                    # Special volume handling
                    if [[ "$config_value" =~ , ]]; then
                        # Multiple volumes
                        IFS=',' read -ra vol_array <<< "$config_value"
                        for volume in "${vol_array[@]}"; do
                            while IFS= read -r vol_arg; do
                                [[ -n "$vol_arg" ]] && DOCKER_COMMAND+=("$vol_arg")  # Skip empty lines
                            done < <(handle_volume_mapping "$volume")
                        done
                    else
                        # Single volume
                        while IFS= read -r vol_arg; do
                            [[ -n "$vol_arg" ]] && DOCKER_COMMAND+=("$vol_arg")  # Skip empty lines
                        done < <(handle_volume_mapping "$config_value")
                    fi
                    ;;
                "env_mapping")
                    # Special environment handling - support both comma and semicolon separators
                    if [[ "$config_value" =~ [,\;] ]]; then
                        # Multiple environment variables - try semicolon first, then comma
                        if [[ "$config_value" == *";"* ]]; then
                            IFS=';' read -ra env_array <<< "$config_value"
                        else
                            IFS=',' read -ra env_array <<< "$config_value"
                        fi
                        for env_var in "${env_array[@]}"; do
                            # Trim whitespace
                            env_var=$(echo "$env_var" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                            [[ -n "$env_var" ]] && while IFS= read -r env_arg; do
                                DOCKER_COMMAND+=("$env_arg")
                            done < <(handle_env_mapping "$env_var")
                        done
                    else
                        # Single environment variable
                        while IFS= read -r env_arg; do
                            DOCKER_COMMAND+=("$env_arg")
                        done < <(handle_env_mapping "$config_value")
                    fi
                    ;;
                "label_mapping")
                    # Special label handling
                    # Check if this is a special Traefik ipwhitelist label that should not be split on commas
                    if [[ "$config_value" =~ ipwhitelist\.sourcerange= ]]; then
                        # IP whitelist labels contain commas as part of the value, don't split
                        while IFS= read -r label_arg; do
                            DOCKER_COMMAND+=("$label_arg")
                        done < <(handle_label_mapping "$config_value")
                    elif [[ "$config_value" =~ , ]]; then
                        # Multiple labels
                        IFS=',' read -ra label_array <<< "$config_value"
                        for label in "${label_array[@]}"; do
                            while IFS= read -r label_arg; do
                                DOCKER_COMMAND+=("$label_arg")
                            done < <(handle_label_mapping "$label")
                        done
                    else
                        # Single label
                        while IFS= read -r label_arg; do
                            DOCKER_COMMAND+=("$label_arg")
                        done < <(handle_label_mapping "$config_value")
                    fi
                    ;;
                "vpn_mapping")
                    # Special VPN handling
                    while IFS= read -r vpn_arg; do
                        DOCKER_COMMAND+=("$vpn_arg")
                    done < <(handle_vpn_mapping "$config_value")
                    ;;
                "traefik_labels")
                    # Special Traefik labels handling for domain routing
                    while IFS= read -r traefik_arg; do
                        DOCKER_COMMAND+=("$traefik_arg")
                    done < <(handle_traefik_labels "$config_value" "$service_name" "${SERVICE_CONFIG[port]}")
                    ;;
                "compose_depends")
                    # Special Docker Compose depends_on handling
                    while IFS= read -r dep_arg; do
                        DOCKER_COMMAND+=("$dep_arg")
                    done < <(handle_compose_depends "$config_value")
                    ;;
                "healthcheck_mapping")
                    # Special healthcheck handling
                    DOCKER_COMMAND+=("--health-cmd" "$config_value")
                    DOCKER_COMMAND+=("--health-interval=30s" "--health-timeout=5s" "--health-retries=3")
                    ;;
                "sysctl_mapping")
                    # Special sysctl handling
                    while IFS= read -r sysctl_arg; do
                        DOCKER_COMMAND+=("$sysctl_arg")
                    done < <(handle_sysctl_mapping "$config_value")
                    ;;
                "restart_policy")
                    DOCKER_COMMAND+=("--restart" "$config_value")
                    ;;
                "discovery_setup")
                    # Discovery configuration handled after main processing loop
                    ;;
                "extra_args_mapping")
                    # Special extra arguments handling
                    while IFS= read -r extra_arg; do
                        DOCKER_COMMAND+=("$extra_arg")
                    done < <(handle_extra_args_mapping "$config_value")
                    ;;
                "ignore")
                    # Configuration option ignored by Docker (metadata only)
                    log_info "Ignoring metadata field: $config_key" || true
                    ;;
                "boolean_flag:"*)
                    # Boolean flag handling - only add flag if value is true
                    local flag_name="${docker_arg#boolean_flag:}"
                    if [[ "$config_value" == "true" ]]; then
                        DOCKER_COMMAND+=("$flag_name")
                    fi
                    # If false, we don't add anything
                    ;;
                "--"*)
                    # Standard Docker argument
                    # Check if this is an option that should NOT be split by commas
                    if [[ "$docker_arg" =~ ^--(tmpfs|mount|log-opt|sysctl|ulimit|device-cgroup-rule|blkio-weight-device|device-read-bps|device-read-iops|device-write-bps|device-write-iops)$ ]]; then
                        # These options use commas as part of their syntax, don't split
                        DOCKER_COMMAND+=("$docker_arg" "$config_value")
                    elif [[ "$config_value" =~ , ]]; then
                        # Multiple values - add multiple arguments
                        IFS=',' read -ra value_array <<< "$config_value"
                        for value in "${value_array[@]}"; do
                            DOCKER_COMMAND+=("$docker_arg" "$value")
                        done
                    else
                        # Single value
                        DOCKER_COMMAND+=("$docker_arg" "$config_value")
                    fi
                    ;;
                *)
                    # Unknown mapping type - log warning but continue
                    log_warning "Unknown Docker argument mapping: $docker_arg for key: $config_key" || true
                    ;;
            esac
        else
            # No mapping found - this is an unknown configuration option
            log_warning "Unknown configuration option: $config_key (value: $config_value)" || true
            log_warning "Add '$config_key' to DOCKER_ARG_MAP if this is a valid Docker option" || true
        fi
    done
    
    # Handle discovery setup if enabled
    if [[ "${SERVICE_CONFIG[enable_discovery]}" == "true" ]]; then
        handle_discovery_setup
    fi
    # Add the image at the end
    DOCKER_COMMAND+=("${SERVICE_CONFIG[image]}")
    
    # Re-enable unbound variable checking
    set -u
    
    return 0
}

# Universal service runner
run_universal_service() {
    local service_name="$1"
    local config_file="$2"
    
    log_info "Starting universal service: $service_name"
    
    # Parse the configuration
    if ! parse_universal_service_config "$service_name" "$config_file"; then
        log_error "Failed to parse configuration for $service_name"
        return 1
    fi
    
    # Auto-generate entrypoint.sh for Python services if needed
    if [[ "${SERVICE_CONFIG[entrypoint]:-}" == "/app/entrypoint.sh" ]]; then
        local app_dir=""
        for vol in $(echo "${SERVICE_CONFIG[volumes]:-}" | tr ',' '\n'); do
            if [[ "$vol" =~ ^([^:]+):/app$ ]]; then
                app_dir="${BASH_REMATCH[1]}"
                break
            fi
        done
        if [[ -n "$app_dir" ]]; then
            generate_default_entrypoint "$app_dir"
        fi
    fi
    # Auto-generate entrypoint.sh for Python services if needed
    if [[ "${SERVICE_CONFIG[entrypoint]:-}" == "/app/entrypoint.sh" ]]; then
        local app_dir=""
        for vol in $(echo "${SERVICE_CONFIG[volumes]:-}" | tr ',' '\n'); do
            if [[ "$vol" =~ ^([^:]+):/app$ ]]; then
                app_dir="${BASH_REMATCH[1]}"
                break
            fi
        done
        if [[ -n "$app_dir" ]]; then
            generate_default_entrypoint "$app_dir"
        fi
    fi
    # Build the Docker command
    if ! build_docker_command "$service_name"; then
        log_error "Failed to build Docker command for $service_name"
        return 1
    fi
    
    # Execute the Docker command
    if [[ "${DRY_RUN:-true}" == "true" ]]; then
        log_info "DRY RUN: docker ${DOCKER_COMMAND[*]}"
        return 0
    else
        log_info "Executing: docker ${DOCKER_COMMAND[*]}"
        if docker "${DOCKER_COMMAND[@]}"; then
            log_success "Successfully started $service_name"
            # Handle post_start_hook if present
            if [[ -n "${SERVICE_CONFIG[post_start_hook]:-}" ]]; then
                log_info "Executing post-start hook: ${SERVICE_CONFIG[post_start_hook]}"
                eval "${SERVICE_CONFIG[post_start_hook]}"
            fi
            return 0
        else
            log_error "Failed to start $service_name"
            return 1
        fi
    fi
}

handle_sysctl_mapping() {
    local sysctl_spec="$1"
    local -a sysctl_args=()
    
    # Handle sysctl formats
    if [[ "$sysctl_spec" =~ ^[^=]+=.*$ ]]; then
        # key=value format
        sysctl_args+=("--sysctl" "$sysctl_spec")
    else
        # Just the key (not typical, but pass through)
        sysctl_args+=("--sysctl" "$sysctl_spec")
    fi
    
    # Only print if we have arguments
    if [[ ${#sysctl_args[@]} -gt 0 ]]; then
        printf '%s\n' "${sysctl_args[@]}"
    fi
}
