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

// PubMed, Trials, and FDA API keys are optional for normal usage
if (!PUBMED_API_KEY) {
    console.warn("PUBMED_API_KEY is not set. Using public rate limits.");
}
if (!TRIALS_API_KEY) {
    console.warn("TRIALS_API_KEY is not set. Using public rate limits.");
}
if (!FDA_API_KEY) {
    console.warn("FDA_API_KEY is not set. Using public rate limits.");
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

// Create Express app for HTTP server mode
const app = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'healthcare-mcp', timestamp: new Date().toISOString() });
});

// MCP JSON-RPC endpoint
app.post('/mcp', async (req, res) => {
    try {
        const { jsonrpc, method, params, id } = req.body;

        // Debug logging
        console.log(`MCP Request: ${method}`, params ? JSON.stringify(params, null, 2) : 'no params');

        // Basic JSON-RPC validation
        if (jsonrpc !== '2.0') {
            return res.status(400).json({
                jsonrpc: '2.0',
                error: { code: -32600, message: 'Invalid Request' },
                id: id || null
            });
        }

        // Handle MCP methods
        switch (method) {
            case 'initialize':
                res.json({
                    jsonrpc: '2.0',
                    result: {
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
                    },
                    id
                });
                break;

            case 'notifications/initialized':
                // Acknowledge initialization
                res.json({
                    jsonrpc: '2.0',
                    result: {},
                    id
                });
                break;

            case 'ping':
                res.json({
                    jsonrpc: '2.0',
                    result: {},
                    id
                });
                break;

            case 'tools/list':
                // Use the HealthcareServer to get the actual tools
                const tools = healthcareServer.getTools();
                res.json({
                    jsonrpc: '2.0',
                    result: {
                        tools: tools
                    },
                    id
                });
                break;

            case 'tools/call':
                // Route tool calls to the HealthcareServer
                if (params?.name) {
                    try {
                        let result;
                        switch (params.name) {
                            case 'get_trial_details':
                                result = await healthcareServer.getTrialDetails(params.arguments?.trialId);
                                break;
                            case 'match_patient_to_trials':
                                result = await healthcareServer.matchPatientToTrials(params.arguments?.patientId);
                                break;
                            case 'find_trial_locations':
                                result = await healthcareServer.findTrialLocations(params.arguments?.condition, params.arguments?.zipCode);
                                break;
                            case 'get_enrollment_status':
                                result = await healthcareServer.getEnrollmentStatus(params.arguments?.trialId);
                                break;
                            case 'search_patients':
                                result = await healthcareServer.searchPatients(params.arguments?.name, params.arguments?.dob, params.arguments?.insurance);
                                break;
                            case 'get_patient_encounter_summary':
                                result = await healthcareServer.getPatientEncounterSummary(params.arguments?.patientId, params.arguments?.limit);
                                break;
                            case 'get_recent_lab_results':
                                result = await healthcareServer.getRecentLabResults(params.arguments?.patientId, params.arguments?.abnormalOnly);
                                break;
                            case 'verify_patient_insurance':
                                result = await healthcareServer.verifyPatientInsurance(params.arguments?.patientId);
                                break;
                            default:
                                // Fallback to legacy tool handler
                                result = await healthcareServer.callTool(params.name, params.arguments || {});
                        }
                        res.json({
                            jsonrpc: '2.0',
                            result: result,
                            id
                        });
                    } catch (error) {
                        console.error(`Tool call error for ${params.name}:`, error);
                        res.status(500).json({
                            jsonrpc: '2.0',
                            error: {
                                code: -32603,
                                message: `Tool execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`
                            },
                            id
                        });
                    }
                } else {
                    res.status(400).json({
                        jsonrpc: '2.0',
                        error: { code: -32602, message: 'Invalid params: tool name required' },
                        id
                    });
                }
                break;

            default:
                console.log(`Unknown MCP method: ${method}`);
                res.status(400).json({
                    jsonrpc: '2.0',
                    error: { code: -32601, message: `Method not found: ${method}` },
                    id
                });
        }
    } catch (error) {
        console.error('MCP endpoint error:', error);
        res.status(500).json({
            jsonrpc: '2.0',
            error: { code: -32603, message: 'Internal error' },
            id: req.body?.id || null
        });
    }
});

// Start HTTP server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Healthcare MCP Server running on port ${PORT}`);
    console.log(`Health check available at http://localhost:${PORT}/health`);
    console.log(`Available tools: ${healthcareServer.getTools().map((t: any) => t.name).join(', ')}`);
});

// Keep the stdio version for development/testing
if (process.env.MCP_TRANSPORT === 'stdio') {
    healthcareServer.run().catch(console.error);
}