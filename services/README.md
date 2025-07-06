# Service Configuration Directory

This directory contains service configuration files that define how Docker containers are deployed and managed by the CLINIC bootstrap system.

## Directory Structure

```
services/
└── user/           # User-defined services (managed automatically)
    ├── wireguard.conf      # VPN server
    ├── ollama.conf         # Local LLM inference
    ├── agentcare-mcp.conf  # Medical tool orchestration
    ├── postgres.conf       # Primary database
    ├── redis.conf          # Cache and session store
    ├── grafana.conf        # Monitoring dashboards
    ├── influxdb.conf       # Time series database
    ├── traefik.conf        # Reverse proxy (required)
    ├── n8n.conf           # Workflow automation
    └── config-web-ui.conf  # Configuration web interface
```

## Service Configuration Format

Each `.conf` file defines a Docker service with the following format:

```ini
# Service description
image=docker/image:tag
port=8080
description=Human readable description
volumes=host-path:/container-path;another-host:/container-path
env=ENV_VAR=value;ANOTHER_VAR=value
extra_args=--cap-add=NET_ADMIN --privileged
network_mode=custom|host
healthcheck=curl -f http://localhost:8080/health
user=1000:1000
requires_setup=traefik_config|wireguard_keys
```

### Configuration Keys

- **image** (required): Docker image to use
- **port** (required): Primary port the service listens on
- **description** (optional): Human-readable service description
- **volumes** (optional): Volume mounts (semicolon-separated)
- **env** (optional): Environment variables (semicolon-separated)
- **extra_args** (optional): Additional Docker run arguments
- **network_mode** (optional): `custom` (default) or `host`
- **healthcheck** (optional): Health check command
- **user** (optional): User specification (UID:GID)
- **requires_setup** (optional): Special setup requirements

## Service Organization

### Universal Service Management
- **All services** are now managed through the universal-service-runner.sh system
- **Minimal set**: Traefik (reverse proxy) for basic functionality
- **User Choice**: All services are optional and can be selected during setup
- **Dynamic configuration** - services can be added or removed anytime

### Service Categories
- **Infrastructure**: Traefik (reverse proxy), WireGuard (VPN)
- **AI Services**: Ollama (LLM inference), AgentCare-MCP (tool orchestration)
- **Data Storage**: PostgreSQL (primary database), Redis (cache/sessions)
- **Monitoring**: Grafana (dashboards), InfluxDB (metrics)
- **Automation**: n8n (workflow automation)
- **Management**: Config Web UI

## Adding New Services

To add a new service:

1. Create a new `.conf` file in `services/user/`
2. Define the service configuration using the format above
3. Run `make validate` to check the configuration
4. Create service configuration files directly in the services/user/ directory

Example:
```bash
# Create services/user/nextcloud.conf
echo "image=nextcloud:latest" > services/user/nextcloud.conf
echo "port=8080" >> services/user/nextcloud.conf
echo "description=File hosting and collaboration" >> services/user/nextcloud.conf
echo "service_type=docker" >> services/user/nextcloud.conf
```

## Service Discovery

The bootstrap system automatically discovers services by:

1. Scanning both `core/` and `user/` directories
2. Reading all `.conf` files
3. Building the available service list dynamically
4. Loading service definitions at runtime

This means you can add services without modifying the main bootstrap script.
