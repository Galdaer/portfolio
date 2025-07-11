#!/usr/bin/env bash
# setup-environment.sh - Intelluxe AI Healthcare System dependency installer
# Author: Justin Michael Sue (Galdaer)
# Repo: https://github.com/Intelluxe-AI/intelluxe-core
#
# Copyright (c) 2025 Justin Michael Sue
#
# Dual License Notice:
# This software is available under two licensing options:
#
# 1. AGPL v3.0 License (Open Source)
#    - Free for personal, educational, and open-source use
#    - Requires derivative works to also be open source
#    - See LICENSE-AGPL file for full terms
#
# 2. Commercial License
#    - For proprietary/commercial use without AGPL restrictions
#    - Contact: licensing@intelluxeai.com for commercial licensing terms
#    - Allows embedding in closed-source products
#
# Choose the license that best fits your use case.
#
# TRADEMARK NOTICE: "Intelluxe" and related branding may be trademark protected.
# Commercial use of project branding requires separate permission.
#_______________________________________________________________________________
# Version: 1.0.0
SCRIPT_VERSION="1.1.0"
set -euo pipefail

DEFAULT_UID=1000
DEFAULT_GID=1000

# Use a safer way to define multi-line strings that doesn't trigger set -e
USAGE=$(cat <<EOF
Usage: $0 [--help] [--health-check]
Installs base dependencies for Intelluxe AI healthcare environment with automatic retry and verification

Options:
  --health-check  Verify required tools are installed and exit

Environment variables:
  CFG_UID  Target UID for file ownership (default: $DEFAULT_UID)
  CFG_GID  Target GID for file ownership (default: $DEFAULT_GID)
  GO_VERSION  Go version to install (default: ${GO_VERSION:-1.21.0})
EOF
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/clinic-lib.sh
source "${SCRIPT_DIR}/clinic-lib.sh"

# Parse common flags like --help
parse_basic_flags "$@"

HEALTH_CHECK=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --health-check)
      HEALTH_CHECK=true
      shift
      ;;
    *)
      break
      ;;
  esac
done

# Retry helper with exponential backoff
retry_with_backoff() {
    local max_attempts="$1"
    shift
    local attempt=1
    local delay=1
    until "$@"; do
        if (( attempt >= max_attempts )); then
            err "Command failed after $attempt attempts: $*"
            return 1
        fi
        warn "Attempt $attempt failed. Retrying in $delay seconds..."
        sleep "$delay"
        attempt=$(( attempt + 1 ))
        delay=$(( delay * 2 ))
    done
}

verify_installation() {
    local cmd="$1"
    local name="${2:-$1}"
    if bash -c "$cmd" >/dev/null 2>&1; then
        ok "$name working"
        return 0
    else
        fail "$name verification failed"
        return 1
    fi
}

health_check() {
    local failed=0
    declare -A tools=(
        ["docker info"]="Docker"
        ["python3 --version"]="Python 3"
        ["uv --version"]="uv (Python package manager)"
        ["git --version"]="Git"
        ["go version"]="Go"
        ["psql --version"]="PostgreSQL client"
        ["redis-cli --version"]="Redis client"
        ["wg-quick --help"]="WireGuard tools"
    )

    # Add Docker Compose tools using helper function
    add_tool "docker compose version" "Docker Compose"
    add_tool "docker-compose --version" "Docker Compose"

    # Loop through tools and verify each
    for cmd in "${!tools[@]}"; do
        verify_installation "$cmd" "${tools[$cmd]}" || failed=1
    done
    return "$failed"
}

add_tool() {
    local cmd="$1"
    local name="$2"
    if bash -c "$cmd" >/dev/null 2>&1; then
        tools["$cmd"]="$name"
    else
        fail "$name missing"
    fi
}
: "${CFG_ROOT:=/opt/intelluxe/clinic-stack}"
: "${CFG_UID:=$DEFAULT_UID}"
: "${CFG_GID:=$DEFAULT_GID}"
: "${IP_FORWARD_FILE:=/proc/sys/net/ipv4/ip_forward}"

check_root() {
    if [[ $EUID -ne 0 ]]; then
        err "This script must be run as root (use sudo)"
        exit 1
    fi
}

detect_os() {
    local os_file="${OS_RELEASE_FILE:-/etc/os-release}"
    [[ -f "$os_file" ]] || { err "Cannot detect OS"; exit 1; }
    # shellcheck disable=SC1090
    . "$os_file"
    OS=$ID
    OS_VERSION=$VERSION_ID
    case $OS in
        ubuntu|debian)
            PKG_MANAGER=apt
            PKG_UPDATE="apt-get update -y"
            # Use env to prefix apt-get with DEBIAN_FRONTEND so the variable
            # assignment remains attached to the command when expanded via the
            # PKG_INSTALL array. Without this, the first element would be treated
            # as a standalone command resulting in "DEBIAN_FRONTEND=noninteractive: command not found" errors.
            if systemctl is-active --quiet gdm3 || dpkg -l | grep -q ubuntu-desktop; then
                echo "Desktop system detected - using desktop-safe package installation"
                PKG_INSTALL=(env DEBIAN_FRONTEND=noninteractive apt-get install -y)  # Remove --no-install-recommends
            fi
            ;;
        fedora|rhel|centos)
            PKG_MANAGER=dnf
            PKG_UPDATE="dnf check-update || true"
            PKG_INSTALL=(dnf install -y)
            ;;
        arch)
            PKG_MANAGER=pacman
            PKG_UPDATE="pacman -Sy"
            PKG_INSTALL=(pacman -S --noconfirm)
            ;;
        *)
            err "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    log "Detected OS: $OS $OS_VERSION"
}

update_packages() {
    log "Updating package lists"
    retry_with_backoff 5 bash -c "$PKG_UPDATE"
}

build_dependency_list() {
    local common=(
        # Core system tools
        curl wget git jq less vim nano htop 
        iproute2 iptables net-tools tcpdump nmap socat
        coreutils util-linux lsof psmisc sysstat
        make gcc g++ 
        
        # Security & monitoring (host-level only)
        fail2ban ufw bc tree ncdu iotop mtr
        
        # VPN and networking tools
        wireguard-tools
        
        # Development tools
        shellcheck # shfmt bats installed via Go/Git
        
        # Runtime environments for CI/CD
        nodejs npm
        
        # Python & AI dependencies
        python3-dev python3-pip python3-venv
        
        # Database clients (for connecting to containerized DBs)
        postgresql-client redis-tools
        
        # File system tools
        rsync fuse3
    )
    case $PKG_MANAGER in
        apt)
            # Clean list - no Docker conflicts, no containerized services
            DEPENDENCIES=(apt-utils "${common[@]}" dnsutils)
            ;;
        dnf)
            DEPENDENCIES=("${common[@]}" bind-utils)
            ;;
        pacman)
            DEPENDENCIES=("${common[@]/make/base-devel}" bind-tools)
            ;;
        *)
            DEPENDENCIES=("${common[@]}")
            ;;
    esac
}

install_system_deps() {
    if [[ ${#DEPENDENCIES[@]} -eq 0 ]]; then
        ok "No system dependencies to install"
        return 0
    fi

    log "Installing system dependencies in bulk"

    if "${PKG_INSTALL[@]}" "${DEPENDENCIES[@]}" >/dev/null; then
        ok "All system packages installed"
    else
        warn "Some packages failed to install"
    fi
}

install_docker() {
    if command -v docker &>/dev/null; then
        ok "Docker already present"
        return
    fi
    log "Attempting rootful Docker install"
    case $OS in
        ubuntu|debian)
            retry_with_backoff 5 bash -c 'curl -fsSL https://get.docker.com | sh' || true
            ;;
        fedora|rhel|centos|arch)
            "${PKG_INSTALL[@]}" docker docker-compose || true
            ;;
    esac
    if command -v systemctl &>/dev/null && [[ -d /run/systemd/system ]]; then
        systemctl enable docker &>/dev/null || true
        systemctl start docker &>/dev/null || true
    fi
    verify_installation "docker info" Docker || exit 1
}

ensure_docker_cli() {
    if command -v docker &>/dev/null && docker info &>/dev/null; then
        ok "Docker CLI & daemon working"
        return
    fi

    warn "Docker unusable ➜ installing Podman wrapper"
    case $PKG_MANAGER in
        apt|dnf|pacman)
            "${PKG_INSTALL[@]}" podman podman-docker
            ;;
    esac

    # If podman-docker didn't drop a docker wrapper where sudo secure_path can see it, create one.
    if ! command -v docker &>/dev/null; then
        cat >/usr/bin/docker <<'WRAP'
#!/usr/bin/env bash
exec podman "$@"
WRAP
        chmod +x /usr/bin/docker
    fi

    # Final sanity check
    command -v docker &>/dev/null || { err "docker alias not found after Podman install"; exit 1; }
    ok "Podman installed and docker alias configured"
    verify_installation "docker info" Docker || exit 1
}

ensure_compose() {
    if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null; then
        ok "docker-compose present"
        return
    fi

    if command -v pip3 &>/dev/null; then
        pip3 install --break-system-packages docker-compose >/dev/null 2>&1 || true
    fi

    if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null; then
        ok "docker-compose installed"
    else
        warn "docker-compose installation failed"
    fi
    if docker compose version >/dev/null 2>&1; then
        verify_installation "docker compose version" 'Docker Compose' || exit 1
    elif docker-compose --version >/dev/null 2>&1; then
        verify_installation "docker-compose --version" 'Docker Compose' || exit 1
    else
        err "Docker Compose verification failed"
        exit 1
    fi
}

install_go() {
    if command -v go &>/dev/null; then
        ok "Go present"
        return
    fi
    log "Installing Go"
    GO_VERSION=${GO_VERSION:-1.21.0}
    retry_with_backoff 5 wget -qO /tmp/go.tgz "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
    tar -C /usr/local -xzf /tmp/go.tgz
    rm /tmp/go.tgz
    export PATH="$PATH:/usr/local/go/bin"
    echo "export PATH=\$PATH:/usr/local/go/bin" >>/etc/profile
    ok "Go $GO_VERSION installed"
    verify_installation "go version" Go || exit 1
}

install_uv() {
    if command -v uv &>/dev/null; then
        ok "uv already present"
        return
    fi
    log "Installing uv (fast Python package manager)"
    retry_with_backoff 5 bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    # Find where uv was installed and copy to /usr/local/bin
    if [[ -f "$HOME/.local/bin/uv" ]]; then
        cp "$HOME/.local/bin/uv" /usr/local/bin/
    elif [[ -f "/root/.local/bin/uv" ]]; then
        cp "/root/.local/bin/uv" /usr/local/bin/
    fi
    chmod +x /usr/local/bin/uv
    verify_installation "uv --version" "uv" || exit 1
    ok "uv installed successfully"
}

install_python_deps() {
    log "Installing Python dependencies with uv"
    if [[ $PKG_MANAGER == apt ]]; then
        local py_pkgs=(python3 python3-dev python3-venv libyaml-dev build-essential)
        # Ubuntu 24.04 dropped python3-distutils
        if apt-cache show python3-distutils 2>/dev/null | grep -q '^Package:'; then
            py_pkgs+=(python3-distutils)
        fi
        "${PKG_INSTALL[@]}" "${py_pkgs[@]}"
    fi
    
    # Install uv first
    install_uv
    
    # Use uv to install Python packages system-wide (override Ubuntu's restriction)
    log "Installing Intelluxe AI dependencies with uv (system-wide)"
    uv pip install --system --break-system-packages \
        fastapi uvicorn pydantic \
        sqlalchemy alembic \
        redis psycopg2-binary \
        httpx aiofiles \
        python-multipart "python-jose[cryptography]" \
        passlib bcrypt \
        prometheus-client \
        "pyyaml>=6.0" \
        requests \
        flake8 mypy pytest pytest-asyncio \
        jinja2 yamllint \
        transformers torch ollama-python \
        langchain langchain-community
    
    ok "Python dependencies installed with uv"
    verify_installation "python3 -c 'import fastapi'" "Python dependencies" || exit 1
}

setup_directories() {
    log "Creating Intelluxe directory structure"
    local dirs=(
        "$CFG_ROOT/config" "$CFG_ROOT/data" "$CFG_ROOT/logs" "$CFG_ROOT/backups" "$CFG_ROOT/scripts"
        "$CFG_ROOT/containers" "$CFG_ROOT/wireguard/clients" 
        /opt/intelluxe/storage/disk1 /opt/intelluxe/storage/disk2 
        /opt/intelluxe/data /opt/intelluxe/models /opt/intelluxe/agents
    )
    mkdir -p "${dirs[@]}"
    chmod -R 755 "$CFG_ROOT"
    chmod -R 755 /opt/intelluxe
    set_ownership -R "$CFG_ROOT"
    set_ownership -R /opt/intelluxe
}

install_testing_tools() {
    log "Installing testing tools"
    command -v shellcheck &>/dev/null || "${PKG_INSTALL[@]}" shellcheck
    command -v shellcheck &>/dev/null || { err "shellcheck missing"; exit 1; }
    if ! command -v shfmt &>/dev/null; then
        if command -v go &>/dev/null; then
            /usr/local/go/bin/go install mvdan.cc/sh/v3/cmd/shfmt@latest
            cp "$HOME/go/bin/shfmt" /usr/local/bin
        else
            warn "shfmt skipped"
        fi
    fi
    if ! command -v bats &>/dev/null; then
        if command -v git &>/dev/null; then
            local tmp
            tmp=$(mktemp -d)
            git clone -q https://github.com/bats-core/bats-core "$tmp"
            "$tmp/install.sh" /usr/local
            rm -rf "$tmp"
        fi
    fi
    command -v bats &>/dev/null || { err "bats missing"; exit 1; }
    if ! command -v expect &>/dev/null; then
        "${PKG_INSTALL[@]}" expect >/dev/null
    fi
    command -v expect &>/dev/null || { err "expect missing"; exit 1; }
    ok "Testing tools ready"
}

setup_firewall() {
    command -v ufw &>/dev/null || { warn "ufw absent"; return; }

    # Skip firewall configuration if kernel parameters are read-only
    if [[ "$IP_FORWARD_FILE" == "/proc/sys/net/ipv4/ip_forward" ]] && \
       grep -Eq '^proc /proc/sys proc .*ro' /proc/mounts; then
        warn "Firewall configuration skipped (ip_forward is read-only)"
        return
    fi

    # UFW configuration for Intelluxe healthcare AI system
    if yes | ufw enable >/dev/null 2>&1; then
        ufw default deny incoming || warn "Failed to set default deny policy"
        ufw default allow outgoing || warn "Failed to set default allow policy"
        ufw allow ssh || warn "Failed to open SSH port"
        ufw allow 80/tcp || warn "Failed to open HTTP port"
        ufw allow 443/tcp || warn "Failed to open HTTPS port"
        ufw allow 51820/udp || warn "Failed to open WireGuard port"
        # Intelluxe-specific ports
        ufw allow 11434/tcp || warn "Failed to open Ollama port"
        ufw allow 5678/tcp || warn "Failed to open n8n port"
        ok "Firewall configured for Intelluxe"
    else
        warn "ufw enable failed - skipping firewall configuration"
    fi
}

setup_systemd() {
    mkdir -p /etc/systemd/{system,user}
    # Reload the systemd manager when available. Minimal containers may lack
    # systemctl entirely, in which case skipping the reload is harmless for all
    # supported environments.
    if command -v systemctl &>/dev/null && [[ -d /run/systemd/system ]]; then
        systemctl daemon-reload || true
    fi
}

main() {
    check_root
    detect_os
    if [[ "$HEALTH_CHECK" == true ]]; then
        health_check && ok "All dependencies present" && exit 0 || exit 1
    fi
    update_packages
    build_dependency_list
    install_system_deps
    install_docker
    ensure_docker_cli
    ensure_compose
    install_go
    install_python_deps
    setup_directories
    install_testing_tools
    setup_firewall
    setup_systemd
    ok "All Intelluxe dependencies installed!"
    exit 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
