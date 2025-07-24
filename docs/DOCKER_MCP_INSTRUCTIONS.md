## Setting Up Docker Desktop + MCP Toolkit/Gateway

### Step 1: Install Docker Desktop

**Important**: This will replace your current Docker Engine setup, but all your containers and data will remain intact.

```bash
# Download Docker Desktop for Linux
wget https://desktop.docker.com/linux/main/amd64/docker-desktop-4.26.1-amd64.deb

# Install Docker Desktop
sudo apt install ./docker-desktop-4.26.1-amd64.deb

# Start Docker Desktop
systemctl --user start docker-desktop

# Enable auto-start
systemctl --user enable docker-desktop
```

**Or use the GUI installer**:
1. Go to https://docs.docker.com/desktop/install/linux-install/
2. Download the `.deb` file for Ubuntu
3. Double-click to install

### Step 2: Verify Docker Desktop

```bash
# Check Docker Desktop is running
docker version
docker compose version

# Your existing containers should still be there
docker ps
```

### Step 3: Enable MCP Toolkit Extension

1. **Open Docker Desktop** (GUI application)
2. **Go to Extensions** (left sidebar)
3. **Browse Extensions** → Search for "MCP"
4. **Install MCP Toolkit** extension
5. **Install Docker MCP Gateway** extension (if separate)

### Step 4: Configure Your Healthcare MCP

In Docker Desktop:

1. **Open MCP Toolkit** extension
2. **Add MCP Server**:
   - **Name**: `Intelluxe Healthcare`
   - **URL**: `http://192.168.86.150:3000/mcp`
   - **Description**: `Healthcare AI tools for clinical workflows`

3. **Test Connection**: `curl http://192.168.86.150:3000/health`

### Step 5: Visual Container Management

Docker Desktop will now show:
- ✅ All your existing containers (healthcare-mcp, ollama, postgres, etc.)
- ✅ Container logs in GUI
- ✅ Easy start/stop/restart buttons
- ✅ Resource usage monitoring
- ✅ MCP tool testing interface

Your existing `./scripts/universal-service-runner.sh` commands will still work exactly the same!

Dad's Computer → VPN → Your Network → Your Docker Container
     ↓              ↓         ↓              ↓
Docker Desktop → WireGuard → 192.168.86.150 → healthcare-mcp:3000