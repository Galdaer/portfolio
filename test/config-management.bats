#!/usr/bin/env bats

# Test direct function sourcing for configuration management utilities

setup() {
    TMPDIR=$(mktemp -d)
    export CFG_ROOT="$TMPDIR/test-config"
    mkdir -p "$CFG_ROOT"
    
    # Create test config files
    cat > "$CFG_ROOT/.clinic-bootstrap.conf" <<EOF
CFG_ROOT="$CFG_ROOT"
DOCKER_NETWORK_NAME="test-net"
SELECTED_CONTAINERS=(service1 service2)
VPN_SUBNET="10.8.0.0/24"
EOF

    cat > "$TMPDIR/test-service.conf" <<EOF
image=nginx:latest
port=8080
description=Test service for config parsing
volumes=data:/var/data;logs:/var/log
env=TEST_VAR=value;DEBUG=true
network_mode=bridge
healthcheck=curl -f http://localhost:8080/health
extra_args=--restart unless-stopped
EOF
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "parse_service_config handles all configuration keys" {
    # Source only the function we want to test
    source <(sed -n '/^parse_service_config()/,/^}$/p' scripts/clinic-bootstrap.sh)
    
    local config_array=()
    mapfile -t config_array < <(parse_service_config "$TMPDIR/test-service.conf")
    
    # Should extract all non-comment, non-empty lines
    local found_image=false found_port=false found_volumes=false found_env=false
    for item in "${config_array[@]}"; do
        case "$item" in
            image=*) found_image=true ;;
            port=*) found_port=true ;;
            volumes=*) found_volumes=true ;;
            env=*) found_env=true ;;
        esac
    done
    
    [ "$found_image" = true ]
    [ "$found_port" = true ]
    [ "$found_volumes" = true ]
    [ "$found_env" = true ]
}

@test "get_service_config_value extracts individual values correctly" {
    source <(sed -n '/^get_service_config_value()/,/^}$/p' scripts/clinic-bootstrap.sh)
    
    local image port description volumes env
    
    image=$(get_service_config_value "$TMPDIR/test-service.conf" "image")
    port=$(get_service_config_value "$TMPDIR/test-service.conf" "port")
    description=$(get_service_config_value "$TMPDIR/test-service.conf" "description")
    volumes=$(get_service_config_value "$TMPDIR/test-service.conf" "volumes")
    env=$(get_service_config_value "$TMPDIR/test-service.conf" "env")
    
    [ "$image" = "nginx:latest" ]
    [ "$port" = "8080" ]
    [ "$description" = "Test service for config parsing" ]
    [ "$volumes" = "data:/var/data;logs:/var/log" ]
    [ "$env" = "TEST_VAR=value;DEBUG=true" ]
}

@test "get_service_config_value handles missing files and keys" {
    source <(sed -n '/^get_service_config_value()/,/^}$/p' scripts/clinic-bootstrap.sh)
    
    # Test missing file
    local missing_file_result
    missing_file_result=$(get_service_config_value "/nonexistent/file.conf" "image" "default")
    [ "$missing_file_result" = "default" ]
    
    # Test missing key
    local missing_key_result
    missing_key_result=$(get_service_config_value "$TMPDIR/test-service.conf" "nonexistent" "fallback")
    [ "$missing_key_result" = "fallback" ]
    
    # Test missing key without default
    local empty_result
    empty_result=$(get_service_config_value "$TMPDIR/test-service.conf" "nonexistent")
    [ -z "$empty_result" ]
}

@test "get_service_config_value expands environment variables" {
    export TEST_VERSION="1.2.3"
    export TEST_REGISTRY="registry.example.com"
    
    cat > "$TMPDIR/env-test.conf" <<EOF
image=\$TEST_REGISTRY/myapp:\$TEST_VERSION
port=8080
description=Service with env vars
env=VERSION=\$TEST_VERSION
EOF
    
    source <(sed -n '/^get_service_config_value()/,/^}$/p' scripts/clinic-bootstrap.sh)
    
    local image env_var
    image=$(get_service_config_value "$TMPDIR/env-test.conf" "image")
    env_var=$(get_service_config_value "$TMPDIR/env-test.conf" "env")
    
    [ "$image" = "registry.example.com/myapp:1.2.3" ]
    [ "$env_var" = "VERSION=1.2.3" ]
}

@test "get_service_config_value handles comments and whitespace" {
    cat > "$TMPDIR/commented.conf" <<EOF
# This is a comment
image=redis:alpine   
   # Another comment

port=6379  
description=Service with comments and whitespace  
# Final comment
EOF
    
    source <(sed -n '/^get_service_config_value()/,/^}$/p' scripts/clinic-bootstrap.sh)
    
    local image port description
    image=$(get_service_config_value "$TMPDIR/commented.conf" "image")
    port=$(get_service_config_value "$TMPDIR/commented.conf" "port")
    description=$(get_service_config_value "$TMPDIR/commented.conf" "description")
    
    [ "$image" = "redis:alpine" ]
    [ "$port" = "6379" ]
    [ "$description" = "Service with comments and whitespace" ]
}
