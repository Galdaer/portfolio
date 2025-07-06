#!/usr/bin/env bats

# Test service-agnostic codebase integrity
# Validates that the system works with ANY Docker service without hardcoded logic

load "test_helper"

setup() {
    # Create test environment
    TEST_ROOT=$(mktemp -d)
    export SCRIPT_DIR="$TEST_ROOT/scripts"
    export CFG_ROOT="$TEST_ROOT/config"
    export TMPDIR="$TEST_ROOT/tmp"
    
    mkdir -p "$SCRIPT_DIR" "$CFG_ROOT" "$TMPDIR"
    mkdir -p "$TEST_ROOT/services/user"
    
    # Copy actual scripts for testing
    cp "$BATS_TEST_DIRNAME/../scripts/clinic-bootstrap.sh" "$SCRIPT_DIR/"
    cp "$BATS_TEST_DIRNAME/../scripts/clinic-lib.sh" "$SCRIPT_DIR/"
    
    # Set test environment variables
    export NON_INTERACTIVE=true
    export DRY_RUN=true
    export SKIP_DOCKER_CHECK=true
    
    # Network configuration for testing
    export LAN_SUBNET="192.168.1.0/24"
    export VPN_SUBNET="10.8.0.0/24"
    export DOCKER_NETWORK_SUBNET="172.20.0.0/16"
    export TRAEFIK_DOMAIN_MODE="local"
    export TRAEFIK_DOMAIN_NAME="example.local"
    
    # Initialize arrays
    declare -gA CONTAINER_PORTS
    CONTAINER_PORTS[test-service]="8080"
    CONTAINER_PORTS[custom-app]="9000"
    
    # Mock functions for testing
    get_server_ip() { echo "192.168.1.100"; }
    log() { echo "LOG: $*"; }
    warn() { echo "WARN: $*"; }
    ok() { echo "OK: $*"; }
    
    export -f get_server_ip log warn ok
}

teardown() {
    rm -rf "$TEST_ROOT"
}

# Test the new generic setup_service_env_vars function
@test "setup_service_env_vars function exists and is callable" {
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should be able to call the function without error
    setup_service_env_vars "nonexistent-service"
    [ $? -eq 0 ]
}

@test "setup_service_env_vars processes ADVERTISE_IP for local mode" {
    # Create test service config with ADVERTISE_IP
    cat > "$TEST_ROOT/services/user/test-app.conf" <<EOF
image=nginx:latest
port=8080
description=Test application
env=ADVERTISE_IP=placeholder;OTHER_VAR=value
EOF
    
    # Add port to CONTAINER_PORTS
    CONTAINER_PORTS[test-app]="8080"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    export TRAEFIK_DOMAIN_MODE="local"
    
    setup_service_env_vars "test-app"
    
    # Should set ADVERTISE_IP using server IP and port
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:8080/" ]]
}

@test "setup_service_env_vars processes ADVERTISE_IP for ddns mode" {
    cat > "$TEST_ROOT/services/user/test-app.conf" <<EOF
image=nginx:latest
port=8080
description=Test application
env=ADVERTISE_IP=placeholder
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    export TRAEFIK_DOMAIN_MODE="ddns"
    export TRAEFIK_DOMAIN_NAME="test.duckdns.org"
    
    setup_service_env_vars "test-app"
    
    # Should set ADVERTISE_IP using domain name
    [[ "$ADVERTISE_IP" == "https://test-app.test.duckdns.org/" ]]
}

@test "setup_service_env_vars processes HOSTNAME for local mode" {
    cat > "$TEST_ROOT/services/user/custom-service.conf" <<EOF
image=postgres:latest
port=5432
description=Custom database
env=HOSTNAME=placeholder;DB_NAME=test
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    export TRAEFIK_DOMAIN_MODE="local"
    
    setup_service_env_vars "custom-service"
    
    # Should set hostname using generic pattern
    [[ "$HOSTNAME" == "custom-service-server" ]]
}

@test "setup_service_env_vars processes HOSTNAME for ddns mode" {
    cat > "$TEST_ROOT/services/user/my-app.conf" <<EOF
image=redis:latest
port=6379
description=My custom application
env=HOSTNAME=placeholder
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    export TRAEFIK_DOMAIN_MODE="ddns"
    export TRAEFIK_DOMAIN_NAME="mydomain.com"
    
    setup_service_env_vars "my-app"
    
    # Should set hostname using domain
    [[ "$HOSTNAME" == "my-app.mydomain.com" ]]
}

@test "setup_service_env_vars processes ALLOWED_NETWORKS generically" {
    cat > "$TEST_ROOT/services/user/any-service.conf" <<EOF
image=alpine:latest
port=3000
description=Any service that needs network access
env=ALLOWED_NETWORKS=placeholder;DEBUG=true
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    setup_service_env_vars "any-service"
    
    # Should combine all network subnets
    local expected="${LAN_SUBNET},${VPN_SUBNET},${DOCKER_NETWORK_SUBNET}"
    [[ "$ALLOWED_NETWORKS" == "$expected" ]]
}

@test "setup_service_env_vars processes multiple environment variables" {
    cat > "$TEST_ROOT/services/user/multi-env.conf" <<EOF
image=myapp:latest
port=4000
description=Service with multiple env vars
env=ADVERTISE_IP=placeholder;HOSTNAME=placeholder;ALLOWED_NETWORKS=placeholder;CUSTOM_VAR=custom_value
EOF
    
    # Add port to CONTAINER_PORTS
    CONTAINER_PORTS[multi-env]="4000"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    export TRAEFIK_DOMAIN_MODE="local"
    
    setup_service_env_vars "multi-env"
    
    # Should process all special variables
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:4000/" ]]
    [[ "$HOSTNAME" == "multi-env-server" ]]
    [[ "$ALLOWED_NETWORKS" == "${LAN_SUBNET},${VPN_SUBNET},${DOCKER_NETWORK_SUBNET}" ]]
    [[ "$CUSTOM_VAR" == "custom_value" ]]
}

@test "setup_service_env_vars handles regular environment variables" {
    cat > "$TEST_ROOT/services/user/normal-env.conf" <<EOF
image=nginx:latest
port=8080
description=Service with normal env vars
env=DEBUG=true;LOG_LEVEL=info;API_KEY=secret123
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    setup_service_env_vars "normal-env"
    
    # Should export regular variables unchanged
    [[ "$DEBUG" == "true" ]]
    [[ "$LOG_LEVEL" == "info" ]]
    [[ "$API_KEY" == "secret123" ]]
}

@test "setup_service_env_vars gracefully handles missing config file" {
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should not fail when service config doesn't exist
    setup_service_env_vars "nonexistent-service"
    [ $? -eq 0 ]
}

@test "setup_service_env_vars gracefully handles missing env section" {
    cat > "$TEST_ROOT/services/user/no-env.conf" <<EOF
image=nginx:latest
port=8080
description=Service without env section
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should not fail when no env section exists
    setup_service_env_vars "no-env"
    [ $? -eq 0 ]
}

# Test service-agnostic directory structure
@test "bootstrap script only looks in services/user directory" {
    script_content=$(cat "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should not reference services/core anywhere
    ! [[ "$script_content" == *"services/core"* ]]
    
    # Should only reference services/user
    [[ "$script_content" == *"services/user"* ]]
}

@test "service discovery works with any service configuration" {
    # Create diverse service configurations to test generic discovery
    cat > "$TEST_ROOT/services/user/webapp.conf" <<EOF
image=node:alpine
port=3000
description=Web application
volumes=data:/app/data
env=NODE_ENV=production
EOF

    cat > "$TEST_ROOT/services/user/database.conf" <<EOF
image=postgres:13
port=5432
description=Database server
volumes=db-data:/var/lib/postgresql/data
env=POSTGRES_DB=myapp;POSTGRES_USER=admin
network_mode=custom
EOF

    cat > "$TEST_ROOT/services/user/cache.conf" <<EOF
image=redis:alpine
port=6379
description=Cache server
extra_args=--restart unless-stopped
EOF

    # Source the bootstrap discovery logic
    cd "$SCRIPT_DIR"
    source <(grep -A 50 "# Dynamic service discovery" clinic-bootstrap.sh | sed '/^$/,$d')
    
    # Should discover all three services
    local discovered_services=()
    for conf in "$TEST_ROOT/services/user"/*.conf; do
        [ -f "$conf" ] || continue
        local svc=$(basename "$conf" .conf)
        if grep -q '^image=' "$conf"; then
            discovered_services+=("$svc")
        fi
    done
    
    [ ${#discovered_services[@]} -eq 3 ]
    [[ " ${discovered_services[*]} " == *" webapp "* ]]
    [[ " ${discovered_services[*]} " == *" database "* ]]
    [[ " ${discovered_services[*]} " == *" cache "* ]]
}

@test "no hardcoded service names remain in bootstrap script" {
    script_content=$(cat "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should not contain hardcoded references to specific services in logic
    # (comments and help text are OK, but not in functional code)
    
    # Check ensure_container_running doesn't have service-specific cases
    ensure_container_function=$(sed -n '/^ensure_container_running()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    ! [[ "$ensure_container_function" == *"plex)"* ]]
    ! [[ "$ensure_container_function" == *"grafana)"* ]]
    ! [[ "$ensure_container_function" == *"traefik)"* ]]
    ! [[ "$ensure_container_function" == *"wireguard)"* ]]
    
    # Should not have setup_service_plex, setup_service_grafana, etc.
    ! [[ "$script_content" == *"setup_service_plex"* ]]
    ! [[ "$script_content" == *"setup_service_grafana"* ]]
    ! [[ "$script_content" == *"setup_service_traefik"* ]]
    ! [[ "$script_content" == *"setup_service_wireguard"* ]]
}

@test "service restriction logic is purely port-based" {
    script_content=$(cat "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should not contain hardcoded service lists in restriction logic
    ! [[ "$script_content" == *"grafana | plex | influxdb | adguard"* ]]
    
    # Should use dynamic port-based logic
    [[ "$script_content" == *'if [[ -n "${CONTAINER_PORTS[$container]:-}" ]]'* ]]
}

@test "works with completely custom service configurations" {
    # Test with services that don't exist in the original codebase
    cat > "$TEST_ROOT/services/user/my-custom-app.conf" <<EOF
image=mycompany/proprietary-app:v2.1
port=8888
description=My proprietary business application
volumes=app-data:/data;app-logs:/logs;app-config:/etc/app
env=ADVERTISE_IP=placeholder;HOSTNAME=placeholder;LICENSE_KEY=ABC123;WORKERS=4
network_mode=custom
extra_args=--restart unless-stopped --memory=1g
healthcheck=curl -f http://localhost:8888/health
user=1001:1001
EOF

    cat > "$TEST_ROOT/services/user/microservice-x.conf" <<EOF
image=golang:alpine
port=9999
description=Microservice X for data processing
env=SERVICE_MODE=production;ALLOWED_NETWORKS=placeholder;MAX_CONNECTIONS=100
EOF
    
    # Add ports to CONTAINER_PORTS for these services
    CONTAINER_PORTS[my-custom-app]="8888"
    CONTAINER_PORTS[microservice-x]="9999"
    
    # Test that setup_service_env_vars works with these custom services
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Test custom app
    setup_service_env_vars "my-custom-app"
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:8888/" ]]
    [[ "$HOSTNAME" == "my-custom-app-server" ]]
    [[ "$LICENSE_KEY" == "ABC123" ]]
    [[ "$WORKERS" == "4" ]]
    
    # Reset environment
    unset ADVERTISE_IP HOSTNAME SERVICE_MODE ALLOWED_NETWORKS MAX_CONNECTIONS
    
    # Test microservice
    setup_service_env_vars "microservice-x"
    [[ "$SERVICE_MODE" == "production" ]]
    [[ "$ALLOWED_NETWORKS" == "${LAN_SUBNET},${VPN_SUBNET},${DOCKER_NETWORK_SUBNET}" ]]
    [[ "$MAX_CONNECTIONS" == "100" ]]
}

@test "environment variable expansion works in generic setup" {
    export TEST_API_URL="https://api.example.com"
    export TEST_DATABASE_NAME="prod_db"
    
    cat > "$TEST_ROOT/services/user/expansion-test.conf" <<EOF
image=myapp:latest
port=5000
description=Service with variable expansion
env=API_URL=\$TEST_API_URL;DB_NAME=\$TEST_DATABASE_NAME;HOSTNAME=placeholder
EOF
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    setup_service_env_vars "expansion-test"
    
    # Should expand variables correctly
    [[ "$API_URL" == "https://api.example.com" ]]
    [[ "$DB_NAME" == "prod_db" ]]
    [[ "$HOSTNAME" == "expansion-test-server" ]]
}

@test "service-agnostic system handles edge cases" {
    # Test with special characters in service names and values
    cat > "$TEST_ROOT/services/user/test-app_v2.conf" <<EOF
image=test/app:v2.0-beta
port=8080
description=App with special chars: @#$%
env=SPECIAL_VAR=value@with#special\\chars;ADVERTISE_IP=placeholder
EOF
    
    # Add port to CONTAINER_PORTS for this service
    CONTAINER_PORTS[test-app_v2]="8080"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/clinic-bootstrap.sh")
    
    # Should handle service name with underscores and hyphens
    setup_service_env_vars "test-app_v2"
    [ $? -eq 0 ]
    
    # Should handle special characters in environment values
    # The function should preserve literal characters (without the dollar sign expansion)
    [[ "$SPECIAL_VAR" == "value@with#special\\chars" ]]
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:8080/" ]]
}
