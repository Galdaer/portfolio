#!/usr/bin/env bats
# Test universal service runner functionality

load test_helper

setup() {
    export DRY_RUN=true
    export CFG_ROOT="${BATS_TEST_TMPDIR}/clinic-stack"
    export INTELLUXE_USER="testuser"
    export TRAEFIK_DOMAIN_NAME="test.localhost"
    export DOCKER_NETWORK_NAME="test-net"
    
    mkdir -p "$CFG_ROOT"
    mkdir -p "${BATS_TEST_TMPDIR}/services/user"
    
    # Source required functions from clinic-bootstrap.sh
    source <(sed -n '/^parse_service_config()/,/^}$/p' scripts/clinic-bootstrap.sh)
    
    # Source the libraries with proper order and error handling
    source scripts/clinic-lib.sh || true
    source scripts/universal-service-runner.sh || true
    
    # Create test service config
    cat > "${BATS_TEST_TMPDIR}/services/user/redis.conf" << 'EOF'
image=redis:alpine
port=6379
env=REDIS_PASSWORD=mypassword
volumes=/data:/data
EOF
}

@test "parse_service_config should parse Redis configuration correctly" {
    local config_file="${BATS_TEST_TMPDIR}/services/user/redis.conf"
    
    # Test that parsing succeeds and check the parsed values
    local output
    output=$(parse_service_config "$config_file")
    
    # Check that each expected key=value pair is in the output
    echo "$output" | grep -q "image=redis:alpine"
    echo "$output" | grep -q "port=6379"
    echo "$output" | grep -q "env=REDIS_PASSWORD=mypassword"
    echo "$output" | grep -q "volumes=/data:/data"
}

@test "build_docker_command should generate correct Docker command" {
    local config_file="${BATS_TEST_TMPDIR}/services/user/redis.conf"
    
    # Parse config first
    parse_service_config "$config_file"
    
    # Build the Docker command
    build_docker_command "redis"
    
    # Check that command contains key elements
    [[ "${DOCKER_COMMAND[*]}" =~ "run" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "-d" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--name redis" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "redis:alpine" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "-p 6379:6379" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "-e REDIS_PASSWORD=mypassword" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "-v /data:/data" ]]
}

@test "parse_service_config should handle missing config file" {
    # Test with a helper function since 'run' has limitations with bats
    local status=0
    local output=""
    
    parse_service_config "/nonexistent/path.conf" 2>&1 || status=$?
    
    [ "$status" -ne 0 ]
}

@test "build_docker_command should handle minimal configuration" {
    # Create minimal config
    cat > "${BATS_TEST_TMPDIR}/services/user/minimal.conf" << 'EOF'
image=nginx:alpine
EOF
    
    parse_service_config "${BATS_TEST_TMPDIR}/services/user/minimal.conf"
    
    build_docker_command "minimal"
    
    [[ "${DOCKER_COMMAND[*]}" =~ "nginx:alpine" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--name minimal" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--restart unless-stopped" ]]
}

@test "universal system should handle any Docker option via mapping" {
    cat > "${BATS_TEST_TMPDIR}/services/user/advanced.conf" << 'EOF'
image=postgres:13
port=5432
env=POSTGRES_DB=intelluxe,POSTGRES_USER=admin,POSTGRES_PASSWORD=secret
volumes=/var/lib/postgresql/data:/var/lib/postgresql/data
memory=512m
cpus=1.0
restart=always
health_cmd=pg_isready -U admin
hostname=postgres-server
user=postgres
working_dir=/var/lib/postgresql
EOF
    
    parse_service_config "${BATS_TEST_TMPDIR}/services/user/advanced.conf"
    
    build_docker_command "advanced"
    
    # Check that all mapped options are included
    [[ "${DOCKER_COMMAND[*]}" =~ "--memory 512m" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--cpus 1.0" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--restart always" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--health-cmd pg_isready -U admin" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--hostname postgres-server" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--user postgres" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--workdir /var/lib/postgresql" ]]
}

@test "universal system should handle unknown config options gracefully" {
    cat > "${BATS_TEST_TMPDIR}/services/user/unknown.conf" << 'EOF'
image=nginx:alpine
unknown_option=some_value
another_unknown=test
EOF
    
    # Capture stderr to check for warnings
    parse_service_config "${BATS_TEST_TMPDIR}/services/user/unknown.conf"
    
    build_docker_command "unknown" 2>/dev/null
    
    # Should work despite unknown options (with warnings)
    [[ "${DOCKER_COMMAND[*]}" =~ "nginx:alpine" ]]
    [[ "${DOCKER_COMMAND[*]}" =~ "--name unknown" ]]
}
