#!/usr/bin/env node
dotenv.config();

import dotenv from "dotenv";
import { HealthcareServer } from "./server/HealthcareServer.js";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { AuthConfig } from "./server/utils/AuthConfig.js";
import express from "express";

dotenv.config();

const authConfig: AuthConfig = {
    clientId: process.env.OAUTH_CLIENT_ID!,
    clientSecret: process.env.OAUTH_CLIENT_SECRET!,
    tokenHost: process.env.OAUTH_TOKEN_HOST!,
    tokenPath: process.env.OAUTH_TOKEN_PATH!,
    authorizePath: process.env.OAUTH_AUTHORIZE_PATH!,
    authorizationMethod: (process.env.OAUTH_AUTHORIZATION_METHOD as "body" | "header") || "body",
    audience: process.env.OAUTH_AUDIENCE!,
    callbackURL: process.env.OAUTH_CALLBACK_URL!,
    scopes: process.env.OAUTH_SCOPES!,
    callbackPort: parseInt(process.env.OAUTH_CALLBACK_PORT!)
};

const FHIR_BASE_URL = process.env.FHIR_BASE_URL!;
const PUBMED_API_KEY = process.env.PUBMED_API_KEY!;
const TRIALS_API_KEY = process.env.TRIALS_API_KEY!;
const FDA_API_KEY = process.env.FDA_API_KEY!;

if (!FHIR_BASE_URL) {
    throw new Error("FHIR_BASE_URL is missing");
}

if (!PUBMED_API_KEY) {
    throw new Error("PUBMED_API_KEY is missing");
}

if (!TRIALS_API_KEY) {
    throw new Error("TRIALS_API_KEY is missing");
}

if (!FDA_API_KEY) {
    throw new Error("FDA_API_KEY is missing");
}

let mcpServer = new Server({
    name: "healthcare-mcp",
    version: "1.0.0"
}, {
    capabilities: {
        resources: {},
        tools: {},
        prompts: {},
        logging: {}
    }
});

const healthcareServer = new HealthcareServer(mcpServer, authConfig, FHIR_BASE_URL, PUBMED_API_KEY, TRIALS_API_KEY, FDA_API_KEY);

const app = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

app.use(express.json());

app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'healthcare-mcp', timestamp: new Date().toISOString() });
});

// Define handlers outside the MCP Server
const toolsListHandler = async (req: { method: string; params?: any }) => ({
    tools: [
        {
            name: 'health_check',
            description: 'Check healthcare MCP server health',
            inputSchema: { type: 'object', properties: {}, required: [] }
        }
    ]
});
const toolsCallHandler = async (req: { method: string; params?: any }) => ({
    content: [{ type: 'text', text: 'Healthcare MCP Server is healthy and running' }]
});
// Prompts and resources stubs
const promptsListHandler = async (req: { method: string; params?: any }) => ({
    prompts: [
        {
            name: 'example_prompt',
            description: 'Mock prompt for development/testing',
            inputSchema: { type: 'object', properties: {}, required: [] }
        }
    ]
});
const promptsGetHandler = async (req: { method: string; params?: any }) => ({
    prompt: {
        name: 'example_prompt',
        description: 'Mock prompt for development/testing',
        inputSchema: { type: 'object', properties: {}, required: [] }
    }
});
const resourcesListHandler = async (req: { method: string; params?: any }) => ({ resources: [] });
const resourcesReadHandler = async (req: { method: string; params?: any }) => ({ resource: null });
// Add similar stubs for prompts/resources as needed

app.post('/mcp', async (req, res) => {
    try {
        const { jsonrpc, method, params, id } = req.body;
        console.log(`MCP Request: ${method}`, params ? JSON.stringify(params, null, 2) : 'no params');
        if (jsonrpc !== '2.0') {
            return res.status(400).json({
                jsonrpc: '2.0',
                error: { code: -32600, message: 'Invalid Request' },
                id: id || null
            });
        }
        const mockRequest = {
            method,
            params: params || {}
        };
        let result;
        switch (method) {
            case 'initialize':
                result = {
                    protocolVersion: '2024-11-05',
                    capabilities: {
                        tools: {},
                        resources: {},
                        prompts: {},
                        logging: {}
                    },
                    serverInfo: {
                        name: 'intelluxe-healthcare-mcp-server',
                        version: '1.0.0'
                    }
                };
                break;
            case 'notifications/initialized':
                result = {};
                break;
            case 'ping':
                result = {};
                break;
            case 'tools/list':
                result = await toolsListHandler({ method, params });
                break;
            case 'tools/call':
                result = await toolsCallHandler({ method, params });
                break;
            case 'prompts/list':
                result = await promptsListHandler({ method, params });
                break;
            case 'prompts/get':
                result = await promptsGetHandler({ method, params });
                break;
            case 'resources/list':
                result = await resourcesListHandler({ method, params });
                break;
            case 'resources/read':
                result = await resourcesReadHandler({ method, params });
                break;
            default:
                console.log(`Unknown MCP method: ${method}`);
                return res.status(400).json({
                    jsonrpc: '2.0',
                    error: { code: -32601, message: `Method not found: ${method}` },
                    id
                });
        }
        res.json({
            jsonrpc: '2.0',
            result,
            id
        });
    } catch (error) {
        console.error('MCP endpoint error:', error);
        res.status(500).json({
            jsonrpc: '2.0',
            error: {
                code: -32603,
                message: 'Internal error',
                data: error instanceof Error ? error.message : 'Unknown error'
            },
            id: req.body?.id || null
        });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Healthcare MCP Server running on port ${PORT}`);
    console.log(`Health check available at http://localhost:${PORT}/health`);
    console.log(`MCP endpoint available at http://localhost:${PORT}/mcp`);
});

if (process.env.MCP_TRANSPORT === 'stdio') {
    healthcareServer.run().catch(console.error);
}