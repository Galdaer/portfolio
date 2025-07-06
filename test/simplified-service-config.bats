#!/usr/bin/env bats
# Test service-agnostic dynamic configuration functionality

setup() {
    export NON_INTERACTIVE=true
    export DRY_RUN=true
    export SKIP_DOCKER_CHECK=true
}

@test "service configs can be discovered dynamically" {
    # Skip in CI environments where service configs don't exist
    if [[ "${CI:-false}" == "true" ]] || [[ -n "${VIRTUAL_ENV:-}" ]]; then
        skip "Skipping service config test in CI environment"
    fi
    
    local service_count=0
    
    # Count services in unified directory
    for conf in "services/user"/*.conf; do
        [ -f "$conf" ] || continue
        service_count=$((service_count + 1))
    done
    
    # Should find at least one service
    [[ $service_count -gt 0 ]]
}

@test "service configs contain required fields" {
    # Skip in CI environments where service configs don't exist
    if [[ "${CI:-false}" == "true" ]] || [[ -n "${VIRTUAL_ENV:-}" ]]; then
        skip "Skipping service config test in CI environment"
    fi
    
    local configs_checked=0
    
    for conf in "services/user"/*.conf; do
        [ -f "$conf" ] || continue
        
        # Check for required fields
        grep -q "^image=" "$conf" || continue
        grep -q "^port=" "$conf" || continue
        
        configs_checked=$((configs_checked + 1))
    done
    
    # Should find at least one valid config
    [[ $configs_checked -gt 0 ]]
}

@test "environment variable setup is service-agnostic" {
    # Source the bootstrap script functions only
    source scripts/clinic-bootstrap.sh
    
    # Test that the setup function exists
    declare -F setup_service_env_vars > /dev/null
}

@test "no hardcoded service logic remains" {
    # Check that old service-specific functions are gone
    ! grep -q "setup_service_plex" scripts/clinic-bootstrap.sh
    ! grep -q "setup_service_traefik" scripts/clinic-bootstrap.sh
    ! grep -q "setup_service_grafana" scripts/clinic-bootstrap.sh
    ! grep -q "setup_service_wireguard" scripts/clinic-bootstrap.sh
}
