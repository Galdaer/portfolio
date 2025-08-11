#!/usr/bin/env node
// EARLY STDIO TAP (inserted before any other imports that may write to stdout)
// We capture the very first chunks arriving on stdin and tee them to a file to verify
// whether an MCP client actually sends an initialize request over stdio. This occurs
// before loading the SDK so we can distinguish transport vs. server handler issues.
{
    // Wrap in an async IIFE to allow dynamic import without top-level await (compiled ESM acceptable)
    (async () => {
        try {
            const earlyTransportMode = process.env.MCP_TRANSPORT;
            if (earlyTransportMode === 'stdio' || earlyTransportMode === 'stdio-only') {
                const fsEarly = await import('fs');
                const earlyLogDir = '/app/logs';
                const earlyLogPath = `${earlyLogDir}/early_stdio_tap.log`;
                try { (fsEarly as any).mkdirSync(earlyLogDir, { recursive: true }); } catch (_) { /* ignore */ }
                let captured = 0;
                const CAP_LIMIT = 1024; // capture up to 1KB for diagnostic
                process.stdin.on('data', (chunk: Buffer) => {
                    try {
                        if (captured < CAP_LIMIT) {
                            const slice = chunk.subarray(0, Math.min(chunk.length, CAP_LIMIT - captured));
                            (fsEarly as any).appendFileSync(earlyLogPath, `IN ${new Date().toISOString()} ${slice.toString()}`);
                            captured += slice.length;
                            if (captured >= CAP_LIMIT) {
                                (fsEarly as any).appendFileSync(earlyLogPath, '\n-- CAPTURE LIMIT REACHED --\n');
                            }
                        }
                    } catch (e) { /* ignore */ }
                });
                (fsEarly as any).appendFileSync(earlyLogPath, `[early-tap] process start pid=${process.pid} mode=${earlyTransportMode}\n`);
            }
        } catch (e) {
            console.error('[early-tap][error]', e);
        }
    })();
}
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

// Enhanced Healthcare Intelligence
interface PHIDetectionResult {
    hasPHI: boolean;
    confidence: number;
    detectedTypes: string[];
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

interface RoutingDecision {
    provider: 'ollama-local' | 'openai-cloud' | 'specialized-agent' | 'healthcare-tools';
    model?: string;
    agent?: string;
    tool?: string;
    reasoning: string;
    requiresPrivacy: boolean;
}

interface ConversationContext {
    sessionId: string;
    hasDetectedPHI: boolean;
    userRole?: string;
    conversationTopic?: string;
    riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config();

// ---------------------------------------------------------------------------
// STDIO Transport Logging Safety
// When running in MCP stdio or stdio-only modes, ANY writes to process.stdout
// that are not well‑formed JSON-RPC frames will corrupt the protocol stream
// and cause clients (Python pipeline / Open WebUI) to see zero tools.
// We therefore redirect all console.log/info/warn output to stderr so that
// only the MCP SDK emits JSON-RPC payloads on stdout. This preserves existing
// debug visibility without breaking the framing.
// ---------------------------------------------------------------------------
const __transportMode = process.env.MCP_TRANSPORT;
if (__transportMode === 'stdio' || __transportMode === 'stdio-only') {
    const divert = (label: string) => (...args: any[]) => {
        // Use console.error's original binding to ensure stderr routing
        (console as any).error(`[LOG:${label}]`, ...args);
    };
    // Preserve original error for structured logging already using console.error
    console.log = divert('OUT');
    console.info = divert('INFO');
    console.warn = divert('WARN');
}

// Create auth config only if OAuth environment variables are provided
const authConfig: AuthConfig = {
    clientId: process.env.OAUTH_CLIENT_ID || 'not-configured',
    clientSecret: process.env.OAUTH_CLIENT_SECRET || '',
    tokenHost: process.env.OAUTH_TOKEN_HOST || 'not-configured',
    tokenPath: process.env.OAUTH_TOKEN_PATH || '/token',
    authorizePath: process.env.OAUTH_AUTHORIZE_PATH || '/authorize',
    authorizationMethod: (process.env.OAUTH_AUTHORIZATION_METHOD as "body" | "header") || "body",
    audience: process.env.OAUTH_AUDIENCE || 'not-configured',
    callbackURL: process.env.OAUTH_CALLBACK_URL || 'http://localhost:3456/oauth/callback',
    scopes: process.env.OAUTH_SCOPES || 'read',
    callbackPort: parseInt(process.env.OAUTH_CALLBACK_PORT || '3456', 10)
};

const FHIR_BASE_URL = process.env.FHIR_BASE_URL || 'http://172.20.0.13:5432';
const PUBMED_API_KEY = process.env.PUBMED_API_KEY || 'test';
const TRIALS_API_KEY = process.env.TRIALS_API_KEY || process.env.CLINICALTRIALS_API_KEY || 'test';
const FDA_API_KEY = process.env.FDA_API_KEY || 'test';

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

// Create MCP server with explicit (non-empty) tools capability so some clients
// that short‑circuit when capabilities.tools is undefined/empty still issue
// a tools/list request. We don't enumerate tools here (dynamic); just signal support.
let mcpServer = new Server({
    name: "healthcare-mcp",
    version: "1.0.0"
}, {
    capabilities: {
        resources: {},
        tools: { listChanged: true },
        prompts: {},
        logging: {}
    }
});
console.error('[MCP][init] Server instantiated with tools capability stub');

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

// NOTE: Do NOT start run() here to avoid double invocation. Actual invocation handled below
// after HTTP vs stdio-only branching. Double run() caused two StdioServerTransport instances
// and likely swallowed initialize frames from clients, resulting in zero discovered tools.

// Lightweight raw frame logging (incoming + outgoing) for stdio modes to /app/logs/stdio_frames.log
if (__transportMode === 'stdio' || __transportMode === 'stdio-only') {
    try {
        const fs = await import('fs');
        const logDir = '/app/logs';
        const logPath = `${logDir}/stdio_frames.log`;
        try { fs.mkdirSync(logDir, { recursive: true }); } catch (_) { /* ignore */ }
        const originalWrite = process.stdout.write.bind(process.stdout);
        (process.stdout as any).write = (chunk: any, encoding?: any, cb?: any) => {
            try { fs.appendFileSync(logPath, `OUT ${new Date().toISOString()} ${chunk.toString()}`); } catch (_) { /* ignore */ }
            return originalWrite(chunk, encoding, cb);
        };
        process.stdin.on('data', (chunk) => {
            try { fs.appendFileSync(logPath, `IN  ${new Date().toISOString()} ${chunk.toString()}`); } catch (_) { /* ignore */ }
        });
        console.error('[MCP][debug] Enabled raw stdio frame logging at /app/logs/stdio_frames.log');
    } catch (e) {
        console.error('[MCP][debug] Failed to enable raw stdio frame logging', e);
    }
}

// OpenAI Client Setup (if API key provided)
let openaiClient: any = null;
if (process.env.OPENAI_API_KEY) {
    try {
        // Dynamic import for OpenAI (install with: npm install openai)
        const OpenAI = await import('openai');
        openaiClient = new OpenAI.default({
            apiKey: process.env.OPENAI_API_KEY,
        });
        console.log('OpenAI client initialized for cloud model routing');
    } catch (error) {
        console.warn('OpenAI client not available. Install with: npm install openai');
    }
}

// Conversation Context Management
const conversationContexts = new Map<string, ConversationContext>();

// Enhanced PHI Detection Service
function detectPHI(text: string): PHIDetectionResult {
    let confidence = 0;
    const detectedTypes: string[] = [];
    let riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW';

    // Medical Record Numbers (MRN)
    if (/\b(MRN|mrn|medical record|patient id|patient number)[\s:]*\d+/i.test(text)) {
        confidence += 0.8;
        detectedTypes.push('medical_record_number');
        riskLevel = 'CRITICAL';
    }

    // Social Security Numbers
    if (/\b\d{3}[-]?\d{2}[-]?\d{4}\b/.test(text)) {
        confidence += 0.9;
        detectedTypes.push('ssn');
        riskLevel = 'CRITICAL';
    }

    // Dates of Birth
    if (/\b(dob|date of birth|born|birth date)[\s:]*\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}/i.test(text)) {
        confidence += 0.7;
        detectedTypes.push('date_of_birth');
        riskLevel = 'HIGH';
    }

    // Patient Names with Medical Context
    if (/\b(patient|mr\.|mrs\.|ms\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+/i.test(text)) {
        confidence += 0.6;
        detectedTypes.push('patient_name');
        riskLevel = escalateRiskLevel(riskLevel, 'MEDIUM');
    }

    // Specific Patient Case References
    if (/\b(my patient|this patient|the patient|patient case|case study).*\b(diagnosed|symptoms|treatment|medication|condition)/i.test(text)) {
        confidence += 0.7;
        detectedTypes.push('patient_case');
        riskLevel = 'HIGH';
    }

    // Medical Addresses/Locations
    if (/\b\d+\s+[A-Za-z\s]+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd).*\b(hospital|clinic|medical|health)/i.test(text)) {
        confidence += 0.5;
        detectedTypes.push('medical_address');
        riskLevel = escalateRiskLevel(riskLevel, 'MEDIUM');
    }

    // Phone Numbers with Medical Context
    if (/\b(doctor|physician|hospital|clinic).*\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4}/i.test(text)) {
        confidence += 0.4;
        detectedTypes.push('medical_phone');
        riskLevel = escalateRiskLevel(riskLevel, 'MEDIUM');
    }
    // Type-safe risk level escalation
    function escalateRiskLevel(current: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL', incoming: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' {
        const levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
        return levels[Math.max(levels.indexOf(current), levels.indexOf(incoming))];
    }

    return {
        hasPHI: confidence > 0.3,
        confidence: Math.min(confidence, 1.0),
        detectedTypes,
        riskLevel
    };
}

// Intent Classification Service
function classifyHealthcareIntent(text: string): { intent: string; confidence: number; keywords: string[] } {
    const intents = [
        {
            name: 'medical_literature_search',
            patterns: [/\b(pubmed|research|study|studies|literature|evidence|clinical trial|meta-analysis)\b/gi],
            weight: 1.0
        },
        {
            name: 'clinical_trial_search',
            patterns: [/\b(clinical trial|trials|study recruitment|nct|phase|enrollment)\b/gi],
            weight: 1.0
        },
        {
            name: 'drug_information',
            patterns: [/\b(drug|medication|pharmaceutical|dosage|side effects|interactions|fda)\b/gi],
            weight: 1.0
        },
        {
            name: 'patient_documentation',
            patterns: [/\b(document|note|report|summary|assessment|diagnosis|treatment plan)\b/gi],
            weight: 0.9
        },
        {
            name: 'clinical_decision_support',
            patterns: [/\b(diagnosis|differential|treatment|recommend|suggest|consider)\b/gi],
            weight: 0.8
        },
        {
            name: 'administrative_inquiry',
            patterns: [/\b(billing|insurance|schedule|appointment|policy|procedure)\b/gi],
            weight: 0.7
        }
    ];

    let bestMatch = { intent: 'general_medical', confidence: 0, keywords: [] as string[] };

    for (const intentDef of intents) {
        let matches = 0;
        const foundKeywords: string[] = [];

        for (const pattern of intentDef.patterns) {
            const patternMatches = text.match(pattern);
            if (patternMatches) {
                matches += patternMatches.length;
                foundKeywords.push(...patternMatches.map(m => m.toLowerCase()));
            }
        }

        if (matches > 0) {
            const confidence = Math.min((matches * intentDef.weight) / 10, 1.0);
            if (confidence > bestMatch.confidence) {
                bestMatch = {
                    intent: intentDef.name,
                    confidence,
                    keywords: [...new Set(foundKeywords)]
                };
            }
        }
    }

    return bestMatch;
}

// Intelligent Routing Decision Engine
function makeRoutingDecision(
    text: string,
    phiResult: PHIDetectionResult,
    intent: { intent: string; confidence: number },
    context: ConversationContext
): RoutingDecision {
    // RULE 1: If PHI detected or session marked as PHI, always use local/agents
    if (phiResult.hasPHI || context.hasDetectedPHI || phiResult.riskLevel === 'CRITICAL' || phiResult.riskLevel === 'HIGH') {
        context.hasDetectedPHI = true; // Mark session as PHI-containing

        // Route to appropriate local agent
        if (intent.intent === 'patient_documentation') {
            return {
                provider: 'specialized-agent',
                agent: 'document_processor',
                reasoning: 'PHI detected - routing to local document processor agent for privacy compliance',
                requiresPrivacy: true
            };
        } else if (intent.intent === 'clinical_decision_support') {
            return {
                provider: 'ollama-local',
                model: 'llama3.1:8b-medical',
                reasoning: 'PHI detected - using local Ollama model for clinical decision support',
                requiresPrivacy: true
            };
        } else {
            return {
                provider: 'specialized-agent',
                agent: 'intake',
                reasoning: 'PHI detected - routing to local intake agent for safe processing',
                requiresPrivacy: true
            };
        }
    }

    // RULE 2: Public medical research - can use cloud models for better quality
    if (intent.intent === 'medical_literature_search' && intent.confidence > 0.7) {
        return {
            provider: 'healthcare-tools',
            tool: 'pubmed_search',
            reasoning: 'Public medical literature search - using specialized healthcare tools',
            requiresPrivacy: false
        };
    }

    if (intent.intent === 'clinical_trial_search' && intent.confidence > 0.7) {
        return {
            provider: 'healthcare-tools',
            tool: 'clinical_trials_search',
            reasoning: 'Clinical trial search - using specialized healthcare tools',
            requiresPrivacy: false
        };
    }

    if (intent.intent === 'drug_information' && intent.confidence > 0.7) {
        return {
            provider: 'healthcare-tools',
            tool: 'fda_drug_search',
            reasoning: 'Drug information lookup - using FDA tools',
            requiresPrivacy: false
        };
    }

    // RULE 3: General medical questions - use cloud if available, local otherwise
    if (openaiClient && !phiResult.hasPHI && phiResult.riskLevel === 'LOW') {
        return {
            provider: 'openai-cloud',
            model: 'gpt-4',
            reasoning: 'General medical inquiry without PHI - using cloud model for comprehensive response',
            requiresPrivacy: false
        };
    }

    // RULE 4: Default to local Ollama
    return {
        provider: 'ollama-local',
        model: 'llama3.1:8b',
        reasoning: 'Default routing to local Ollama model',
        requiresPrivacy: context.hasDetectedPHI
    };
}

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

        const userMessage = lastMessage.content;

        // Generate session ID from request headers or create new one
        const sessionId = req.headers['x-session-id'] as string || `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

        // Get or create conversation context
        let context = conversationContexts.get(sessionId);
        if (!context) {
            context = {
                sessionId,
                hasDetectedPHI: false,
                riskLevel: 'LOW'
            };
            conversationContexts.set(sessionId, context);
        }

        // Enhanced PHI Detection
        const phiResult = detectPHI(userMessage);
        console.log(`PHI Detection Result: ${JSON.stringify(phiResult)}`);

        // Update context risk level
        if (phiResult.riskLevel > context.riskLevel) {
            context.riskLevel = phiResult.riskLevel;
        }

        // Intent Classification
        const intentResult = classifyHealthcareIntent(userMessage);
        console.log(`Intent Classification: ${JSON.stringify(intentResult)}`);

        // Intelligent Routing Decision
        const routingDecision = makeRoutingDecision(userMessage, phiResult, intentResult, context);
        console.log(`Routing Decision: ${JSON.stringify(routingDecision)}`);

        // Update conversation context
        conversationContexts.set(sessionId, context);

        let response = '';
        let responseSource = 'unknown';

        try {
            switch (routingDecision.provider) {
                case 'healthcare-tools':
                    response = await handleHealthcareTools(userMessage, routingDecision.tool!);
                    responseSource = `healthcare-tools:${routingDecision.tool}`;
                    break;

                case 'specialized-agent':
                    response = await handleSpecializedAgent(userMessage, routingDecision.agent!, messages);
                    responseSource = `agent:${routingDecision.agent}`;
                    break;

                case 'openai-cloud':
                    if (openaiClient) {
                        response = await handleOpenAICloud(messages, routingDecision.model!);
                        responseSource = `openai:${routingDecision.model}`;
                    } else {
                        // Fallback to local
                        response = await handleOllamaLocal(messages, 'llama3.1:8b');
                        responseSource = 'ollama:llama3.1:8b (openai-fallback)';
                    }
                    break;

                case 'ollama-local':
                default:
                    response = await handleOllamaLocal(messages, routingDecision.model || 'llama3.1:8b');
                    responseSource = `ollama:${routingDecision.model || 'llama3.1:8b'}`;
                    break;
            }

            // Add routing information to response for transparency
            const routingInfo = `\n\n---\n**Routing Info**: ${routingDecision.reasoning} (Source: ${responseSource})`;
            if (routingDecision.requiresPrivacy) {
                response += `\n\n🔒 **Privacy Mode**: This conversation contains sensitive information and is processed locally.`;
            }
            response += routingInfo;

        } catch (error) {
            console.error('Healthcare processing error:', error);
            response = "I encountered an error while processing your healthcare query. Please try rephrasing your question or contact support if the issue persists.";
            responseSource = 'error-handler';
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

// Handler Functions for Intelligent Routing
async function handleHealthcareTools(message: string, tool: string): Promise<string> {
    try {
        switch (tool) {
            case 'pubmed-search':
                const pubmedResult = await healthcareServer.pubmedApiClient.getArticles(
                    { query: message, maxResults: 5 },
                    healthcareServer.cacheManager
                );
                if (pubmedResult?.content?.[0]?.text) {
                    const articles = JSON.parse(pubmedResult.content[0].text);
                    return `Found ${articles.length} PubMed articles:\n\n` +
                        articles.map((article: any, i: number) =>
                            `${i + 1}. **${article.title}**\n   Authors: ${article.authors}\n   PMID: ${article.pmid}\n   Abstract: ${article.abstract?.substring(0, 300)}...\n`
                        ).join('\n');
                }
                return "No PubMed articles found for your query.";

            case 'clinical-trials':
                const condition = message.replace(/clinical trial|trial/gi, '').trim();
                const trialsResult = await healthcareServer.trialsApiClient.getTrials(
                    { condition: condition },
                    healthcareServer.cacheManager
                );
                if (trialsResult?.content?.[0]?.text) {
                    const trials = JSON.parse(trialsResult.content[0].text);
                    return `Found ${trials.length} clinical trials:\n\n` +
                        trials.map((trial: any, i: number) =>
                            `${i + 1}. **${trial.title}**\n   Phase: ${trial.phase || 'N/A'}\n   Status: ${trial.status}\n   Location: ${trial.location || 'Multiple'}\n   NCT ID: ${trial.nctId}\n`
                        ).join('\n');
                }
                return "No clinical trials found for your query.";

            case 'drug-info':
                const drugName = message.replace(/drug|medication|info|information/gi, '').trim();
                const drugResult = await healthcareServer.fdaApiClient.getDrug(
                    { genericName: drugName },
                    healthcareServer.cacheManager
                );
                if (drugResult?.content?.[0]?.text) {
                    const drugInfo = JSON.parse(drugResult.content[0].text);
                    return `**Drug Information for ${drugName}:**\n\n` +
                        `Brand Name: ${drugInfo.brandName || 'N/A'}\n` +
                        `Generic Name: ${drugInfo.genericName || drugName}\n` +
                        `Route: ${drugInfo.route || 'N/A'}\n` +
                        `Strength: ${drugInfo.strength || 'N/A'}\n` +
                        `Manufacturer: ${drugInfo.manufacturer || 'N/A'}\n` +
                        `Purpose: ${drugInfo.purpose || 'N/A'}`;
                }
                return `No FDA drug information found for "${drugName}".`;

            default:
                return "Healthcare tool not recognized. Please specify PubMed research, clinical trials, or drug information.";
        }
    } catch (error) {
        console.error(`Healthcare tool error (${tool}):`, error);
        return `Error accessing ${tool}. Please try again or contact support.`;
    }
}

async function handleSpecializedAgent(message: string, agent: string, messages: any[]): Promise<string> {
    // For now, return a placeholder that indicates the agent would be called
    // In full implementation, this would integrate with the main.py agent system
    const agentDescriptions = {
        'intake': 'patient intake and initial assessment',
        'document_processor': 'medical document analysis and processing',
        'research_assistant': 'comprehensive medical literature research'
    };

    return `🤖 **Specialized Agent Response (${agent})**\n\n` +
        `This query would be processed by the ${agentDescriptions[agent as keyof typeof agentDescriptions] || agent} agent.\n\n` +
        `**Agent Capabilities**: The ${agent} agent specializes in ${agentDescriptions[agent as keyof typeof agentDescriptions] || 'healthcare tasks'} ` +
        `and would provide detailed, context-aware assistance for your specific needs.\n\n` +
        `*Note: Full agent integration is in development. Currently providing Healthcare MCP tool responses.*`;
}

async function handleOpenAICloud(messages: any[], model: string): Promise<string> {
    if (!openaiClient) {
        throw new Error('OpenAI client not initialized');
    }

    try {
        const completion = await openaiClient.chat.completions.create({
            model: model,
            messages: messages,
            max_tokens: 1000,
            temperature: 0.3
        });

        return completion.choices[0]?.message?.content || "No response from OpenAI model.";
    } catch (error) {
        console.error('OpenAI API error:', error);
        throw new Error('Failed to get response from OpenAI');
    }
}

async function handleOllamaLocal(messages: any[], model: string): Promise<string> {
    // For now, return a placeholder that indicates local processing
    // In full implementation, this would call the local Ollama instance
    const lastMessage = messages[messages.length - 1]?.content || '';

    return `🏠 **Local AI Processing (${model})**\n\n` +
        `Your query: "${lastMessage.substring(0, 100)}${lastMessage.length > 100 ? '...' : ''}"\n\n` +
        `This would be processed by the local Ollama model (${model}) ensuring complete privacy. ` +
        `Local processing is especially important for queries containing sensitive healthcare information.\n\n` +
        `**Privacy Benefits**: Your data never leaves this system, ensuring HIPAA compliance and complete confidentiality.\n\n` +
        `*Note: Full Ollama integration is in development. Currently providing Healthcare MCP tool responses.*`;
}

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

const transportMode = process.env.MCP_TRANSPORT;
const isPrimaryContainerProcess = process.pid === 1; // PID 1 inside container
// Treat non-PID1 stdio invocation (docker exec) as pure stdio-only; main PID1 keeps HTTP + optional side-channel
const effectiveStdioOnly = transportMode === 'stdio-only' || (transportMode === 'stdio' && !isPrimaryContainerProcess);

if (effectiveStdioOnly) {
    if (transportMode === 'stdio' && !isPrimaryContainerProcess) {
        console.error('[MCP][startup] docker exec stdio session detected (non-PID1). Running in STDIO ONLY mode.');
    }
    console.error('[MCP][startup] Starting Healthcare MCP in EFFECTIVE STDIO ONLY mode');
    console.error(`[MCP][startup] Registering tools: ${healthcareServer.getTools().map((t: any) => t.name).join(', ')}`);

    // For container primary process (PID 1), also start HTTP server for healthcheck even in stdio-only mode
    if (isPrimaryContainerProcess) {
        app.listen(PORT, '0.0.0.0', () => {
            console.error(`[MCP][startup] Healthcare MCP Server running on port ${PORT} (healthcheck endpoint only)`);
            console.error(`[MCP][startup] Health check available at http://localhost:${PORT}/health`);
            console.error(`[MCP][startup] Available tools: ${healthcareServer.getTools().map((t: any) => t.name).join(', ')}`);
        });
        console.error('[MCP][startup] Primary container process - HTTP healthcheck enabled alongside stdio');

        // Keep stdio available for MCP client connections via docker exec
        healthcareServer.run().catch(err => console.error('[MCP][run][error]', err));
    } else {
        // Non-primary process (docker exec) - pure stdio only
        healthcareServer.run().catch(err => console.error('[MCP][run][error]', err));
    }
} else {
    // Primary container process: start HTTP listener (needed for healthcheck) and optionally stdio side-channel
    app.listen(PORT, '0.0.0.0', () => {
        console.error(`[MCP][startup] Healthcare MCP Server running on port ${PORT}`);
        console.error(`[MCP][startup] Health check available at http://localhost:${PORT}/health`);
        console.error(`[MCP][startup] Available tools: ${healthcareServer.getTools().map((t: any) => t.name).join(', ')}`);
    });
    if (transportMode === 'stdio') {
        console.error('[MCP][startup] Enabling STDIO side-channel (primary PID1 process)');
        healthcareServer.run().catch(err => console.error('[MCP][run][error]', err));
    }
}