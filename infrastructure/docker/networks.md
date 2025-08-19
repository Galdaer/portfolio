# Intelluxe AI Docker Network and Static IP Assignment

This document defines the Docker network topology and static IP assignments for all core services in the Intelluxe AI Healthcare System. Use this as the source of truth for predictable service discovery, firewall rules, and monitoring.

---

## Docker Network: `intelluxe-net`
- **Subnet:** `172.20.0.0/24`
- **Purpose:** Secure, HIPAA-compliant inter-service communication for all healthcare AI components.
- **Driver:** bridge (default)

---

## Static IP Assignments
| Service         | Container Name      | Static IP        | Notes                       |
|-----------------|--------------------|------------------|-----------------------------|
| Wireguard VPN   | wireguard          | 172.20.0.2       | Isolated, not on intelluxe-net |
| Grafana         | grafana            | 172.20.0.3       | Dashboards & monitoring     |
| n8n             | n8n                | 172.20.0.4       | Workflow automation         |
| Whisper         | whisper            | 172.20.0.5       | Speech-to-text              |
| ScispaCy        | scispacy           | 172.20.0.6       | Biomedical NLP              |
| Config Web UI   | config-web-ui      | 172.20.0.7       | System management           |
| Traefik         | traefik            | 172.20.0.8       | Reverse proxy               |
| Open WebUI      | open-webui         | 172.20.0.11      | AI chat interface           |
| Healthcare MCP  | healthcare-mcp     | 172.20.0.12      | Medical tools (auth proxy:3001, mcpo:3000) |
| ...             | ...                | ...              | Add new services here       |

**Healthcare MCP Architecture Notes:**
- **External Port 3001**: FastAPI authentication proxy for Open WebUI integration
- **Internal Port 3000**: mcpo backend for MCP protocol handling  
- **Tools Available**: 3 public research tools (search-pubmed, search-trials, get-drug-info)
- **Protected Tools**: 12 additional patient tools require paid FHIR/database APIs

- **Add new services** to this table as they are deployed.
- **Do not reuse IPs**; increment for each new service.

---

## Network Assignment Guidelines
- All core services must use `network_mode=intelluxe-net` and a unique static IP from the table above.
- Wireguard is for developer VPN access only and should be isolated from `intelluxe-net`.
- For production, use Tailscale for clinic staff and end users (see Phase 3).

---

## Example Docker Network Creation
```bash
docker network create --subnet=172.20.0.0/24 intelluxe-net
```

## Example Service Config
```conf
network_mode=intelluxe-net
static_ip=172.20.0.3
```

---

## Change Log
- 2025-07-12: Initial network and IP assignment documentation created.
