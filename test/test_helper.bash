# Test helper functions for bats tests

# Mock docker command for testing
docker() {
    case "$1" in
        "inspect")
            # Mock successful image inspection
            if [[ "$2" == "--format" ]]; then
                echo "mocked"
            else
                return 0
            fi
            ;;
        "image")
            if [[ "$2" == "inspect" ]]; then
                return 0  # Pretend all images exist
            fi
            ;;
        "ps")
            # Mock container status
            echo "Up 5 minutes"
            ;;
        "run"|"create"|"start"|"stop"|"rm")
            # Mock successful docker operations
            return 0
            ;;
        *)
            return 0
            ;;
    esac
}

# Mock other system commands
wg() {
    echo "mock-wireguard-key"
}

systemctl() {
    return 0
}

ip() {
    echo "192.168.1.100"
}

# Mock logging functions for shan-lib.sh compatibility
log() {
    echo "[LOG] $*"
}

log_info() {
    echo "[INFO] $*"
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_warning() {
    echo "[WARNING] $*" >&2
}

log_success() {
    echo "[SUCCESS] $*"
}

warn() {
    echo "[WARN] $*" >&2
}

fail() {
    echo "[FAIL] $*" >&2
    return 1
}

ok() {
    echo "[OK] $*"
}

# Mock AdGuard DNS function
get_adguard_dns_ip() {
    echo "172.18.0.3"
}

# Export mocked functions
export -f docker wg systemctl ip log log_info log_error log_warning log_success warn fail ok get_adguard_dns_ip

# Set common test environment variables
export DEBUG=false
export DRY_RUN=true
export NON_INTERACTIVE=true
export SKIP_DOCKER_CHECK=true
export VALIDATE_ONLY=false