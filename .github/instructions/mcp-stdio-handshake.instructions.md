# MCP STDIO Handshake Guidance and Troubleshooting

Purpose: Ensure JSON-only STDIO for Model Context Protocol (MCP) servers and provide a repeatable pattern to diagnose and fix handshake timeouts or stream contamination.

## Golden Rules
- JSON-RPC only on stdout. Send all human-readable logs to stderr.
- Divert console.log/info/warn to stderr before importing anything that might log.
- Avoid top-level stdout writes in entrypoints and imported modules.
- Prefer dynamic imports after stdout diversion (prevents import-time logs).
- If third-party code writes to stdout, guard process.stdout.write to redirect non-JSON to stderr.

## Minimal STDIO Entry Pattern (TypeScript)
Note: This is a pattern, not a drop-in; adapt to your entry.

```ts
#!/usr/bin/env node
// Minimal STDIO-only entry (pattern)
async function main() {
  if (process.env.MCP_TRANSPORT !== 'stdio' && process.env.MCP_TRANSPORT !== 'stdio-only') {
    process.env.MCP_TRANSPORT = 'stdio-only';
  }

  const divert = (label: string) => (...args: any[]) => console.error(`[LOG:${label}]`, ...args);
  console.log = divert('OUT');
  console.info = divert('INFO');
  console.warn = divert('WARN');

  const origWrite = process.stdout.write.bind(process.stdout) as any;
  process.stdout.write = ((chunk: any, enc?: any, cb?: any) => {
    try {
      const s = Buffer.isBuffer(chunk) ? chunk.toString('utf8') : String(chunk);
      const looksJson = /^[\s\u0000-\u001F]*[\[{]/.test(s);
      if (!looksJson) return (process.stderr.write as any)(chunk, enc, cb);
    } catch {
      return (process.stderr.write as any)(chunk, enc, cb);
    }
    return origWrite(chunk, enc, cb);
  }) as any;

  const [{ Server }, { StdioServerTransport }, { CallToolRequestSchema, ListToolsRequestSchema }, tools] = await Promise.all([
    import('@modelcontextprotocol/sdk/server/index.js'),
    import('@modelcontextprotocol/sdk/server/stdio.js'),
    import('@modelcontextprotocol/sdk/types.js'),
    import('./server/constants/tools.js'),
  ]);

  const { TOOL_DEFINITIONS } = tools as any;
  const server = new Server({ name: 'your-mcp', version: '1.0.0' }, { capabilities: { tools: { listChanged: true } } });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOL_DEFINITIONS }));
  server.setRequestHandler(CallToolRequestSchema, async (req: any) => ({ content: [{ type: 'text', text: `Tool ${req.params?.name}` }] }));
  await server.connect(new StdioServerTransport());
  console.error(`[stdio-entry][startup] ready:${TOOL_DEFINITIONS.length}`);
}
main().catch((e: unknown) => { console.error('[stdio-entry][error]', e); process.exit(1); });
```

## Docker/Runtime Checklist
- Verify the container ENTRYPOINT/CMD invokes the intended stdio entry (compiled JS path).
- Ensure the stdio entry exists in the final image and is executable.
- Confirm no alternate entrypoint (like an HTTP server) is launched for stdio runs.
- Rebuild image, restart container, and re-run the probe after changes.

## Client/Probe Diagnostics
- Use `scripts/mcp_pubmed_probe.py` to detect handshake issues.
  - Timeout during `session.initialize()` usually indicates stdout contamination.
  - The probe tails container logs on failure; check for banners printed to stdout.
- Expected probe signal when fixed: non-empty tools list, no text on stdout except JSON.

## Common Failure Modes
- Startup banners printed to stdout before SDK connects.
- Library that logs to stdout on import; fix via dynamic import after diversion.
- Different entrypoint used at runtime than the one edited; fix Docker CMD/ENTRYPOINT.
- Long-running init blocking initialize() response; add small readiness logs to stderr.

## Test Pattern (Optional)
- Add a smoke test that shells into the container and runs the stdio entry directly, asserting that no non-JSON text is emitted to stdout during handshake and list_tools.

## Logging Pattern
- Prefix stderr logs with a stable tag: `[stdio-entry][...]` for easier grep.
- Keep stdout silent except for JSON-RPC frames.
