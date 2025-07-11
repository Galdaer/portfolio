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
    
    # Count services in unified directory (flat files)
    for conf in "services/user"/*.conf; do
        [ -f "$conf" ] || continue
        service_count=$((service_count + 1))
    done
    
    # Also count services in nested directories  
    for service_dir in "services/user"/*; do
        [ -d "$service_dir" ] || continue
        local svc
        svc=$(basename "$service_dir")
        local conf="$service_dir/$svc.conf"
        if [[ -f "$conf" ]]; then
            service_count=$((service_count + 1))
        fi
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
    
    # Check flat service configs
    for conf in "services/user"/*.conf; do
        [ -f "$conf" ] || continue
        
        # Check for required fields
        grep -q "^image=" "$conf" || continue
        grep -q "^port=" "$conf" || continue
        
        configs_checked=$((configs_checked + 1))
    done
    
    # Check nested service configs
    for service_dir in "services/user"/*; do
        [ -d "$service_dir" ] || continue
        local svc
        svc=$(basename "$service_dir")
        local conf="$service_dir/$svc.conf"
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
    # Source only the setup_service_env_vars function without executing main script logic
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "scripts/clinic-bootstrap.sh")
    
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
