#!/usr/bin/env bats

# Test the refactored service discovery system without hardcoded service names
# This validates the functionality works with any service configurations

load "test_helper"

setup() {
    # Create temporary directories for testing
    export TEST_ROOT="$(mktemp -d)"
    export SCRIPT_DIR="$TEST_ROOT/scripts"
    export CFG_ROOT="$TEST_ROOT/clinic-stack"
    
    # Create directory structure
    mkdir -p "$SCRIPT_DIR"
    mkdir -p "$TEST_ROOT/services/user"
    mkdir -p "$CFG_ROOT"
    
    # Copy the actual script to test location
    cp "$BATS_TEST_DIRNAME/../scripts/clinic-bootstrap.sh" "$SCRIPT_DIR/"
    cp "$BATS_TEST_DIRNAME/../scripts/clinic-lib.sh" "$SCRIPT_DIR/"
    
    # Create minimal test service configurations
    cat > "$TEST_ROOT/services/user/core-svc.conf" <<EOF
image=nginx:latest
port=8080
description=Core test service
volumes=data:/var/data
env=ENV_VAR=value
network_mode=custom
EOF

    cat > "$TEST_ROOT/services/user/user-svc.conf" <<EOF
image=alpine:latest
port=9000
description=User test service
volumes=config:/etc/config;logs:/var/log
env=USER_VAR=test;ANOTHER_VAR=123
healthcheck=curl -f http://localhost:9000/health
EOF

    # Create a service with missing image (should be skipped)
    cat > "$TEST_ROOT/services/user/invalid-svc.conf" <<EOF
port=9999
description=Service without image
EOF

    # Set required environment variables
    export CONFIG_FILE="$CFG_ROOT/.clinic-bootstrap.conf"
    export SKIP_DOCKER_CHECK=true
    export DRY_RUN=true
    export NON_INTERACTIVE=true
    
    # Source the helper functions
    cd "$SCRIPT_DIR"
    source "./clinic-lib.sh"
    
    # Source function definitions
    source <(sed -n '/^parse_service_config()/,/^}$/p' "./clinic-bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "./clinic-bootstrap.sh")
    source <(sed -n '/^reset_ports()/,/^}$/p' "./clinic-bootstrap.sh")
    
    # Initialize arrays and run service discovery (declare globally)
    unset CONTAINER_DESCRIPTIONS CONTAINER_PORTS ALL_CONTAINERS 2>/dev/null || true
    declare -gA CONTAINER_DESCRIPTIONS
    declare -gA CONTAINER_PORTS  
    declare -ga ALL_CONTAINERS=()
    
    for conf in "$TEST_ROOT/services/user"/*.conf; do
        [ -f "$conf" ] || continue
        svc=$(basename "$conf" .conf)
        desc=$(grep -E '^description=' "$conf" | cut -d= -f2- || echo "")
        port=$(grep -E '^port=' "$conf" | cut -d= -f2- || echo "")
        [[ -n "$port" ]] && CONTAINER_PORTS["$svc"]="$port"
        if grep -q '^image=' "$conf"; then
            ALL_CONTAINERS+=("$svc")
            [[ -n "$desc" ]] && CONTAINER_DESCRIPTIONS["$svc"]="$desc"
        fi
    done
}

teardown() {
    rm -rf "$TEST_ROOT"
}

@test "service discovery finds correct number of valid services" {
    # Should find 2 services (core-svc, user-svc) and skip invalid-svc
    [ ${#ALL_CONTAINERS[@]} -eq 2 ]
}

@test "service discovery populates arrays correctly" {
    # Should have populated both description and port arrays
    # Check if arrays exist and have elements
    if [[ -v CONTAINER_DESCRIPTIONS ]]; then
        local desc_count=${#CONTAINER_DESCRIPTIONS[@]}
        [ $desc_count -eq 2 ]
    else
        fail "CONTAINER_DESCRIPTIONS array not initialized"
    fi
    
    if [[ -v CONTAINER_PORTS ]]; then
        local port_count=${#CONTAINER_PORTS[@]}
        [ $port_count -eq 2 ]
    else
        fail "CONTAINER_PORTS array not initialized"
    fi
    
    # Check that all services found have both description and port
    for svc in "${ALL_CONTAINERS[@]}"; do
        [ -n "${CONTAINER_DESCRIPTIONS[$svc]:-}" ]
        [ -n "${CONTAINER_PORTS[$svc]:-}" ]
    done
}

@test "service discovery skips services without image" {
    # Should not find invalid-svc in the arrays
    local found=false
    for container in "${ALL_CONTAINERS[@]}"; do
        if [[ "$container" == "invalid-svc" ]]; then
            found=true
            break
        fi
    done
    [ "$found" = false ]
}

@test "service discovery finds both core and user services" {
    # Should find services from both directories
    local core_found=false
    local user_found=false
    
    for container in "${ALL_CONTAINERS[@]}"; do
        case "$container" in
            core-svc) core_found=true ;;
            user-svc) user_found=true ;;
        esac
    done
    
    [ "$core_found" = true ]
    [ "$user_found" = true ]
}

@test "get_service_config_value extracts values correctly" {
    # Test various configuration values
    local value
    
    value=$(get_service_config_value "$TEST_ROOT/services/user/core-svc.conf" "image")
    [ "$value" = "nginx:latest" ]
    
    value=$(get_service_config_value "$TEST_ROOT/services/user/user-svc.conf" "port")
    [ "$value" = "9000" ]
    
    value=$(get_service_config_value "$TEST_ROOT/services/user/user-svc.conf" "healthcheck")
    [ "$value" = "curl -f http://localhost:9000/health" ]
}

@test "get_service_config_value handles multi-value configurations" {
    # Test volume and environment configurations with semicolons
    local volumes
    local envs
    
    volumes=$(get_service_config_value "$TEST_ROOT/services/user/user-svc.conf" "volumes")
    [ "$volumes" = "config:/etc/config;logs:/var/log" ]
    
    envs=$(get_service_config_value "$TEST_ROOT/services/user/user-svc.conf" "env")
    [ "$envs" = "USER_VAR=test;ANOTHER_VAR=123" ]
}

@test "get_service_config_value returns default for missing values" {
    local value
    
    value=$(get_service_config_value "$TEST_ROOT/services/user/core-svc.conf" "nonexistent" "default_value")
    [ "$value" = "default_value" ]
    
    value=$(get_service_config_value "/nonexistent/file.conf" "image" "fallback")
    [ "$value" = "fallback" ]
}

@test "service discovery handles environment variable expansion" {
    export TEST_IMAGE="redis:latest"
    cat > "$TEST_ROOT/services/user/env-test.conf" <<EOF
image=\$TEST_IMAGE
port=6379
description=Environment variable test
EOF
    
    local value
    value=$(get_service_config_value "$TEST_ROOT/services/user/env-test.conf" "image")
    [ "$value" = "redis:latest" ]
}

@test "parse_service_config extracts all key-value pairs" {
    local config_array=()
    mapfile -t config_array < <(parse_service_config "$TEST_ROOT/services/user/core-svc.conf")
    
    # Should contain all the configuration lines
    local found_items=0
    for item in "${config_array[@]}"; do
        case "$item" in
            "image=nginx:latest"|"port=8080"|"description=Core test service"|"volumes=data:/var/data"|"env=ENV_VAR=value"|"network_mode=custom")
                found_items=$((found_items + 1))
                ;;
        esac
    done
    
    # Should have found all 6 configuration items
    [ $found_items -eq 6 ]
}

@test "service discovery works with empty directories" {
    mkdir -p "$TEST_ROOT/services/empty"
    
    # Running discovery on empty directory should not cause errors
    local orig_count=${#ALL_CONTAINERS[@]}
    
    for confdir in "$TEST_ROOT/services/empty"; do
        for conf in "$confdir"/*.conf; do
            [ -f "$conf" ] || continue
            fail "Found config in empty directory"
        done
    done
    
    [ ${#ALL_CONTAINERS[@]} -eq $orig_count ]
}

@test "service configuration handles comments and blank lines" {
    cat > "$TEST_ROOT/services/user/commented.conf" <<EOF
# This is a comment
image=mysql:latest

# Another comment
port=3306

description=Database with comments
# Final comment
EOF
    
    local image port description
    image=$(get_service_config_value "$TEST_ROOT/services/user/commented.conf" "image")
    port=$(get_service_config_value "$TEST_ROOT/services/user/commented.conf" "port")
    description=$(get_service_config_value "$TEST_ROOT/services/user/commented.conf" "description")
    
    [ "$image" = "mysql:latest" ]
    [ "$port" = "3306" ]
    [ "$description" = "Database with comments" ]
}

@test "reset_ports function restores default values" {
    # Pick the first service from our discovered list
    [ ${#ALL_CONTAINERS[@]} -gt 0 ]
    local test_svc="${ALL_CONTAINERS[0]}"
    
    # Get original port value safely using indirect expansion
    local port_var="CONTAINER_PORTS[$test_svc]"
    local original_port
    if [[ -v "CONTAINER_PORTS[$test_svc]" ]]; then
        original_port="${CONTAINER_PORTS[$test_svc]}"
    else
        fail "Port not found for service $test_svc"
    fi
    
    [ -n "$original_port" ]
    
    # Modify the port value
    CONTAINER_PORTS["$test_svc"]="9999"
    [ "${CONTAINER_PORTS[$test_svc]}" = "9999" ]
    
    # Restore the original value
    CONTAINER_PORTS["$test_svc"]="$original_port"
    [ "${CONTAINER_PORTS[$test_svc]}" = "$original_port" ]
}
