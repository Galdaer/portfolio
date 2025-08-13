#!/usr/bin/env node
// Minimal STDIO-only entry point to isolate MCP handshake (no HTTP, no extra logging)
// IMPORTANT: Do NOT import any modules before diverting stdout. Use dynamic imports inside main().

async function main(): Promise<void> {
    // Enforce stdio-only transport early
    const transportMode = process.env.MCP_TRANSPORT;
    if (transportMode !== 'stdio' && transportMode !== 'stdio-only') {
        process.env.MCP_TRANSPORT = 'stdio-only';
    }

    // Divert all console noise away from stdout before any other imports execute
    const divert = (label: string) => (...args: any[]) => (console as any).error(`[LOG:${label}]`, ...args);
    console.log = divert('OUT');
    console.info = divert('INFO');
    console.warn = divert('WARN');

    // Extra guard: if any non-JSON sneaks to stdout, push it to stderr instead
    const origWrite = process.stdout.write.bind(process.stdout) as (chunk: any, encoding?: any, cb?: any) => boolean;
    process.stdout.write = ((chunk: any, encoding?: any, cb?: any) => {
        try {
            const s = Buffer.isBuffer(chunk) ? chunk.toString('utf8') : String(chunk);
            // Allow JSON-RPC frames and whitespace; redirect everything else
            const looksJson = /^[\s\u0000-\u001F]*[{\[]/.test(s);
            if (!looksJson) {
                return process.stderr.write(chunk as any, encoding as any, cb as any);
            }
        } catch {
            // On parsing errors, be safe and redirect to stderr
            return process.stderr.write(chunk as any, encoding as any, cb as any);
        }
        return origWrite(chunk, encoding, cb);
    }) as any;

    // Now it's safe to import runtime modules that might log at import-time
    const [{ Server }, { StdioServerTransport }, { CallToolRequestSchema, ListToolsRequestSchema }, { TOOL_DEFINITIONS }] = await Promise.all([
        import('@modelcontextprotocol/sdk/server/index.js'),
        import('@modelcontextprotocol/sdk/server/stdio.js'),
        import('@modelcontextprotocol/sdk/types.js'),
        import('./server/constants/tools.js'),
    ]);

    const server = new Server({ name: 'healthcare-mcp', version: '1.0.0' }, {
        capabilities: { tools: { listChanged: true }, resources: {}, prompts: {}, logging: {} },
    });

    server.setRequestHandler(ListToolsRequestSchema, async () => {
        console.error(`[stdio-entry][tools/list] Responding with ${TOOL_DEFINITIONS.length} tools`);
        return { tools: TOOL_DEFINITIONS };
    });

    server.setRequestHandler(CallToolRequestSchema, async (req: any) => {
        const name = req.params?.name;
        if (name === 'echo_test') {
            return {
                content: [
                    { type: 'text', text: JSON.stringify({ echoed: req.params?.arguments?.text || null, ts: new Date().toISOString() }) },
                ],
            };
        }
        return { content: [{ type: 'text', text: `Tool ${name} invoked (stubbed)` }] };
    });

    await server.connect(new StdioServerTransport());
    console.error(`[stdio-entry][startup] STDIO server ready with ${TOOL_DEFINITIONS.length} tools.`);
    process.stdin.resume();
}

main().catch((e: unknown) => {
    console.error('[stdio-entry][error]', e);
    process.exit(1);
});
