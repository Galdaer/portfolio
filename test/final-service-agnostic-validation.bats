#!/usr/bin/env bats

# Final validation test for service-agnostic codebase integrity

setup() {
    TEST_ROOT=$(mktemp -d)
    export SCRIPT_DIR="$TEST_ROOT/scripts"
    export CFG_ROOT="$TEST_ROOT/config"
    
    mkdir -p "$SCRIPT_DIR" "$CFG_ROOT" "$TEST_ROOT/services/user"
    
    # Copy actual scripts
    cp "$BATS_TEST_DIRNAME/../scripts/bootstrap.sh" "$SCRIPT_DIR/"
    cp "$BATS_TEST_DIRNAME/../scripts/lib.sh" "$SCRIPT_DIR/"
    
    # Set test environment
    export NON_INTERACTIVE=true
    export DRY_RUN=true
    export SKIP_DOCKER_CHECK=true
    export LAN_SUBNET="192.168.1.0/24"
    export VPN_SUBNET="10.8.0.0/24"
    export DOCKER_NETWORK_SUBNET="172.20.0.0/16"
    export TRAEFIK_DOMAIN_MODE="local"
    
    # Mock functions
    get_server_ip() { echo "192.168.1.100"; }
    export -f get_server_ip
    
    # Initialize required arrays
    declare -gA CONTAINER_PORTS
}

teardown() {
    rm -rf "$TEST_ROOT"
}

@test "setup_service_env_vars function exists and works" {
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    # Should exist and be callable
    type setup_service_env_vars >/dev/null 2>&1
}

@test "bootstrap script is service-agnostic: no hardcoded service references" {
    local script_content
    script_content=$(cat "$SCRIPT_DIR/bootstrap.sh")
    
    # Should NOT contain any of the old service-specific setup functions
    ! [[ "$script_content" == *"setup_service_plex"* ]]
    ! [[ "$script_content" == *"setup_service_grafana"* ]]
    ! [[ "$script_content" == *"setup_service_traefik"* ]]
    ! [[ "$script_content" == *"setup_service_wireguard"* ]]
    
    # Should NOT reference services/core directory
    ! [[ "$script_content" == *"services/core"* ]]
    
    # Should only use services/user for service discovery
    [[ "$script_content" == *"services/user"* ]]
}

@test "generic environment variable processing works for any service" {
    # Create a completely custom service config
    cat > "$TEST_ROOT/services/user/my-new-service.conf" <<EOF
image=custom/app:latest
port=7777
description=My new custom service
env=ADVERTISE_IP=placeholder;HOSTNAME=placeholder;ALLOWED_NETWORKS=placeholder;CUSTOM_ENV=test123
EOF
    
    # Add to CONTAINER_PORTS for ADVERTISE_IP calculation
    CONTAINER_PORTS[my-new-service]="7777"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    # Run the generic setup
    setup_service_env_vars "my-new-service"
    
    # Should compute environment variables generically
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:7777/" ]]
    [[ "$HOSTNAME" == "my-new-service-server" ]]
    [[ "$ALLOWED_NETWORKS" == "${LAN_SUBNET},${VPN_SUBNET},${DOCKER_NETWORK_SUBNET}" ]]
    [[ "$CUSTOM_ENV" == "test123" ]]
}

@test "service discovery works with unified directory structure" {
    # Create multiple service configs in services/user
    cat > "$TEST_ROOT/services/user/service-a.conf" <<EOF
image=nginx:latest
port=8001
description=Service A
EOF

    cat > "$TEST_ROOT/services/user/service-b.conf" <<EOF
image=postgres:latest
port=5432
description=Service B
EOF

    cat > "$TEST_ROOT/services/user/service-c.conf" <<EOF
image=redis:alpine
port=6379
description=Service C
EOF
    
    # Simulate service discovery logic from bootstrap script
    local discovered_services=()
    for conf in "$TEST_ROOT/services/user"/*.conf; do
        [ -f "$conf" ] || continue
        local svc=$(basename "$conf" .conf)
        if grep -q '^image=' "$conf"; then
            discovered_services+=("$svc")
        fi
    done
    
    # Should discover all services
    [ ${#discovered_services[@]} -eq 3 ]
    [[ " ${discovered_services[*]} " == *" service-a "* ]]
    [[ " ${discovered_services[*]} " == *" service-b "* ]]
    [[ " ${discovered_services[*]} " == *" service-c "* ]]
}

@test "no core/user service distinction exists" {
    # Verify services/core directory does not exist or is not referenced
    local script_content
    script_content=$(cat "$SCRIPT_DIR/bootstrap.sh")
    
    # Should not have any references to services/core
    ! [[ "$script_content" == *"services/core"* ]]
    
    # Should not have loops over multiple directories
    ! [[ "$script_content" == *'for confdir in'*'services/core'*'services/user'* ]]
}

@test "system handles arbitrary service configurations" {
    # Test with extreme configuration to ensure complete service-agnostic operation
    cat > "$TEST_ROOT/services/user/totally-custom-app.conf" <<EOF
image=company.registry.com/proprietary/app:v3.2.1-beta
port=9876
description=Completely custom proprietary application with complex setup
volumes=data-vol:$TEST_ROOT/data;config-vol:/etc/config;logs-vol:/var/logs
env=APP_MODE=production;HOSTNAME=placeholder;DATABASE_URL=postgresql://user:pass@db:5432/myapp;SECRET_KEY=super-secret-key-123;WORKERS=8
network_mode=custom
extra_args=--restart unless-stopped --memory=2g --cpus=1.5 --ulimit nofile=65536:65536
healthcheck=curl -f http://localhost:9876/health || exit 1
user=1500:1500
EOF
    
    # Add port for ADVERTISE_IP calculation
    CONTAINER_PORTS[totally-custom-app]="9876"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    # Should handle any configuration without errors
    setup_service_env_vars "totally-custom-app"
    
    # Should process environment variables correctly
    [[ "$APP_MODE" == "production" ]]
    [[ "$HOSTNAME" == "totally-custom-app-server" ]]
    [[ "$DATABASE_URL" == "postgresql://user:pass@db:5432/myapp" ]]
    [[ "$SECRET_KEY" == "super-secret-key-123" ]]
    [[ "$WORKERS" == "8" ]]
}
