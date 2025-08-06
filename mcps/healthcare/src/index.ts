#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { HealthcareServer } from "./server/HealthcareServer.js";
import { AuthConfig } from "./server/utils/AuthConfig.js";
import { agentTools, callAgent, validateNoPHI } from "./tools/agent_bridge.js";

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

const healthcareServer = new HealthcareServer(
    mcpServer,
    authConfig,
    FHIR_BASE_URL,
    PUBMED_API_KEY,
    TRIALS_API_KEY,
    FDA_API_KEY,
    process.env.OLLAMA_API_URL || "http://host.docker.internal:11434",
    process.env.OLLAMA_MODEL || "llama-3"
);

// Create Express app for HTTP server mode
const app = express();
const PORT = parseInt(process.env.PORT || '3000', 10);

// CORS configuration for Open WebUI
app.use(cors({
    origin: [
        'http://localhost:1000',           // Open WebUI external
        'http://172.20.0.11:8080',        // Open WebUI container internal  
        'http://172.20.0.11:1000',        // Open WebUI container external
        'http://127.0.0.1:1000',          // Open WebUI local
        'http://host.docker.internal:1000' // Docker host access
    ],
    credentials: true,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'Accept']
}));

app.use(express.json());

// OpenAPI specification endpoint
app.get('/openapi.json', (req, res) => {
    try {
        const __filename = fileURLToPath(import.meta.url);
        const __dirname = path.dirname(__filename);
        const openApiPath = path.join(__dirname, 'openapi.json');
        const openApiSpec = JSON.parse(fs.readFileSync(openApiPath, 'utf8'));
        res.json(openApiSpec);
    } catch (error) {
        console.error('Error loading OpenAPI spec:', error);
        res.status(500).json({ error: 'Failed to load OpenAPI specification' });
    }
});

// REST API endpoints for Open WebUI integration
app.post('/tools/search-pubmed', async (req, res) => {
    try {
        const { query, maxResults = 10 } = req.body;
        if (!query) {
            return res.status(400).json({ error: 'Query parameter is required' });
        }

        // Call PubMed API directly
        const result = await healthcareServer.pubmedApiClient.getArticles(
            { query, maxResults },
            healthcareServer.cacheManager
        );

        if (result?.content?.[0]?.text) {
            const articles = JSON.parse(result.content[0].text);
            res.json({ articles });
        } else {
            res.json({ articles: [] });
        }
    } catch (error) {
        console.error('PubMed search error:', error);
        res.status(500).json({
            error: 'Failed to search PubMed',
            message: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});

app.post('/tools/search-trials', async (req, res) => {
    try {
        const { condition, location } = req.body;
        if (!condition) {
            return res.status(400).json({ error: 'Condition parameter is required' });
        }

        // Call Clinical Trials API directly
        const result = await healthcareServer.trialsApiClient.getTrials(
            { condition, location },
            healthcareServer.cacheManager
        );

        if (result?.content?.[0]?.text) {
            const trials = JSON.parse(result.content[0].text);
            res.json({ trials });
        } else {
            res.json({ trials: [] });
        }
    } catch (error) {
        console.error('Clinical trials search error:', error);
        res.status(500).json({
            error: 'Failed to search clinical trials',
            message: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});

app.post('/tools/get-drug-info', async (req, res) => {
    try {
        const { genericName } = req.body;
        if (!genericName) {
            return res.status(400).json({ error: 'genericName parameter is required' });
        }

        // Call FDA API directly
        const result = await healthcareServer.fdaApiClient.getDrug(
            { genericName },
            healthcareServer.cacheManager
        );

        if (result?.content?.[0]?.text) {
            const drugInfo = JSON.parse(result.content[0].text);
            res.json(drugInfo);
        } else {
            res.json({ error: 'Drug information not found' });
        }
    } catch (error) {
        console.error('Drug info error:', error);
        res.status(500).json({
            error: 'Failed to get drug information',
            message: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'healthcare-mcp', timestamp: new Date().toISOString() });
});

// OpenAI-compatible endpoints for Open WebUI
app.get('/v1/models', (req, res) => {
    res.json({
        object: "list",
        data: [
            {
                id: "healthcare-assistant",
                object: "model",
                created: Math.floor(Date.now() / 1000),
                owned_by: "intelluxe-healthcare",
                permission: [],
                root: "healthcare-assistant",
                parent: null
            }
        ]
    });
});

app.post('/v1/chat/completions', async (req, res) => {
    try {
        const { messages, model = "healthcare-assistant", stream = false } = req.body;

        if (!messages || !Array.isArray(messages)) {
            return res.status(400).json({ error: { message: "Messages array is required" } });
        }

        // Get the last user message
        const lastMessage = messages[messages.length - 1];
        if (!lastMessage || lastMessage.role !== 'user') {
            return res.status(400).json({ error: { message: "Last message must be from user" } });
        }

        const query = lastMessage.content;

        // Determine which healthcare tool to use based on the query
        let response = '';
        try {
            if (query.toLowerCase().includes('pubmed') || query.toLowerCase().includes('research') || query.toLowerCase().includes('study')) {
                // Search PubMed
                const result = await healthcareServer.pubmedApiClient.getArticles(
                    { query: query, maxResults: 5 },
                    healthcareServer.cacheManager
                );

                if (result?.content?.[0]?.text) {
                    const articles = JSON.parse(result.content[0].text);
                    response = `Found ${articles.length} PubMed articles:\n\n` +
                        articles.map((article: any, i: number) =>
                            `${i + 1}. **${article.title}**\n   Authors: ${article.authors}\n   PMID: ${article.pmid}\n   Summary: ${article.abstract?.substring(0, 200)}...\n`
                        ).join('\n');
                } else {
                    response = "No PubMed articles found for your query.";
                }
            } else if (query.toLowerCase().includes('clinical trial') || query.toLowerCase().includes('trial')) {
                // Search Clinical Trials
                const condition = query.replace(/clinical trial|trial/gi, '').trim();
                const result = await healthcareServer.trialsApiClient.getTrials(
                    { condition: condition },
                    healthcareServer.cacheManager
                );

                if (result?.content?.[0]?.text) {
                    const trials = JSON.parse(result.content[0].text);
                    response = `Found ${trials.length} clinical trials:\n\n` +
                        trials.map((trial: any, i: number) =>
                            `${i + 1}. **${trial.title}**\n   Phase: ${trial.phase || 'N/A'}\n   Status: ${trial.status}\n   Location: ${trial.location || 'Multiple'}\n   ID: ${trial.nctId}\n`
                        ).join('\n');
                } else {
                    response = "No clinical trials found for your query.";
                }
            } else if (query.toLowerCase().includes('drug') || query.toLowerCase().includes('medication')) {
                // Search FDA drug info
                const drugName = query.replace(/drug|medication|info|information/gi, '').trim();
                const result = await healthcareServer.fdaApiClient.getDrug(
                    { genericName: drugName },
                    healthcareServer.cacheManager
                );

                if (result?.content?.[0]?.text) {
                    const drugInfo = JSON.parse(result.content[0].text);
                    response = `**Drug Information for ${drugName}:**\n\n` +
                        `Brand Name: ${drugInfo.brandName || 'N/A'}\n` +
                        `Generic Name: ${drugInfo.genericName || drugName}\n` +
                        `Route: ${drugInfo.route || 'N/A'}\n` +
                        `Strength: ${drugInfo.strength || 'N/A'}\n` +
                        `Manufacturer: ${drugInfo.manufacturer || 'N/A'}\n` +
                        `Purpose: ${drugInfo.purpose || 'N/A'}`;
                } else {
                    response = `No FDA drug information found for "${drugName}".`;
                }
            } else {
                // General healthcare assistant response
                response = `I'm a healthcare research assistant. I can help you with:

• **PubMed Research**: Search medical literature by including "research" or "pubmed" in your query
• **Clinical Trials**: Find clinical trials by including "clinical trial" in your query  
• **Drug Information**: Get FDA drug info by including "drug" or "medication" in your query

Please specify what type of healthcare information you're looking for, and I'll search the appropriate medical databases for you.

**Medical Disclaimer**: This tool provides administrative support only and does not provide medical advice, diagnosis, or treatment recommendations. Always consult with qualified healthcare professionals for medical decisions.`;
            }
        } catch (error) {
            console.error('Healthcare tool error:', error);
            response = "I encountered an error while searching the medical databases. Please try rephrasing your query or contact support if the issue persists.";
        }

        // Return OpenAI-compatible response
        const completion = {
            id: `chatcmpl-${Date.now()}`,
            object: "chat.completion",
            created: Math.floor(Date.now() / 1000),
            model: model,
            choices: [{
                index: 0,
                message: {
                    role: "assistant",
                    content: response
                },
                finish_reason: "stop"
            }],
            usage: {
                prompt_tokens: messages.reduce((acc: number, msg: any) => acc + (msg.content?.length || 0), 0),
                completion_tokens: response.length,
                total_tokens: messages.reduce((acc: number, msg: any) => acc + (msg.content?.length || 0), 0) + response.length
            }
        };

        if (stream) {
            // Simple streaming response
            res.setHeader('Content-Type', 'text/plain');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');

            res.write(`data: ${JSON.stringify(completion)}\n\n`);
            res.write('data: [DONE]\n\n');
            res.end();
        } else {
            res.json(completion);
        }
    } catch (error) {
        console.error('Chat completion error:', error);
        res.status(500).json({
            error: {
                message: "Failed to generate completion",
                type: "internal_error"
            }
        });
    }
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
                // Use the HealthcareServer to get the actual tools and add agent bridge tools
                const tools = healthcareServer.getTools();
                const allTools = [...tools, ...agentTools];
                res.json({
                    jsonrpc: '2.0',
                    result: {
                        tools: allTools
                    },
                    id
                });
                break;

            case 'tools/call':
                // Route tool calls to the HealthcareServer or Agent Bridge
                if (params?.name) {
                    try {
                        let result;

                        // Check if it's an agent bridge tool
                        const isAgentTool = agentTools.some(tool => tool.name === params.name);

                        if (isAgentTool) {
                            // Validate no PHI in arguments for agent calls
                            try {
                                validateNoPHI(params.arguments);
                            } catch (phiError) {
                                res.status(400).json({
                                    jsonrpc: '2.0',
                                    error: {
                                        code: -32602,
                                        message: `PHI validation failed: ${phiError instanceof Error ? phiError.message : 'PHI detected'}`
                                    },
                                    id
                                });
                                return;
                            }

                            // Call agent through bridge
                            result = await callAgent(params.name, params.arguments || {});
                        } else {
                            // Handle existing healthcare server tools
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

            case 'generate_documentation':
                // Administrative documentation generation (Ollama LLM)
                try {
                    const result = await healthcareServer.generateDocumentation(params.prompt, params.model);
                    res.json({
                        jsonrpc: '2.0',
                        result: { text: result },
                        id
                    });
                } catch (error) {
                    res.status(500).json({
                        jsonrpc: '2.0',
                        error: {
                            code: -32603,
                            message: `Ollama documentation generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`
                        },
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

// Administrative documentation generation (Ollama LLM)
app.post("/generate_documentation", async (req, res) => {
    try {
        const { prompt, model } = req.body;
        if (!prompt || typeof prompt !== "string") {
            return res.status(400).json({ error: "Missing or invalid prompt" });
        }
        const doc = await healthcareServer.generateDocumentation(prompt, model);
        res.json({ documentation: doc });
    } catch (err) {
        // Generic error message for security compliance
        res.status(500).json({ error: "Failed to generate documentation" });
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