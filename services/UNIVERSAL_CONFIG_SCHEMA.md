# Universal Service Configuration Schema
# This schema defines ALL possible configuration options for ANY service
# Services only need to specify values they use; everything else defaults to N/A

# =============================================================================
# UNIVERSAL SERVICE CONFIGURATION TEMPLATE
# =============================================================================
# Copy this template for any new service and fill in only what you need

# === BASIC INFORMATION ===
image=required                          # Docker image name (REQUIRED)
port=required                          # Primary service port (REQUIRED)  
description=Optional service description # Human-readable description

# === NETWORKING ===
additional_ports=N/A                   # Extra ports: 8080/tcp,9000/udp,1234
network_mode=bridge                    # bridge|host|none|container:name
static_ip=N/A                         # Static IP within Docker network
hostname=N/A                          # Custom hostname for container
dns_servers=N/A                       # Custom DNS: 8.8.8.8,1.1.1.1
dns_search=N/A                        # DNS search domains: example.com
expose_ports=N/A                      # Ports to expose without publishing: 80,443

# === STORAGE & VOLUMES ===
volumes=N/A                           # Named volumes: vol1:/path1,vol2:/path2
bind_mounts=N/A                       # Host bind mounts: /host/path:/container/path
tmpfs_mounts=N/A                      # Temporary filesystems: /tmp,/var/tmp
volume_driver=local                   # Volume driver: local|nfs|custom

# === ENVIRONMENT & CONFIGURATION ===
environment=N/A                       # Environment vars: KEY1=val1,KEY2=val2
env_file=N/A                         # Path to environment file
config_files=N/A                     # Config files to mount: /host/file:/container/file
secrets=N/A                          # Docker secrets: secret1,secret2
configs=N/A                          # Docker configs: config1,config2

# === RUNTIME & SECURITY ===
user=N/A                             # User/UID to run as: 1000 or user:group
group=N/A                            # Group/GID: 1000 or groupname
privileged=false                     # Run in privileged mode: true|false
read_only=false                      # Read-only root filesystem: true|false
security_opt=N/A                     # Security options: no-new-privileges,apparmor:unconfined
capabilities_add=N/A                 # Add capabilities: NET_ADMIN,SYS_TIME
capabilities_drop=N/A                # Drop capabilities: ALL,SETUID
no_new_privileges=true               # Prevent privilege escalation: true|false

# === RESOURCE LIMITS ===
memory_limit=N/A                     # Memory limit: 512m,1g,2048m
memory_reservation=N/A               # Memory soft limit: 256m
cpu_limit=N/A                        # CPU limit: 0.5,1,2 (cores)
cpu_reservation=N/A                  # CPU reservation: 0.25
pids_limit=N/A                       # Process limit: 100
ulimits=N/A                          # Ulimits: nofile:65536,nproc:4096

# === DEVICES & HARDWARE ===
devices=N/A                          # Device access: /dev/dri:/dev/dri,/dev/usb
device_cgroup_rules=N/A              # Device cgroup rules: c 1:1 rwm
gpu_access=false                     # Enable GPU access: true|false
gpu_device_ids=N/A                   # Specific GPU IDs: 0,1 or all
runtime=runc                         # Container runtime: runc|nvidia|custom

# === HEALTH & MONITORING ===
health_check=N/A                     # Health check command: curl -f http://localhost/health
health_interval=30s                  # Health check interval
health_timeout=10s                   # Health check timeout
health_retries=3                     # Health check retries
health_start_period=60s              # Grace period during startup
restart_policy=unless-stopped        # no|always|on-failure|unless-stopped
restart_max_attempts=5               # Max restart attempts for on-failure

# === LOGGING ===
log_driver=json-file                 # Logging driver: json-file|syslog|journald
log_options=N/A                      # Log options: max-size:10m,max-file:3
logging_tag=N/A                      # Custom logging tag

# === DOMAIN & SSL INTEGRATION ===
domain_routing=false                 # Enable Traefik domain routing: true|false
subdomain=N/A                        # Custom subdomain (default: service name)
ssl_mode=auto                        # auto|manual|disabled
ssl_cert_path=N/A                    # Custom SSL certificate path
ssl_key_path=N/A                     # Custom SSL key path
auth_required=false                  # Require authentication: true|false
auth_type=basic                      # basic|oauth|ldap|custom

# === SERVICE INTEGRATION ===
requires_services=N/A                # Required services: database,cache,redis
conflicts_with=N/A                   # Conflicting services: apache,nginx
waits_for=N/A                        # Wait for services: database:healthy,redis:started
service_discovery=true               # Enable service discovery: true|false
load_balancer=false                  # Enable load balancing: true|false

# === SPECIAL FEATURES ===
media_access=false                   # Mount media directories: true|false
media_paths=N/A                      # Custom media paths: /movies,/tv,/music
backup_paths=N/A                     # Paths to backup: /data,/config,/var/lib
vpn_client=false                     # Route through VPN: true|false
vpn_config=N/A                       # VPN configuration file path
host_networking=false                # Use host networking: true|false
ipc_mode=N/A                         # IPC mode: container:name|host|shareable
pid_mode=N/A                         # PID mode: container:name|host

# === DNS SERVICES ===
dns_service=false                    # Provides DNS service: true|false
dns_ports=N/A                        # DNS ports: 53/tcp,53/udp,5353/udp
dns_upstream=N/A                     # Upstream DNS servers: 8.8.8.8,1.1.1.1
dns_block_lists=N/A                  # DNS block lists: malware,ads,tracking
dns_local_records=N/A                # Local DNS records: host1:ip1,host2:ip2

# === DATABASE SERVICES ===
database_type=N/A                    # Database type: mysql|postgres|mongo|redis
database_name=N/A                    # Default database name
database_user=N/A                    # Default database user
database_password_env=N/A            # Environment variable for password
database_init_scripts=N/A            # Initialization scripts: script1.sql,script2.js
database_backup=false                # Enable automatic backups: true|false

# === WEB SERVICES ===
web_service=false                    # Provides web interface: true|false
web_port=N/A                         # Web interface port (if different from main)
web_path=N/A                         # Web interface path: /admin,/ui
web_auth=false                       # Web interface needs auth: true|false
static_files=N/A                     # Static file directories: /var/www,/public

# === PROXY SERVICES ===
proxy_service=false                  # Provides proxy functionality: true|false
proxy_backends=N/A                   # Backend services: service1:port1,service2:port2
proxy_config_template=N/A            # Proxy configuration template path
load_balancing_method=round_robin    # round_robin|least_conn|ip_hash

# === LIFECYCLE HOOKS ===
pre_start_script=N/A                 # Script to run before container starts
post_start_script=N/A                # Script to run after container starts
pre_stop_script=N/A                  # Script to run before container stops
post_stop_script=N/A                 # Script to run after container stops
init_container=N/A                   # Init container image for setup
startup_delay=0                      # Delay before starting (seconds)
shutdown_timeout=10                  # Graceful shutdown timeout (seconds)

# === ADVANCED FEATURES ===
cgroup_parent=N/A                    # Custom cgroup parent
oom_kill_disable=false               # Disable OOM killer: true|false
oom_score_adj=N/A                    # OOM score adjustment: -1000 to 1000
shm_size=64m                         # Shared memory size
sysctls=N/A                          # Sysctl settings: net.core.somaxconn:1024
storage_opt=N/A                      # Storage driver options
platform=N/A                        # Target platform: linux/amd64,linux/arm64

# === DEVELOPMENT & DEBUGGING ===
development_mode=false               # Enable development features: true|false
debug_ports=N/A                      # Debug/development ports: 9229,5005
volume_mounts_rw=false               # Mount volumes as read-write in dev: true|false
auto_reload=false                    # Auto-reload on file changes: true|false
debug_logging=false                  # Enable debug logging: true|false

# === NETWORK DISCOVERY CONFIGURATION ===
enable_discovery=false                # Enable DLNA/mDNS/UPnP discovery protocols: true|false
discovery_ports=1900/udp,5353/udp   # Additional ports for discovery (comma-separated, auto-detected for common services)
discovery_protocol=both               # Type of discovery to enable: dlna|mdns|both (default: both)
multicast_relay=false                 # Bridge multicast between Docker network and host: true|false (default: false)

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

# SIMPLE SERVICE (Redis):
# image=redis:alpine
# port=6379
# volumes=redis-data:/data
# environment=REDIS_PASSWORD=secret
# health_check=redis-cli ping
# description=Redis cache server

# OLLAMA LLM SERVICE:
# image=ollama/ollama:latest
# port=11434
# volumes=ollama-models:/root/.ollama
# gpu_support=true
# environment=OLLAMA_HOST=0.0.0.0
# health_check=curl -f http://172.20.0.10:11434/api/tags
# description=Local LLM inference server

# AGENTCARE-MCP SERVICE:
# image=agentcare/mcp:latest
# port=3000
# volumes=agentcare-config:/app/config,agentcare-data:/app/data
# environment=POSTGRES_URL=postgresql://postgres:password@postgres:5432/agentcare
# health_check=curl -f http://localhost:3000/health
# description=Medical tool orchestration platform

# PROXY SERVICE (Traefik):
# image=traefik:v3.0
# port=8080
# additional_ports=80,443
# proxy_service=true
# volumes=traefik-config:/etc/traefik,traefik-data:/data
# bind_mounts=/var/run/docker.sock:/var/run/docker.sock:ro
# ssl_mode=auto
# domain_routing=false
# health_check=curl -f http://localhost:8080/api/overview
# description=Traefik reverse proxy

# NETWORK DISCOVERY (Plex):
# image=plexinc/pms-docker
# port=32400
# enable_discovery=true
# discovery_protocol=dlna
# multicast_relay=true
# volumes=plex-config:/config,plex-transcode:/transcode
# environment=PLEX_CLAIM=claim-xyz,TZ=America/New_York,HOSTNAME=PlexServer
# media_access=true
# gpu_access=true
# domain_routing=true
# health_check=curl -f http://localhost:32400/web
# description=Plex Media Server with network discovery

# NETWORK DISCOVERY (Home Assistant):
# image=homeassistant/home-assistant:latest
# port=8123
# enable_discovery=true
# discovery_protocol=mdns
# discovery_ports=5353/udp,21063/tcp
# volumes=homeassistant-config:/config
# environment=TZ=America/New_York
# health_check=curl -f http://localhost:8123
# description=Home Assistant with network discovery
