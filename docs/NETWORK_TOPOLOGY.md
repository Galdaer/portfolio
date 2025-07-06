# Network Topology

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

When you create a custom service, the universal service runner automatically handles container networking. Services are automatically assigned IPs within the custom Docker network `172.20.0.x` range.

The `VPN_SUBNET` value sets the WireGuard client network while `VPN_SUBNET_BASE` controls sequential IP assignments. New peers receive IPs like `<VPN_SUBNET_BASE>.2`, `<VPN_SUBNET_BASE>.3`, and so on. Firewall rules reference `VPN_SUBNET` to restrict access.

Example `.env` override:

```bash
echo "OLLAMA_CONTAINER_IP=172.20.0.50" >> .env
```

You can also override the Docker network name, subnet, and WireGuard client DNS.
These values are saved to `.clinic-bootstrap.conf` on first run and automatically
restored whenever the file is sourced. The default config file path is
`$CFG_ROOT/.clinic-bootstrap.conf` (typically `/opt/intelluxe/clinic-stack/.clinic-bootstrap.conf`).
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
