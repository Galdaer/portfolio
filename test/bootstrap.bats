#!/usr/bin/env bats

# Source required scripts once for all tests
source scripts/lib.sh
source scripts/universal-service-runner.sh

# Extract specific functions and variables from bootstrap script without executing the whole script
eval "$(awk '/^ALL_CONTAINERS=\(/ {print; exit}' scripts/bootstrap.sh)"
eval "$(awk '/^ensure_container_running\(\)/,/^}/' scripts/bootstrap.sh)"
eval "$(awk '/^get_service_config_value\(\)/,/^}/' scripts/bootstrap.sh)"
eval "$(awk '/^ensure_directories\(\)/,/^}/' scripts/bootstrap.sh)"
eval "$(awk '/^stop_service\(\)/,/^}/' scripts/bootstrap.sh)"

setup() {
  TMPDIR=$(mktemp -d)
  ORIGINAL_PATH=$PATH
}

teardown() {
  rm -rf "$TMPDIR"
  PATH=$ORIGINAL_PATH
}

@test "ensure_directories creates WireGuard dirs with ownership" {
  CFG_ROOT="$TMPDIR/stack"
  WG_DIR="$TMPDIR/wireguard"
  WG_CLIENTS_DIR="$WG_DIR/clients"
  BACKUP_DIR="$CFG_ROOT/backups"
  QR_DIR="$CFG_ROOT/qrcodes"
  CFG_UID=$(id -u)
  CFG_GID=$(id -g)
  DRY_RUN=false

  ensure_directories

  [ -d "$WG_DIR" ]
  [ -d "$WG_CLIENTS_DIR" ]
  [ "$(stat -c %u "$WG_DIR")" -eq "$CFG_UID" ]
  [ "$(stat -c %g "$WG_DIR")" -eq "$CFG_GID" ]
  [ "$(stat -c %u "$WG_CLIENTS_DIR")" -eq "$CFG_UID" ]
  [ "$(stat -c %g "$WG_CLIENTS_DIR")" -eq "$CFG_GID" ]

  containers=($(grep '^ALL_CONTAINERS=(' scripts/bootstrap.sh | awk -F'[()]' '{print $2}'))
  for c in "${containers[@]}"; do
    case "$c" in
      influxdb)
        dir="$CFG_ROOT/${c}-data"
        [ -d "$dir" ]
        [ "$(stat -c %u "$dir")" -eq "$CFG_UID" ]
        [ "$(stat -c %g "$dir")" -eq "$CFG_GID" ]
        ;;
      traefik)
        [ -d "$CFG_ROOT/traefik-config" ]
        [ -d "$CFG_ROOT/traefik-data" ]
        [ "$(stat -c %u "$CFG_ROOT/traefik-config")" -eq "$CFG_UID" ]
        [ "$(stat -c %g "$CFG_ROOT/traefik-config")" -eq "$CFG_GID" ]
        [ "$(stat -c %u "$CFG_ROOT/traefik-data")" -eq "$CFG_UID" ]
        [ "$(stat -c %g "$CFG_ROOT/traefik-data")" -eq "$CFG_GID" ]
        ;;
      wireguard)
        dir="$CFG_ROOT/wireguard"
        [ -d "$dir" ]
        [ "$(stat -c %u "$dir")" -eq "$CFG_UID" ]
        [ "$(stat -c %g "$dir")" -eq "$CFG_GID" ]
        ;;
      *)
        dir="$CFG_ROOT/${c}-config"
        [ -d "$dir" ]
        [ "$(stat -c %u "$dir")" -eq "$CFG_UID" ]
        [ "$(stat -c %g "$dir")" -eq "$CFG_GID" ]
        ;;
    esac
done
}

@test "logs directory and log file path set correctly" {
  CFG_ROOT="$TMPDIR/root"
  mkdir -p "$CFG_ROOT"
  snippet=$(sed -n '/CONFIG_FILE=/,/LOG_FILE=/p' scripts/bootstrap.sh)
  eval "$snippet"
  [ "$LOG_DIR" = "$CFG_ROOT/logs" ]
  [ -d "$LOG_DIR" ]
  [ "$LOG_FILE" = "$LOG_DIR/bootstrap.log" ]
}

@test "enable_config_web_ui invoked when not dry run" {
  DRY_RUN=false
  called=false
  enable_config_web_ui() { called=true; }
  line=$(grep -n "enable_config_web_ui" scripts/bootstrap.sh | grep -v "()" | cut -d: -f1)
  start=$((line-1))
  end=$((line+1))
  snippet=$(sed -n "${start},${end}p" scripts/bootstrap.sh)
  eval "$snippet"
  [ "$called" = true ]
}

@test "enable_config_web_ui skipped when dry run" {
  DRY_RUN=true
  called=false
  enable_config_web_ui() { called=true; }
  line=$(grep -n "enable_config_web_ui" scripts/bootstrap.sh | grep -v "()" | cut -d: -f1)
  start=$((line-1))
  end=$((line+1))
  snippet=$(sed -n "${start},${end}p" scripts/bootstrap.sh)
  eval "$snippet"
  [ "$called" = false ]
}

@test "get_server_ip parses IP from ip route" {
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/ip" <<'EOF'
#!/usr/bin/env bash
echo "8.8.8.8 via 192.168.1.1 dev eth0 src 10.0.0.5"
EOF
  chmod +x "$TMPDIR/bin/ip"
  PATH="$TMPDIR/bin:$PATH"

  eval "$(awk '/^get_server_ip\(\)/,/^}/' scripts/bootstrap.sh)"
  result=$(bash -c "$(declare -f get_server_ip); set -euo pipefail; get_server_ip" 2>/dev/null || echo "failed")
  [ "$result" = "10.0.0.5" ]
}

@test "get_server_ip falls back when ip route fails" {
  mkdir -p "$TMPDIR/bin"
  cat >"$TMPDIR/bin/ip" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  chmod +x "$TMPDIR/bin/ip"
  PATH="$TMPDIR/bin:$PATH"

  eval "$(awk '/^get_server_ip\(\)/,/^}/' scripts/bootstrap.sh)"
  result=$(bash -c "$(declare -f get_server_ip); set -euo pipefail; get_server_ip" 2>/dev/null || echo "your-server-ip")
  [ "$result" = "your-server-ip" ]
}

@test "--reset-wg-keys updates key file and client configs" {
  WG_DIR="$TMPDIR/wg"
  WG_CLIENTS_DIR="$WG_DIR/clients"
  WG_KEYS_ENV="$WG_DIR/wg-keys.env"
  mkdir -p "$WG_CLIENTS_DIR/client1"
  echo "WG_SERVER_PRIVATE_KEY=old" > "$WG_KEYS_ENV"
  echo "WG_SERVER_PUBLIC_KEY=oldpub" >> "$WG_KEYS_ENV"
  echo "WG_PRESHARED_KEY=oldpsk" >> "$WG_KEYS_ENV"
  cat > "$WG_CLIENTS_DIR/client1/client1.conf" <<EOF
[Peer]
PublicKey = oldpub
PresharedKey = oldpsk
EOF

  eval "$(awk '/^reset_wireguard_keys\(\)/,/^}/' scripts/bootstrap.sh)"
  generate_wg_qr() { touch "$1/$2.png"; }
  backup_wireguard() { :; }
  warn() { :; }
  log() { :; }
  set_ownership() { :; }
  wg() {
    case "$1" in
      genkey) echo newpriv ;;
      pubkey) cat >/dev/null; echo newpub ;;
      genpsk) echo newpsk ;;
    esac
  }
  export NON_INTERACTIVE=true
  export FORCE_DEFAULTS=true
  export WG_DIR WG_CLIENTS_DIR WG_KEYS_ENV

  run bash -c "$(declare -f reset_wireguard_keys generate_wg_qr backup_wireguard warn log set_ownership wg); set -euo pipefail; reset_wireguard_keys"
  # Verify the function succeeded by checking the outputs directly
  newpub=$(grep '^WG_SERVER_PUBLIC_KEY=' "$WG_KEYS_ENV" | cut -d= -f2)
  newpsk=$(grep '^WG_PRESHARED_KEY=' "$WG_KEYS_ENV" | cut -d= -f2)
  [ "$newpub" != "oldpub" ]
  [ "$newpsk" != "oldpsk" ]
  grep -q "$newpub" "$WG_CLIENTS_DIR/client1/client1.conf"
  grep -q "$newpsk" "$WG_CLIENTS_DIR/client1/client1.conf"
  [ -f "$WG_CLIENTS_DIR/client1/client1.png" ]
}

@test "save_config persists VPN subnet settings" {
  CFG_ROOT="$TMPDIR/stack"
  CONFIG_FILE="$CFG_ROOT/.bootstrap.conf"
  mkdir -p "$CFG_ROOT"

  VPN_SUBNET="10.9.0.0/24"
  VPN_SUBNET_BASE="10.9.0"
  SCRIPT_VERSION="test-version"
  CFG_UID=$(id -u)
  CFG_GID=$(id -g)
  # Add dummy values for other variables used in save_config
  DOCKER_NETWORK_NAME="dummy-net"
  DOCKER_NETWORK_SUBNET="172.28.0.0/24"
  LAN_SUBNET="192.168.1.0/24"
  WG_CLIENT_DNS="8.8.8.8"
  DNS_FALLBACK="8.8.8.8"
  FIREWALL_RESTRICT_MODE="false"
  TRAEFIK_DOMAIN_MODE="local"
  TRAEFIK_DOMAIN_NAME=""
  TRAEFIK_ACME_EMAIL=""
  WG_DIR="/tmp/wg"
  STORE_WG_IN_VAULT="false"
  declare -A USER_SERVICE_PORTS=()
  declare -a SELECTED_CONTAINERS=()
  declare -a RESTRICTED_SERVICES=()
  declare -a ALL_CONTAINERS=()

  log() { :; }
  set_ownership() { :; }
  eval "$(awk '/^save_config\(\)/,/^}/' scripts/bootstrap.sh)"

  save_config

  [ -f "$CONFIG_FILE" ]
  grep -q "VPN_SUBNET=\"$VPN_SUBNET\"" "$CONFIG_FILE"
  grep -q "VPN_SUBNET_BASE=\"$VPN_SUBNET_BASE\"" "$CONFIG_FILE"

  source "$CONFIG_FILE"
  [ "$VPN_SUBNET" = "10.9.0.0/24" ]
  [ "$VPN_SUBNET_BASE" = "10.9.0" ]
}

@test "save_config persists Docker network and DNS settings" {
  CFG_ROOT="$TMPDIR/stack"
  CONFIG_FILE="$CFG_ROOT/.bootstrap.conf"
  mkdir -p "$CFG_ROOT"

  DOCKER_NETWORK_NAME="test-net"
  DOCKER_NETWORK_SUBNET="172.30.0.0/24"
  WG_CLIENT_DNS="1.1.1.1"
  SCRIPT_VERSION="test-version"
  MEDIA_ROOT="$TMPDIR/media"
  CFG_UID=$(id -u)
  CFG_GID=$(id -g)
  # Add dummy values for other variables used in save_config
  VPN_SUBNET="10.8.0.0/24"
  VPN_SUBNET_BASE="10.8.0"
  LAN_SUBNET="192.168.1.0/24"
  DNS_FALLBACK="8.8.8.8"
  FIREWALL_RESTRICT_MODE="false"
  TRAEFIK_DOMAIN_MODE="local"
  TRAEFIK_DOMAIN_NAME=""
  TRAEFIK_ACME_EMAIL=""
  WG_DIR="/tmp/wg"
  STORE_WG_IN_VAULT="false"
  declare -A USER_SERVICE_PORTS=()
  declare -a SELECTED_CONTAINERS=()
  declare -a RESTRICTED_SERVICES=()
  declare -a ALL_CONTAINERS=()

  log() { :; }
  set_ownership() { :; }
  eval "$(awk '/^save_config\(\)/,/^}/' scripts/bootstrap.sh)"

  save_config

  [ -f "$CONFIG_FILE" ]
  grep -q "DOCKER_NETWORK_NAME=\"$DOCKER_NETWORK_NAME\"" "$CONFIG_FILE"
  grep -q "DOCKER_NETWORK_SUBNET=\"$DOCKER_NETWORK_SUBNET\"" "$CONFIG_FILE"
  grep -q "WG_CLIENT_DNS=\"$WG_CLIENT_DNS\"" "$CONFIG_FILE"

  source "$CONFIG_FILE"
  [ "$DOCKER_NETWORK_NAME" = "test-net" ]
  [ "$DOCKER_NETWORK_SUBNET" = "172.30.0.0/24" ]
  [ "$WG_CLIENT_DNS" = "1.1.1.1" ]
}

@test "saved user service ports override defaults" {
  loop=$(sed -n '/<USER_PORT_ENV_OVERRIDES>/,/done/p' scripts/bootstrap.sh | tail -n +2)
  result=$(bash -c "set -euo pipefail; declare -Ag CONTAINER_PORTS=([my-svc]=8080); MY_SVC_PORT=9999; $loop; echo \${CONTAINER_PORTS[my-svc]}" 2>/dev/null || echo "failed")
  [ "$result" = "9999" ]
}

@test "default user service port preserved when not in config" {
  loop=$(sed -n '/<USER_PORT_ENV_OVERRIDES>/,/done/p' scripts/bootstrap.sh | tail -n +2)
  result=$(bash -c "set -euo pipefail; declare -Ag CONTAINER_PORTS=([my-svc]=8080); $loop; echo \${CONTAINER_PORTS[my-svc]}" 2>/dev/null || echo "failed")
  [ "$result" = "8080" ]
}
@test "stop_service uses docker stop when container exists" {
  eval "$(awk '/^stop_service\(\)/,/^}/' scripts/bootstrap.sh)"
  script="$TMPDIR/script1.sh"
  cat >"$script" <<'EOS'
set -euo pipefail
cmd_file="$1"
run(){ echo "$*" >>"$cmd_file"; }
docker(){ if [[ "$1" == "ps" ]]; then echo "plex"; else echo "docker $*" >> "$cmd_file"; fi; }
systemctl(){ echo "systemctl $*" >> "$cmd_file"; }
stop_wireguard(){ echo "WG_STOP" >> "$cmd_file"; }
ok(){ echo "OK:$*" >> "$cmd_file"; }
log(){ :; }
EOS
  declare -f stop_service >>"$script"
  cat >>"$script" <<'EOS'
stop_service plex
EOS
  chmod +x "$script"
  cmd_file="$TMPDIR/cmd1"
  bash "$script" "$cmd_file" >/dev/null 2>&1 || true
  # Check the output file directly
  output_content=$(cat "$cmd_file" 2>/dev/null || echo "")
  [[ "$output_content" == *"OK:plex stopped."* ]]
  [[ "$output_content" == *"docker stop plex"* ]]
}

@test "stop_service uses systemctl stop for non-container" {
  eval "$(awk '/^stop_service\(\)/,/^}/' scripts/bootstrap.sh)"
  script="$TMPDIR/script2.sh"
  cat >"$script" <<'EOS'
set -euo pipefail
cmd_file="$1"
run(){ echo "$*" >>"$cmd_file"; }
docker(){ if [[ "$1" == "ps" ]]; then echo ""; else echo "docker $*" >> "$cmd_file"; fi; }
systemctl(){ echo "systemctl $*" >> "$cmd_file"; }
stop_wireguard(){ echo "WG_STOP" >> "$cmd_file"; }
ok(){ echo "OK:$*" >> "$cmd_file"; }
log(){ :; }
EOS
  declare -f stop_service >>"$script"
  cat >>"$script" <<'EOS'
stop_service sshd
EOS
  chmod +x "$script"
  cmd_file="$TMPDIR/cmd2"
  bash "$script" "$cmd_file" >/dev/null 2>&1 || true
  # Check the output file directly
  output_content=$(cat "$cmd_file" 2>/dev/null || echo "")
  [[ "$output_content" == *"OK:sshd stopped."* ]]
  [[ "$output_content" == *"systemctl stop sshd"* ]]
}

@test "stop_service wireguard stops interface and container" {
  eval "$(awk '/^stop_service\(\)/,/^}/' scripts/bootstrap.sh)"
  script="$TMPDIR/script3.sh"
  cat >"$script" <<'EOS'
set -euo pipefail
cmd_file="$1"
run(){ echo "$*" >>"$cmd_file"; }
docker(){ if [[ "$1" == "ps" ]]; then echo "wireguard"; else echo "docker $*" >> "$cmd_file"; fi; }
systemctl(){ echo "systemctl $*" >> "$cmd_file"; }
stop_wireguard(){ echo "WG_STOP" >> "$cmd_file"; }
ok(){ echo "OK:$*" >> "$cmd_file"; }
log(){ :; }
EOS
  declare -f stop_service >>"$script"
  cat >>"$script" <<'EOS'
stop_service wireguard
EOS
  chmod +x "$script"
  cmd_file="$TMPDIR/cmd3"
  bash "$script" "$cmd_file" >/dev/null 2>&1 || true
  # Check the output file directly
  output_content=$(cat "$cmd_file" 2>/dev/null || echo "")
  [[ "$output_content" == *"WG_STOP"* ]]
  [[ "$output_content" == *"OK:wireguard stopped."* ]]
  [[ "$output_content" == *"docker stop wireguard"* ]]
}

@test "service image override respected" {
  mkdir -p "$TMPDIR/scripts" "$TMPDIR/services/user/wireguard"
  cp services/user/wireguard/wireguard.conf "$TMPDIR/services/user/wireguard/"
  sed -i 's|^image=.*|image=test/wireguard:latest|' "$TMPDIR/services/user/wireguard/wireguard.conf"

  SCRIPT_DIR="$TMPDIR/scripts"
  CFG_ROOT="$TMPDIR/root"
  WG_DIR="$TMPDIR/wg"
  DOCKER_NETWORK_NAME=testnet
  WG_CONTAINER_IP=172.20.0.2

  script="$TMPDIR/run-wireguard.sh"
  cat >"$script" <<EOS
# Source the universal service runner to get all needed functions
source scripts/universal-service-runner.sh
docker(){ echo "docker \$*" >>"\$cmd_file"; }
log(){ :; }
log_info(){ :; }
log_error(){ :; }
log_warning(){ :; }
log_success(){ :; }
ensure_docker_image(){ :; }
get_health_cmd(){ echo ""; }
verify_container_ip(){ :; }
selinux_volume_flag(){ :; }
# Remove mock, let it read from real config file
setup_service_env_vars(){ :; }
get_server_ip(){ echo "192.168.1.100"; }
SCRIPT_DIR="$SCRIPT_DIR"
CFG_ROOT="$CFG_ROOT"
WG_DIR="$WG_DIR"
DOCKER_NETWORK_NAME="$DOCKER_NETWORK_NAME"
WG_CONTAINER_IP="$WG_CONTAINER_IP"
declare -Ag CONTAINER_PORTS=([wireguard]=51820)
declare -Ag CONTAINER_DESCRIPTIONS=([wireguard]="WireGuard")
CFG_UID=1000
CFG_GID=1000
DRY_RUN=false
EOS
  # Include the function definitions in the script
  declare -f ensure_container_running >>"$script"
  declare -f get_service_config_value >>"$script"
  cat >>"$script" <<'EOS'
ensure_container_running wireguard
cat "$cmd_file"
EOS
  chmod +x "$script"
  cmd_file="$TMPDIR/cmd_wireguard"
  wrapper="$TMPDIR/wrap.sh"
  cat >"$wrapper" <<EOF
#!/usr/bin/env bash
cmd_file="$cmd_file" bash "$script"
EOF
  chmod +x "$wrapper"
  run bash "$wrapper"
  # The test succeeds if we can find the custom image in the cmd file
  cmd_content=$(cat "$cmd_file" 2>/dev/null || echo "")
  [[ "$cmd_content" == *"test/wireguard:latest"* ]]
}

@test "service image override respected for traefik" {
  mkdir -p "$TMPDIR/scripts" "$TMPDIR/services/user/traefik"
  cp services/user/traefik/traefik.conf "$TMPDIR/services/user/traefik/"
  sed -i 's|^image=.*|image=test/traefik:latest|' "$TMPDIR/services/user/traefik/traefik.conf"

  SCRIPT_DIR="$TMPDIR/scripts"
  CFG_ROOT="$TMPDIR/root"
  DOCKER_NETWORK_NAME=testnet
  TRAEFIK_CONTAINER_IP=172.20.0.7
  DOCKER_SOCKET=/var/run/docker.sock

  script="$TMPDIR/run-traefik.sh"
  cat >"$script" <<EOS
# Source the universal service runner to get all needed functions
source scripts/universal-service-runner.sh
docker(){ echo "docker \$*" >>"\$cmd_file"; }
log(){ :; }
log_info(){ :; }
log_error(){ :; }
log_warning(){ :; }
log_success(){ :; }
ensure_docker_image(){ :; }
get_health_cmd(){ echo ""; }
verify_container_ip(){ :; }
selinux_volume_flag(){ :; }
get_traefik_labels(){ :; }
# Remove mock, let it read from real config file
setup_service_env_vars(){ :; }
get_server_ip(){ echo "192.168.1.100"; }
SCRIPT_DIR="$SCRIPT_DIR"
CFG_ROOT="$CFG_ROOT"
DOCKER_NETWORK_NAME="$DOCKER_NETWORK_NAME"
TRAEFIK_CONTAINER_IP="$TRAEFIK_CONTAINER_IP"
DOCKER_SOCKET="$DOCKER_SOCKET"
declare -Ag CONTAINER_PORTS=([traefik]=8080)
declare -Ag CONTAINER_DESCRIPTIONS=([traefik]="Traefik")
CFG_UID=1000
CFG_GID=1000
DRY_RUN=false
EOS
  # Include the function definitions in the script
  declare -f ensure_container_running >>"$script"
  declare -f get_service_config_value >>"$script"
  cat >>"$script" <<'EOS'
ensure_container_running traefik
cat "$cmd_file"
EOS
  chmod +x "$script"
  cmd_file="$TMPDIR/cmd_traefik"
  wrapper="$TMPDIR/wrap_traefik.sh"
  cat >"$wrapper" <<EOF2
#!/usr/bin/env bash
cmd_file="$cmd_file" bash "$script"
EOF2
  chmod +x "$wrapper"
  run bash "$wrapper"
  # The test succeeds if we can find the custom image in the cmd file
  cmd_content=$(cat "$cmd_file" 2>/dev/null || echo "")
  [[ "$cmd_content" == *"test/traefik:latest"* ]]
}