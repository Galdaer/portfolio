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

    // IMPORTANT: Do not override process.stdout.write. The MCP SDK owns stdout for JSON-RPC framing.
    // We only divert console.* to stderr and leave stdout pristine.


    // Minimal stderr-only diagnostics to debug stdio handshake without touching stdout
    process.on('uncaughtException', (err) => {
        console.error('[stdio-entry][uncaughtException]', err);
    });
    process.on('unhandledRejection', (reason) => {
        console.error('[stdio-entry][unhandledRejection]', reason);
    });

    // Now it's safe to import runtime modules that might log at import-time
    const [{ Server }, { StdioServerTransport }, { CallToolRequestSchema, ListToolsRequestSchema }, { TOOL_DEFINITIONS }] = await Promise.all([
        import('@modelcontextprotocol/sdk/server/index.js'),
        import('@modelcontextprotocol/sdk/server/stdio.js'),
        import('@modelcontextprotocol/sdk/types.js'),
        import('./server/constants/tools.js'),
    ]);

    // Import medical connectors for orchestrator tool
    const [{ PubMed }, { ClinicalTrials }, { FDA }, { CacheManager }] = await Promise.all([
        import('./server/connectors/medical/PubMed.js'),
        import('./server/connectors/medical/ClinicalTrials.js'),
        import('./server/connectors/medical/FDA.js'),
        import('./server/utils/Cache.js'),
    ]);

    // Initialize cache and medical connectors
    const cache = new CacheManager();
    const pubmed = new PubMed(process.env.PUBMED_API_KEY);
    const clinicalTrials = new ClinicalTrials(process.env.CLINICALTRIALS_API_KEY);
    const fda = new FDA(process.env.FDA_API_KEY);

    const server = new Server({ name: 'healthcare-mcp', version: '1.0.0' }, {
        capabilities: { tools: { listChanged: true }, resources: {}, prompts: {}, logging: {} },
    });

    server.setRequestHandler(ListToolsRequestSchema, async () => {
        console.error(`[stdio-entry][tools/list] Responding with ${TOOL_DEFINITIONS.length} tools`);
        return { tools: TOOL_DEFINITIONS };
    });

    server.setRequestHandler(CallToolRequestSchema, async (req: any) => {
        const name = req.params?.name;
        const args = req.params?.arguments || {};

        console.error(`[stdio-entry][tool-call] Tool: ${name}, Args: ${JSON.stringify(args)}`);

        try {
            if (name === 'echo_test') {
                return {
                    content: [
                        { type: 'text', text: JSON.stringify({ echoed: args.text || null, ts: new Date().toISOString() }) },
                    ],
                };
            }

            // Handle individual tool calls  
            if (name === 'search-pubmed') {
                return await pubmed.getArticles(args, cache);
            }

            if (name === 'search-trials') {
                return await clinicalTrials.getTrials(args, cache);
            }

            if (name === 'get-drug-info') {
                return await fda.getDrug(args, cache);
            }

            // Unknown tool
            console.error(`[stdio-entry][tool-call] Unknown tool: ${name}`);
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        error: `Tool ${name} not implemented`,
                        available_tools: TOOL_DEFINITIONS.map(t => t.name)
                    })
                }]
            };

        } catch (error) {
            console.error(`[stdio-entry][tool-call] Error in tool ${name}: ${error}`);
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        error: `Tool execution failed: ${error}`,
                        tool: name,
                        timestamp: new Date().toISOString()
                    })
                }]
            };
        }
    });

    console.error(`[stdio-entry][startup] STDIO server starting with ${TOOL_DEFINITIONS.length} tools...`);
    // Block here until the stdio connection ends (correct MCP lifecycle)
    try {
        await server.connect(new StdioServerTransport());
    } finally {
        console.error('[stdio-entry][shutdown] stdio connection closed');
    }
}

main().catch((e: unknown) => {
    console.error('[stdio-entry][error]', e);
    process.exit(1);
});
