Healthcare MCP Pipeline Verification
====================================

Goal: Ensure the MCP pipeline service is running, exposes required endpoints, and is detected by Open WebUI pipelines logic.

Steps
-----
1. Build images:
   make mcp mcp-pipeline
2. Start or restart stdio MCP server (if not already):
   scripts/bootstrap.sh (select healthcare-mcp-stdio) or docker restart healthcare-mcp-stdio
3. Start pipeline as root (needs docker.sock):
   make mcp-pipeline-run  (service config sets user=0:0)
4. Verify endpoints:
   curl -s http://172.20.0.17:9099/health
   curl -s http://172.20.0.17:9099/models | jq
5. Update Open WebUI config (already added): ensure env line includes:
   OPENAI_API_BASE_URLS=http://172.20.0.17:9099
   OPENAI_API_KEYS=none (placeholder so slot count matches)
6. Restart Open WebUI:
   make setup (select ollama-webui) OR docker restart ollama-webui
7. Login to WebUI and open Pipelines admin page; pipeline should appear.
8. (Tools) Verify tool discovery endpoints:
    curl -s http://172.20.0.17:9099/tools | jq
    curl -s http://172.20.0.17:9099/tools/medical_literature_search | jq

Tools Endpoints
---------------
The pipeline now exposes placeholder tool metadata for forthcoming MCP tool execution bridging.

Endpoints:
- GET /tools -> list (object="list", data=[{id,name,description,category}])
- GET /tools/{tool_id} -> single tool object

Example Response (GET /tools):
{
   "object": "list",
   "data": [
      {"id": "medical_literature_search", "name": "Medical Literature Search", "description": "Search mirrored PubMed corpus (placeholder)", "category": "research"},
      {"id": "clinical_trial_lookup", "name": "Clinical Trial Lookup", "description": "Query mirrored ClinicalTrials.gov data (placeholder)", "category": "research"},
      {"id": "drug_information", "name": "Drug Information", "description": "Access FDA drug labeling data (placeholder)", "category": "medication"}
   ]
}

Planned Real MCP Integration
----------------------------
Next iteration will: (1) Discover actual MCP tools via stdio initialize handshake, (2) cache tool schemas, (3) add POST /tools/{tool_id}/invoke accepting JSON args, (4) stream tool outputs into chat completion responses.

Non-Root Operation Plan (Future)
--------------------------------
Replace root requirement by either: (A) mapping host docker group GID into container and adding pipeline user, or (B) running a docker-socket-proxy with fine-grained permission and connecting via TCP.

Troubleshooting
---------------
- Pipeline container exits immediately: likely missing /app/data/mcp_config.json inside mounted volume.
- Permission denied on docker.sock: ensure container runs as root (user=0:0 in .conf) or add pipeline user to docker group host-side (less preferred).
- Not detected: confirm /models returns JSON with keys: object ("list"), data (array), pipelines (array).
- 403 on /api/v1/pipelines/list: authenticate to Open WebUI first (session cookie required).

Security Notes
--------------
- Only non-PHI operational metadata is transmitted between WebUI and pipeline.
- Docker exec usage restricted to healthcare-mcp-stdio container by explicit command list in mcp_config.json.

Last updated: 2025-08-09
