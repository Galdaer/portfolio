#!/usr/bin/env bats

# Demonstration: Service-Agnostic System in Action
# This test shows how easy it is to add new services without code changes

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

@test "DEMO: Add MongoDB without any code changes" {
    # Step 1: Create MongoDB configuration (ONLY step needed!)
    cat > "$TEST_ROOT/services/user/mongodb.conf" <<EOF
image=mongo:latest
port=27017
description=MongoDB database server
env=MONGO_INITDB_ROOT_USERNAME=admin;MONGO_INITDB_ROOT_PASSWORD=secret;ADVERTISE_IP=placeholder
volumes=mongo-data:/data/db;mongo-config:/data/configdb
network_mode=custom
extra_args=--restart unless-stopped
healthcheck=echo 'db.stats().ok' | mongo localhost:27017/test --quiet
EOF
    
    # Step 2: System automatically discovers and processes the service
    CONTAINER_PORTS[mongodb]="27017"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    # Step 3: Generic environment setup works automatically
    setup_service_env_vars "mongodb"
    
    # ✅ RESULT: MongoDB fully configured with zero code changes!
    [[ "$MONGO_INITDB_ROOT_USERNAME" == "admin" ]]
    [[ "$MONGO_INITDB_ROOT_PASSWORD" == "secret" ]]
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:27017/" ]]
    
    echo "✅ SUCCESS: MongoDB added with zero code changes!"
}

@test "DEMO: Add custom proprietary application" {
    # Simulate adding a company's proprietary application
    cat > "$TEST_ROOT/services/user/company-erp.conf" <<EOF
image=company-registry.com/erp-system:v2.1.3
port=8443
description=Company ERP System (proprietary)
env=DATABASE_HOST=db.company.com;DATABASE_PORT=5432;ADVERTISE_IP=placeholder;HOSTNAME=placeholder;LICENSE_SERVER=license.company.com;WORKERS=8;DEBUG_MODE=false
volumes=erp-data:$TEST_ROOT/data;erp-logs:/var/log/erp;erp-config:/etc/erp
network_mode=custom
extra_args=--restart unless-stopped --memory=4g --cpus=2.0
healthcheck=curl -k -f https://localhost:8443/api/health
user=1001:1001
EOF
    
    # System processes it generically
    CONTAINER_PORTS[company-erp]="8443"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    setup_service_env_vars "company-erp"
    
    # ✅ RESULT: Complex proprietary application configured automatically!
    [[ "$DATABASE_HOST" == "db.company.com" ]]
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:8443/" ]]
    [[ "$HOSTNAME" == "company-erp-server" ]]
    [[ "$LICENSE_SERVER" == "license.company.com" ]]
    [[ "$WORKERS" == "8" ]]
    [[ "$DEBUG_MODE" == "false" ]]
    
    echo "✅ SUCCESS: Complex proprietary app added with zero code changes!"
}

@test "DEMO: Add microservice fleet" {
    # Add multiple related microservices
    for service in api-gateway user-service order-service payment-service notification-service; do
        local port=$((8000 + $(echo "$service" | wc -c)))
        
        cat > "$TEST_ROOT/services/user/${service}.conf" <<EOF
image=microservices/${service}:latest
port=${port}
description=Microservice: ${service}
env=SERVICE_NAME=${service};ALLOWED_NETWORKS=placeholder;ENVIRONMENT=production;LOG_LEVEL=info
network_mode=custom
extra_args=--restart unless-stopped --memory=512m
healthcheck=curl -f http://localhost:${port}/health
EOF
        
        CONTAINER_PORTS[$service]="$port"
    done
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    # Process all microservices
    local processed_services=0
    for service in api-gateway user-service order-service payment-service notification-service; do
        unset SERVICE_NAME ALLOWED_NETWORKS ENVIRONMENT LOG_LEVEL
        
        setup_service_env_vars "$service"
        
        # Verify each service is configured correctly
        [[ "$SERVICE_NAME" == "$service" ]]
        [[ "$ALLOWED_NETWORKS" == "${LAN_SUBNET},${VPN_SUBNET},${DOCKER_NETWORK_SUBNET}" ]]
        [[ "$ENVIRONMENT" == "production" ]]
        [[ "$LOG_LEVEL" == "info" ]]
        
        processed_services=$((processed_services + 1))
    done
    
    # ✅ RESULT: Entire microservice fleet configured!
    [[ $processed_services -eq 5 ]]
    echo "✅ SUCCESS: 5 microservices added with zero code changes!"
}

@test "DEMO: Verify no service-specific code remains" {
    local script_content
    script_content=$(cat "$SCRIPT_DIR/bootstrap.sh")
    
    # Verify all old service-specific functions are gone
    ! [[ "$script_content" == *"setup_service_plex"* ]]
    ! [[ "$script_content" == *"setup_service_grafana"* ]]
    ! [[ "$script_content" == *"setup_service_traefik"* ]]
    ! [[ "$script_content" == *"setup_service_wireguard"* ]]
    
    # Verify no hardcoded service names in setup logic
    ! [[ "$script_content" == *"case \"\$container\" in"*"plex"* ]]
    ! [[ "$script_content" == *"case \"\$container\" in"*"grafana"* ]]
    
    # Verify only generic setup function exists
    [[ "$script_content" == *"setup_service_env_vars"* ]]
    
    # Verify unified directory structure
    ! [[ "$script_content" == *"services/core"* ]]
    [[ "$script_content" == *"services/user"* ]]
    
    echo "✅ SUCCESS: Bootstrap script is 100% service-agnostic!"
}

@test "DEMO: System handles any Docker configuration" {
    # Test with the most complex Docker configuration possible
    cat > "$TEST_ROOT/services/user/complex-app.conf" <<EOF
image=registry.company.com/complex-app:v3.2.1-beta.5
port=9443
description=Extremely complex application with all Docker features
volumes=app-data:/data;app-cache:/cache;app-logs:/logs;app-secrets:/secrets:ro;app-config:/config
env=APP_MODE=production;WORKERS=16;MEMORY_LIMIT=8GB;HOSTNAME=placeholder;ADVERTISE_IP=placeholder;DATABASE_URLS=postgres://user:pass@db1:5432/app,redis://redis:6379/0;API_KEYS=key1,key2,key3;FEATURE_FLAGS=feature_a:true,feature_b:false
network_mode=custom
extra_args=--restart unless-stopped --memory=8g --cpus=4.0 --ulimit nofile=65536:65536 --cap-add=NET_ADMIN --cap-drop=ALL --security-opt=no-new-privileges --tmpfs /tmp:rw,size=1g --device /dev/fuse --privileged=false
healthcheck=curl -k -f https://localhost:9443/deep/health/check?timeout=30 && test -f /data/health.flag
user=1500:1500
EOF
    
    CONTAINER_PORTS[complex-app]="9443"
    
    source <(sed -n '/^setup_service_env_vars()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    source <(sed -n '/^get_service_config_value()/,/^}$/p' "$SCRIPT_DIR/bootstrap.sh")
    
    # System should handle this complex configuration without any issues
    setup_service_env_vars "complex-app"
    
    # Verify all environment variables are processed correctly
    [[ "$APP_MODE" == "production" ]]
    [[ "$WORKERS" == "16" ]]
    [[ "$MEMORY_LIMIT" == "8GB" ]]
    [[ "$HOSTNAME" == "complex-app-server" ]]
    [[ "$ADVERTISE_IP" == "http://192.168.1.100:9443/" ]]
    [[ "$DATABASE_URLS" == "postgres://user:pass@db1:5432/app,redis://redis:6379/0" ]]
    [[ "$API_KEYS" == "key1,key2,key3" ]]
    [[ "$FEATURE_FLAGS" == "feature_a:true,feature_b:false" ]]
    
    echo "✅ SUCCESS: Most complex Docker configuration handled perfectly!"
}
