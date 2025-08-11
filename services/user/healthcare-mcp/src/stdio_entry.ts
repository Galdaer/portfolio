#!/usr/bin/env node
// Minimal STDIO-only entry point to isolate MCP handshake (no HTTP, no extra logging)
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { TOOL_DEFINITIONS } from './server/constants/tools.js';

async function main() {
    const transportMode = process.env.MCP_TRANSPORT;
    if (transportMode !== 'stdio' && transportMode !== 'stdio-only') {
        process.env.MCP_TRANSPORT = 'stdio-only';
    }
    const divert = (label: string) => (...args: any[]) => (console as any).error(`[LOG:${label}]`, ...args);
    console.log = divert('OUT');
    console.info = divert('INFO');
    console.warn = divert('WARN');

    const server = new Server({ name: 'healthcare-mcp', version: '1.0.0' }, {
        capabilities: { tools: { listChanged: true }, resources: {}, prompts: {}, logging: {} }
    });

    server.setRequestHandler(ListToolsRequestSchema, async () => {
        console.error(`[stdio-entry][tools/list] Responding with ${TOOL_DEFINITIONS.length} tools`);
        return { tools: TOOL_DEFINITIONS };
    });
    server.setRequestHandler(CallToolRequestSchema, async (req: any) => {
        const name = req.params?.name;
        if (name === 'echo_test') {
            return { content: [{ type: 'text', text: JSON.stringify({ echoed: req.params?.arguments?.text || null, ts: new Date().toISOString() }) }] };
        }
        return { content: [{ type: 'text', text: `Tool ${name} invoked (stubbed)` }] };
    });

    await server.connect(new StdioServerTransport());
    console.error(`[stdio-entry][startup] STDIO server ready with ${TOOL_DEFINITIONS.length} tools.`);
    process.stdin.resume();
}

main().catch(e => {
    console.error('[stdio-entry][error]', e);
    process.exit(1);
});
