#!/usr/bin/env bats

# Test port and network validation functions

setup() {
    TMPDIR=$(mktemp -d)
    
    # Mock network commands
    mkdir -p "$TMPDIR/bin"
    
    # Mock ss command for port checking
    cat > "$TMPDIR/bin/ss" <<'EOF'
#!/bin/bash
case "$*" in
    "-ltn")
        # TCP listening ports
        cat <<TCPPORTS
State    Recv-Q    Send-Q       Local Address:Port        Peer Address:Port
LISTEN   0         128                0.0.0.0:22               0.0.0.0:*
LISTEN   0         128                0.0.0.0:80               0.0.0.0:*
LISTEN   0         128                0.0.0.0:443              0.0.0.0:*
LISTEN   0         128              127.0.0.1:3000             0.0.0.0:*
TCPPORTS
        ;;
    "-lun")
        # UDP listening ports
        cat <<UDPPORTS
State    Recv-Q    Send-Q       Local Address:Port        Peer Address:Port
UNCONN   0         0                  0.0.0.0:53               0.0.0.0:*
UNCONN   0         0                  0.0.0.0:51820            0.0.0.0:*
UDPPORTS
        ;;
    "-lntup | grep :8080")
        echo "tcp   LISTEN  0   128   0.0.0.0:8080   0.0.0.0:*"
        ;;
    "-lntup | grep :9999")
        # Port not in use
        exit 1
        ;;
    *)
        echo "Mock ss: $*"
        ;;
esac
EOF
    chmod +x "$TMPDIR/bin/ss"
    
    # Mock lsof command
    cat > "$TMPDIR/bin/lsof" <<'EOF'
#!/bin/bash
case "$*" in
    "-i :8080")
        echo "nginx   1234 root   6u  IPv4  12345      0t0  TCP *:8080 (LISTEN)"
        ;;
    "-i :9999")
        # Port not in use
        exit 1
        ;;
    *)
        echo "Mock lsof: $*"
        ;;
esac
EOF
    chmod +x "$TMPDIR/bin/lsof"
    
    export PATH="$TMPDIR/bin:$PATH"
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "check_port_in_use detects TCP ports correctly" {
    # Source from clinic-lib.sh
    source <(sed -n '/^check_port_in_use()/,/^}$/p' scripts/clinic-lib.sh)
    
    # Test port in use
    check_port_in_use "80" "tcp" && status_80=$? || status_80=$?
    [ "$status_80" -eq 0 ]
    
    check_port_in_use "22" "tcp" && status_22=$? || status_22=$?
    [ "$status_22" -eq 0 ]
    
    # Test port not in use
    check_port_in_use "9999" "tcp" && status_9999=$? || status_9999=$?
    [ "$status_9999" -ne 0 ]
}

@test "check_port_in_use detects UDP ports correctly" {
    source <(sed -n '/^check_port_in_use()/,/^}$/p' scripts/clinic-lib.sh)
    
    # Test UDP port in use
    check_port_in_use "53" "udp" && status_53=$? || status_53=$?
    [ "$status_53" -eq 0 ]
    
    check_port_in_use "51820" "udp" && status_wg=$? || status_wg=$?
    [ "$status_wg" -eq 0 ]
    
    # Test UDP port not in use
    check_port_in_use "8888" "udp" && status_8888=$? || status_8888=$?
    [ "$status_8888" -ne 0 ]
}

@test "check_port_in_use defaults to TCP" {
    source <(sed -n '/^check_port_in_use()/,/^}$/p' scripts/clinic-lib.sh)
    
    # Test without specifying protocol (should default to TCP)
    check_port_in_use "80" && status_default=$? || status_default=$?
    [ "$status_default" -eq 0 ]
    
    check_port_in_use "9999" && status_default_free=$? || status_default_free=$?
    [ "$status_default_free" -ne 0 ]
}

@test "show_port_usage displays port information" {
    # Source from clinic-lib.sh
    source <(sed -n '/^show_port_usage()/,/^}$/p' scripts/clinic-lib.sh)
    
    run show_port_usage "8080"
    [ "$status" -eq 0 ]
    [[ "$output" == *"nginx"* ]]
    [[ "$output" == *"1234"* ]]
    [[ "$output" == *"8080"* ]]
}

@test "show_port_usage handles unused ports" {
    source <(sed -n '/^show_port_usage()/,/^}$/p' scripts/clinic-lib.sh)
    
    run show_port_usage "9999"
    [ "$status" -eq 0 ]
    # Should not show any process info for unused port
    # Output might be empty or show fallback ss info
}

@test "port validation with service configuration" {
    # Test port validation in context of service configuration
    declare -A CONTAINER_PORTS=(
        [service1]="8080"
        [service2]="3000" 
        [service3]="9999"
    )
    
    source <(sed -n '/^check_port_in_use()/,/^}$/p' scripts/clinic-lib.sh)
    
    # Test that we can validate each service's port
    for service in "${!CONTAINER_PORTS[@]}"; do
        port="${CONTAINER_PORTS[$service]}"
        
        # This should not fail - we're just testing the interface works
        check_port_in_use "$port" "tcp" && port_status=$? || port_status=$?
        
        # For known ports, verify expected results
        case "$port" in
            "8080"|"3000") 
                # These ports show as in use in our mock
                ;;
            "9999")
                # This port shows as free in our mock
                [ "$port_status" -ne 0 ]
                ;;
        esac
    done
}
