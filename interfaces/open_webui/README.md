# Open WebUI Integration

This directory contains components for integrating Healthcare AI with Open WebUI through the Pipelines framework.

## Files

- `MCP_pipeline.py` - Open WebUI Pipeline for MCP server integration
- `mcp_config.json` - Configuration for Healthcare MCP server connections

## Architecture

```
Open WebUI (Port 1000) → Open WebUI Pipelines (Port 9099) → Healthcare MCP Server (stdio)
                                    ↓
                            MCP_pipeline.py
                         (handles MCP protocol)
```

## Setup Instructions

1. **Set up Open WebUI Pipelines:**
   ```bash
   git clone https://github.com/open-webui/pipelines.git
   cd pipelines
   python -m venv env
   source env/bin/activate
   pip install -r requirements-minimum.txt
   pip install mcp
   ```

2. **Copy Pipeline files:**
   ```bash
   cp /home/intelluxe/interfaces/open_webui/MCP_pipeline.py pipelines/
   cp /home/intelluxe/interfaces/open_webui/mcp_config.json pipelines/data/
   ```

3. **Start Pipelines server:**
   ```bash
   cd pipelines
   ./start.sh
   ```

4. **Configure Open WebUI:**
   - Go to Settings → Connections
   - Add Pipelines URL: http://localhost:9099
   - Select "MCP Pipeline" as model

## Testing

Run the integration tests:
```bash
cd /home/intelluxe
python tests/test_open_webui_mcp.py
```

## Healthcare Tools Available

- **search-pubmed** - Search medical literature
- **search-trials** - Find clinical trials 
- **get-drug-info** - Get FDA drug information
- Plus 12 additional healthcare tools

## Notes

- This replaces the auth proxy approach with the official Open WebUI Pipelines method
- All PHI/PII remains on-premise through the Healthcare MCP server
- Medical disclaimers and safety boundaries are enforced
