#!/usr/bin/env node
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
    name: "intelluxe-healthcare-mcp-server",
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

// Create Express app for HTTP server mode
const app = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'healthcare-mcp', timestamp: new Date().toISOString() });
});

// MCP endpoint (placeholder for future HTTP MCP implementation)
app.post('/mcp', (req, res) => {
    res.json({ message: 'MCP endpoint - implementation pending' });
});

// Start HTTP server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Healthcare MCP Server running on port ${PORT}`);
    console.log(`Health check available at http://localhost:${PORT}/health`);
});

// Keep the stdio version for development/testing
if (process.env.MCP_TRANSPORT === 'stdio') {
    healthcareServer.run().catch(console.error);
}