# 📖 Detailed Usage Guide

### Interactive Setup Walkthrough

The bootstrap script provides two main interaction modes:

#### **🎛️ Standard Setup (Recommended for beginners)**
```bash
sudo ./scripts/clinic-bootstrap.sh
```

**Step-by-step process:**

1. **Port Configuration** - Script shows current ports and asks if you want to change them
   - Shows: Ollama (11434), Grafana (3001), AgentCare-MCP (3000), etc.
   - Choose: Keep defaults or customize ports to avoid conflicts

2. **Service Configuration** - Configure healthcare AI services
   - Set up Ollama for local LLM inference
   - Configure AgentCare-MCP for medical tool orchestration
   - Set database connections for PostgreSQL and Redis

3. **Container Selection** - Choose which services to install
   - Shows all available containers with descriptions
   - Enter numbers (e.g., "1 3 5") or press Enter for all services
   - Selected containers will be started automatically

4. **Container Management Choice** - Decide on management mode
   - **"No" (recommended)**: Continue with automatic setup
   - **"Yes"**: Enter interactive container management menu

5. **Domain Configuration** (if Traefik selected)
   - **Local development**: No domain, access via IP:port
   - **Dynamic DNS**: Free domain (DuckDNS) with SSL certificates
   - **Local DNS**: Custom domain with hosts file modification
   - **VPN-only**: Domain routing only for VPN clients

6. **Security Configuration** - Configure network access restrictions
   - **Restrict all services**: LAN + VPN only (recommended)
   - **Keep open**: Allow internet access to all services
   - **Custom restrictions**: Choose per service

#### **⚙️ Advanced Container Management (For experienced users)**

If you choose "Yes" for container management, you get a detailed menu:

```
Container Management Menu
---------------------------------
1) traefik       Reverse proxy with automatic SSL    running
2) wireguard     Secure VPN server                   running  
3) ollama        Local LLM inference server          running
4) agentcare-mcp Medical tool orchestration          running
5) grafana       Dashboards and monitoring           running
6) influxdb      Time-series database for metrics    running
7) postgres      Primary database for Intelluxe     running
8) redis         Memory cache and session store     running
9) n8n           Workflow automation                 running
a) Start/Recreate All
s) Stop All
q) Continue setup with defaults
```

**Actions per container:**
- **Start/Recreate**: Pull latest image and start container
- **Stop**: Stop the container (keeps configuration)
- **Remove**: Delete container completely (keeps data volumes)
- **Status**: Show detailed container status and logs

### Script Options and Flags

```bash
# Interactive mode (default)
sudo ./scripts/clinic-bootstrap.sh

# Non-interactive mode with defaults
sudo ./scripts/clinic-bootstrap.sh --non-interactive

# Force defaults without prompting
sudo ./scripts/clinic-bootstrap.sh --force-defaults

# Skip container selection (use all containers)
sudo SKIP_CONTAINER_SELECTION=true ./scripts/clinic-bootstrap.sh

# Run with specific log level
sudo LOG_LEVEL=DEBUG ./scripts/clinic-bootstrap.sh

# Reset WireGuard server keys and regenerate client configs
sudo ./scripts/clinic-bootstrap.sh --reset-wg-keys
# Stop a running service (e.g., WireGuard)
sudo ./scripts/clinic-bootstrap.sh --stop-service wireguard
# Use --non-interactive or set NON_INTERACTIVE=true for unattended runs
```

### Directory Structure

```
intelluxe/
├── scripts/                           # All automation scripts
│   ├── clinic-bootstrap.sh              # Main bootstrap script
│   ├── clinic-lib.sh                    # Shared functions library
│   ├── clinic-auto-repair.sh            # Automated container health checks
│   ├── clinic-diagnostics.sh            # System diagnostics and monitoring
│   ├── clinic-reset.sh                  # System reset and cleanup
│   ├── clinic-teardown.sh               # Complete system teardown
│   ├── clinic-netns-setup.sh            # Network namespace configuration
│   ├── duckdns-update.sh              # Dynamic DNS updates
│   ├── media-mount-check.sh           # Storage mount verification
│   ├── setup-mergerfs.sh              # Multi-drive pooling setup
│   ├── diagnostic-pusher.sh           # Metrics collection and pushing
│   ├── resource-pusher.sh             # Host resource metrics exporter
│   └── systemd-summary.sh             # SystemD service status reports
├── systemd/                           # SystemD service definitions
│   ├── clinic-auto-repair.service       # Auto-repair timer service
│   ├── clinic-auto-repair.timer         # Auto-repair scheduling
│   ├── clinic-diagnostics.service       # Diagnostics service
│   ├── clinic-diagnostics.timer         # Diagnostics scheduling
│   ├── diagnostic-pusher.service      # Metrics push service
│   ├── diagnostic-pusher.timer        # Metrics push scheduling
│   ├── resource-pusher.service        # Host metrics push service
│   ├── resource-pusher.timer          # Host metrics push scheduling
│   ├── clinic-reset.service             # Reset service
│   ├── clinic-teardown.service          # Teardown service
│   ├── clinic-netns.service             # Network namespace service
│   ├── duckdns-update.service         # DNS update service
│   ├── duckdns-update.timer           # DNS update scheduling
│   ├── media-mount-check.service      # Storage monitoring service
│   ├── git-pull.service               # Runs git pull for the runtime clone
│   ├── git-pull.timer                 # Pulls new commits every 10 minutes
│   └── grafana-provision.service      # Restart Grafana to load updated dashboards
├── DEVELOPMENT_ROADMAP.md             # Public roadmap and features
├── README.md                          # This file
└── udev/                              # udev rules for automatic drive mounting (repo root)
    └── 99-media-mount.rules           # Triggers media-mount-check.sh on drive detection

Generated during setup:
├── /opt/intelluxe/clinic-stack/        # Main configuration directory
│   ├── logs/                          # Application logs
│   │   ├── bootstrap.log              # Main setup log
│   │   ├── auto-repair.log            # Repair operation logs
│   │   ├── diagnostics.log            # System diagnostic logs
│   │   └── systemd-summary.log        # Systemd service summary logs
│   ├── backups/                       # System backups
│   │   ├── docker-compose.yml.backup  # Compose file backups
│   │   └── configs/                   # Configuration backups
│   ├── configs/                       # Service configurations
│   │   ├── traefik/                   # Traefik configuration
│   │   ├── grafana/                   # Grafana dashboards
│   │   ├── ollama/                    # Ollama model configuration
│   │   ├── agentcare-mcp/             # AgentCare-MCP setup
│   │   ├── postgres/                  # PostgreSQL database config
│   │   ├── redis/                     # Redis cache configuration
│   │   └── n8n/                       # n8n workflow automation
│   ├── docker-compose.yml             # Main compose file
│   └── .clinic-bootstrap.conf           # Bootstrap configuration
└── /etc/wireguard/                    # WireGuard active configurations
    ├── wg0.conf                       # Server configuration
    ├── wg0-server.private             # Server private key
    ├── wg0-server.public              # Server public key
    ├── clients/                       # Client configurations
    │   ├── client1.conf               # Individual client configs
    │   ├── client1.private            # Client private keys
    │   ├── client1.public             # Client public keys
    │   └── client1.qr.png             # QR codes for mobile setup
    └── keys/                          # Key management
        ├── server-keys/               # Server key backups
        └── client-keys/               # Client key archives
```
The udev rule `99-media-mount.rules` launches `media-mount-check.sh` via `systemd-run` whenever an ext4 block device is added (ACTION="add", SUBSYSTEM="block"). This immediate check complements the periodic `media-mount-check.timer`.

Example rule contents:

```
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_TYPE}=="ext4", \
  RUN+="/usr/bin/systemd-run --no-block /usr/local/bin/media-mount-check.sh --dev $env{DEVNAME}"
```
### Service Dependencies and Startup Order

1. **Foundation Services** (started first):
   - Docker daemon
   - Network interfaces and VLANs

2. **Core Infrastructure**:
   - Traefik (reverse proxy) - required for SSL termination
   - AdGuard Home (DNS) - provides local DNS resolution

3. **Application Services**:
   - Plex Media Server - depends on storage mounts
   - Grafana + InfluxDB - depends on Traefik for SSL

4. **Security Layer**:
   - WireGuard VPN - configured after all services are running
   - Firewall rules - applied last to secure everything

### Network Topology

```
Internet
    │
    ├── Router/Modem
    │   └── Primary Network: 192.168.1.0/24
    │
    ├── Homelab Server (this system)
    │   ├── Main Interface: 192.168.1.100 (example)
    │   ├── Docker Bridge: 172.20.0.0/16
    │   └── WireGuard VPN: 10.8.0.0/24
    │
    ├── Guest Network: 192.168.10.0/24 (planned)
    │   └── Isolated from main network
    │
    └── IoT Network: 192.168.20.0/24 (planned)
        └── Smart home devices
```

### Container Network Configuration

- **Traefik**: Ports 80, 443, 8080 (HTTP/HTTPS/Dashboard) - IP: 172.20.0.4
- **Ollama**: Port 11434 (LLM inference API) - IP: 172.20.0.7
- **AgentCare-MCP**: Port 3000 (tool orchestration) - IP: 172.20.0.3
- **Grafana**: Port 3001 (monitoring dashboard) - IP: 172.20.0.5
- **InfluxDB**: Port 8086 (metrics database) - IP: 172.20.0.6
- **PostgreSQL**: Port 5432 (primary database) - IP: 172.20.0.8
- **Redis**: Port 6379 (cache/sessions) - IP: 172.20.0.9
- **n8n**: Port 5678 (workflow automation) - IP: 172.20.0.10
- **WireGuard**: Port 51820 (VPN tunnel) - IP: 172.20.0.2

### Container IP Environment Variables

Customize container IP addresses with environment variables. Add them to a `.env` file or export them in your shell to override the defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `VPN_SUBNET` | `10.8.0.0/24` | CIDR subnet for WireGuard clients and firewall rules |
| `VPN_SUBNET_BASE` | `10.8.0` | Base (first three octets) used when assigning sequential client IPs |
| `LAN_SUBNET` | `192.168.0.0/16` | CIDR subnet for LAN firewall rules (must be valid) |

When you create a custom service, create a `.conf` file in `services/user/` using the universal configuration format. The universal service runner automatically discovers and manages all services defined in `.conf` files.

The `VPN_SUBNET` value sets the WireGuard client network while `VPN_SUBNET_BASE` controls sequential IP assignments. New peers receive IPs like `<VPN_SUBNET_BASE>.2`, `<VPN_SUBNET_BASE>.3`, and so on. Firewall rules reference `VPN_SUBNET` to restrict access.

Example `.env` override:

```bash
echo "WATCHTOWER_CONTAINER_IP=172.20.0.50" >> .env
```

You can also override the Docker network name, subnet, and WireGuard client DNS.
These values are saved to `.clinic-bootstrap.conf` on first run and automatically
restored whenever the file is sourced.
```bash
echo "DOCKER_NETWORK_NAME=intelluxe-net" >> .env
echo "DOCKER_NETWORK_SUBNET=172.25.0.0/24" >> .env
echo "WG_CLIENT_DNS=1.1.1.1" >> .env
echo "DOCKER_SOCKET=/var/run/docker.sock" >> .env
```

Set a custom interval for the repository auto-update timer:

```bash
echo "GIT_PULL_INTERVAL=10min" >> .env
```
This controls how often `git-pull.timer` runs `git-pull.service`.

### Make Commands

```bash
# Set up development environment
make setup

# Lint all scripts (shell and Python)
make lint

# Validate configuration and compose syntax
make validate

# Run tests
make test

# Clean temporary files
make clean

# Lint scripts with shellcheck and run Python linters
make lint

# Deploy to remote server (when implemented)
make deploy
```

  > **Note**: `make validate` runs the bootstrap script with `--non-interactive`, so passwordless sudo is required. `make deps` invokes `sudo` to install tools like [Bats](https://bats-core.readthedocs.io/en/latest/installation.html), so passwordless sudo is also needed for it to succeed. For apt-based systems, `setup-environment.sh` installs all packages in a single command to greatly accelerate this step. The installer sets `DEBIAN_FRONTEND=noninteractive` and runs `apt-get install -y --no-install-recommends` to avoid prompts and recommended packages.
  > Set the `BOOTSTRAP_CONFIG` environment variable to use a custom configuration path during testing.
    > `make validate` (or running `./scripts/clinic-bootstrap.sh --validate`) requires Docker to be installed and the Docker daemon running. If Docker isn't installed, follow the [official installation guide](https://docs.docker.com/get-docker/) to set it up.
    > When `CI=true`, the `make validate` target skips Docker checks if Docker is unavailable.
    > The bootstrap script supports `--skip-docker-check` for this purpose.
    > Compose files are linted via `docker compose config -q` during validation.

### Configuration Management

The bootstrap script creates and manages several configuration files:

- **Main Config**: `/opt/intelluxe/clinic-stack/.clinic-bootstrap.conf`
- **WireGuard**: `/etc/wireguard/wg0.conf`
- **Docker Compose**: `/opt/intelluxe/clinic-stack/docker-compose.yml`
- **Service Configs**: Individual container configurations in `/opt/intelluxe/clinic-stack/`
- **DuckDNS Env**: `${CFG_ROOT}/duckdns/duckdns.env` (loaded by `duckdns-update.service`)

### Data Drive Setup

The script can automatically detect and configure media drives:

1. **Single Drive**: Direct mount to `/media`
2. **Multiple Drives**: Uses mergerfs to combine drives
3. **Network Storage**: Can mount NFS/SMB shares

### Monitoring and Logs

- **System Logs**: `${CFG_ROOT}/logs/bootstrap.log` (default `/opt/intelluxe/clinic-stack/logs/bootstrap.log`)
- **Container Logs**: `docker logs <container-name>`
- **Grafana Dashboard**: Depends on your Traefik configuration:
  - Local mode: `http://your-server-ip:3001`
  - Domain mode: `https://grafana.yourdomain.com` (e.g., `https://grafana.example.duckdns.org`)
  - VPN-only mode: `https://grafana.yourdomain.com` (VPN clients only)
- **Service Status**: `systemctl status <service>`

### Automated Maintenance Scripts

These helpers run automatically via systemd timers but can also be invoked manually if needed:

#### `clinic-auto-repair.sh`
Runs every 5 minutes via `clinic-auto-repair.timer` to restart unhealthy containers.
```bash
sudo ./scripts/clinic-auto-repair.sh
```

#### `diagnostic-pusher.sh`
Runs every 30 minutes via `diagnostic-pusher.timer` to export diagnostics to InfluxDB.
```bash
sudo ./scripts/diagnostic-pusher.sh
```

#### `resource-pusher.sh`
Runs every 10 minutes via `resource-pusher.timer` to send host CPU, memory, and disk metrics to InfluxDB.
```bash
sudo ./scripts/resource-pusher.sh
```

### Adding Services

Add new services by creating `.conf` files in the `services/user/` directory:

```bash
# Example: services/user/myservice.conf
image=my/image:latest
port=1234
description=My custom service
service_type=docker
# Optional: volumes=./myservice-config:/app/config
# Optional: env=MY_VAR=value;ANOTHER_VAR=value
# Optional: network_mode=custom
# Optional: healthcheck=curl -f http://localhost:1234/health
```

The universal service runner automatically discovers and manages services from these configuration files. Key features:

- **Auto-discovery**: No need to modify bootstrap scripts
- **Universal format**: Same configuration for all services
- **Flexible networking**: Support for custom networks, host mode, etc.
- **Health monitoring**: Built-in health checks
- **Traefik integration**: Automatic reverse proxy setup

### Configuration Web UI


A lightweight Flask interface provides a simple form to edit `*.clinic-bootstrap.conf`. The bootstrap script automatically enables and starts `config-web-ui.service`. Open `http://localhost:<CONFIG_WEB_UI_PORT>` (defaults to `9123`) to make changes. If you have a public IP or domain name (e.g., a DuckDNS address), use that hostname instead of `localhost`.
The service reads `CONFIG_WEB_UI_PORT` from `$CFG_ROOT/.clinic-bootstrap.conf`; restart `config-web-ui.service` after editing this value to use a different port.
  - *Changing this field through the web form does not restart the unit automatically.* Run `sudo systemctl restart config-web-ui.service` for the new port to take effect.

Submissions trigger `clinic-bootstrap.sh --non-interactive` so changes apply immediately.
You can also click **Run Bootstrap** to manually invoke the same script without modifying values.
Additional maintenance buttons provide:
- **Self Update Script** – run `clinic-bootstrap.sh --self-update` to refresh the bootstrapper.
- **Run Diagnostics** – execute `clinic-diagnostics.sh` for system info.
- **Run Auto Repair** – invoke `clinic-auto-repair.sh` for automated fixes.
- **Run System Reset** – invoke `clinic-reset.sh --non-interactive` to rebuild the stack.
- **Systemd Summary** – view `systemd-summary.sh` output for service status.
- **Run Teardown** – invoke `clinic-teardown.sh --force --all` to remove the entire stack.
 - **Add Service** – enter a service name, Docker image, default port and description. The form creates a service configuration file directly in the `services/user/` directory using the universal configuration format.
  - **Remove Service** – run `clinic-bootstrap.sh --remove <service>` or use the service control forms to delete a container while keeping its data.
  - Use the service control forms to **Start**, **Restart**, or **Stop** containers via `clinic-bootstrap.sh`.
Selecting or deselecting services via the `SELECTED_CONTAINERS` field will also run the bootstrap automatically so containers are created or removed.
A **View Logs** link lists files under `~/clinic-stack/logs/` for quick troubleshooting.
Click any container name in the status table to view its recent Docker logs.

The editor also exposes advanced settings such as `VPN_SUBNET`, `VPN_SUBNET_BASE`,
`LAN_SUBNET`, `DNS_FALLBACK`, `FIREWALL_RESTRICT_MODE`, and `RESTRICTED_SERVICES`.

To add a desktop launcher that opens your default browser on the configured port, copy `misc/config-web-ui.desktop` to `~/.local/share/applications`. The entry calls `/usr/local/bin/open-config-web-ui.sh`, which is installed when you run `sudo make install`; update the `Exec` line if you choose a different location.
If your configuration file lives outside the default `~/clinic-stack` directory, set `CFG_ROOT` to that folder so the bootstrap scripts and web UI can locate `.clinic-bootstrap.conf` there. Add `export CFG_ROOT=/path/to/clinic-stack` to `~/.bashrc` or `~/.profile` for a persistent override, then launch the desktop entry. This variable also controls the log directory—logs are written under `$CFG_ROOT/logs`.
`git-pull.service` uses `RUNTIME_REPO_DIR` from the same config file; adjust this path if your runtime clone lives elsewhere.
Set `BOOTSTRAP_PATH` if `clinic-bootstrap.sh` resides outside your `PATH`:

```bash
export BOOTSTRAP_PATH=/opt/scripts/clinic-bootstrap.sh
```
The web UI attempts `shutil.which("clinic-bootstrap.sh")` and falls back to `/usr/local/bin/clinic-bootstrap.sh` when unset.

Set `TEARDOWN_PATH` if `clinic-teardown.sh` resides outside your `PATH`:

```bash
export TEARDOWN_PATH=/opt/scripts/clinic-teardown.sh
```
The web UI attempts `shutil.which("clinic-teardown.sh")` and falls back to `/usr/local/bin/clinic-teardown.sh` when unset.

The web UI creates service configuration files directly in the universal format.

### Security Features

- **Firewall**: Automated UFW/iptables configuration
- **VPN Access**: Admin services restricted to VPN users
- **SSL Certificates**: Automatic Let's Encrypt via Traefik
- **Network Isolation**: Containers run in isolated networks

### WireGuard VPN Setup and QR Code Generation

The bootstrap script automatically generates WireGuard configurations and QR codes for easy client setup.

#### **QR Code Generation Process**

When setting up WireGuard clients, the script:

1. **Generates Client Configuration**:
   ```bash
   # Example client config (client1.conf)
   [Interface]
   PrivateKey = [generated-private-key]
   Address = 10.8.0.2/24
   DNS = 10.8.0.1

   [Peer]
   PublicKey = [server-public-key]
   Endpoint = your-domain.duckdns.org:51820
   AllowedIPs = 0.0.0.0/0
   ```

2. **Creates QR Code**: `qrencode -t PNG -o /etc/wireguard/clients/client1.qr.png < client1.conf`

3. **Displays QR Code**: Shows the QR code in terminal for immediate scanning

#### **Client Setup Methods**

**📱 Mobile Devices (iOS/Android)**
- **Recommended method**: Scan QR code with camera app
- **Process**:
  1. Open WireGuard app on phone
  2. Tap "+" → "Create from QR code"
  3. Point camera at QR code displayed in terminal
  4. Configuration automatically imports
  5. Tap to connect immediately

**💻 Desktop/Laptop Computers**
- **Method 1: Manual Configuration** (recommended)
  ```bash
  # Copy the client config file
  sudo cp /etc/wireguard/clients/client1.conf /etc/wireguard/

  # Start the VPN connection
  sudo wg-quick up client1
  ```

- **Method 2: QR Code Bridge** (for Windows/macOS)
  ```bash
  # Display QR code in terminal
  qrencode -t ANSIUTF8 < /etc/wireguard/clients/client1.conf

  # Use phone to scan QR code, then export config and transfer to computer
  # OR use QR code reader software on computer
  ```

- **Method 3: File Transfer**
  ```bash
  # Transfer .conf file directly to client computer
  scp /etc/wireguard/clients/client1.conf user@client-computer:/etc/wireguard/
  ```

<details>
<summary><strong>QR Code Display Options</strong></summary>


The script provides multiple ways to view QR codes:

```bash
# Display QR code in terminal (ASCII art)
qrencode -t ANSIUTF8 < /etc/wireguard/clients/client1.conf

# Generate PNG file for sharing
qrencode -t PNG -s 6 -o client1-qr.png < /etc/wireguard/clients/client1.conf

# Display QR code on screen (if GUI available)
qrencode -t PNG -s 10 -o /tmp/qr.png < client1.conf && xdg-open /tmp/qr.png
```

</details>

<details>
<summary><strong>Cross-Platform Compatibility</strong></summary>


**Mobile Apps**:
- **iOS**: Official WireGuard app (App Store)
- **Android**: Official WireGuard app (Google Play)
- **Camera**: Most phones can read QR codes with built-in camera app

**Desktop Applications**:
- **Windows**: WireGuard for Windows (official client) - download from wireguard.com
- **macOS**: WireGuard for macOS (official client) - download from App Store or wireguard.com
- **Linux**: WireGuard tools package (install manually on client systems)
  ```bash
  # Install on client Linux systems
  sudo apt install wireguard-tools  # Ubuntu/Debian
  sudo dnf install wireguard-tools  # Fedora
  sudo pacman -S wireguard-tools    # Arch Linux
  ```

**QR Code Readers for Desktop**:
- **Windows**: Built-in Camera app, ZXing Decoder Online
- **macOS**: Preview app can read QR codes from images
- **Linux**: `zbar-tools` package (`zbarimg` command)

</details>

#### **Security Considerations**

- **QR codes contain private keys** - treat them as sensitive credentials
- **Auto-delete QR codes** after successful client setup
- **Regenerate client configs** if QR codes are compromised
- **Use VPN-only access** for admin services after setup
- **Reset server keys if compromised** using `clinic-bootstrap.sh --reset-wg-keys` or the web UI button (regenerates QR codes)

#### **Troubleshooting QR Codes**

**If QR code won't scan**:
1. **Increase terminal font size** for better resolution
2. **Generate larger PNG**: `qrencode -t PNG -s 10 -o large-qr.png`
3. **Use better lighting** when scanning with phone
4. **Try different QR reader apps** if camera app fails

**If configuration fails**:
1. **Check network connectivity** to server
2. **Verify firewall allows port 51820**
3. **Confirm DNS resolution** for domain name
4. **Check client IP doesn't conflict** with existing network

