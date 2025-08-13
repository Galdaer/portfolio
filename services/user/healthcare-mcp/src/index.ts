#!/usr/bin/env node
// EARLY STDIO TAP (inserted before any other imports that may write to stdout)
// We capture the very first chunks arriving on stdin and tee them to a file to verify
// whether an MCP client actually sends an initialize request over stdio. This occurs
// before loading the SDK so we can distinguish transport vs. server handler issues.
{
    // Wrap in an async IIFE to allow dynamic import without top-level await (compiled ESM acceptable)
    (async () => {
        try {
            // DISABLED: Early stdio tap was consuming MCP frames meant for stdio_entry.js
            // Only index.js runs as the main container process; MCP client execs stdio_entry.js separately
            const earlyTransportMode = process.env.MCP_TRANSPORT;
            if (false && (earlyTransportMode === 'stdio' || earlyTransportMode === 'stdio-only')) {
                // ... early tap code disabled
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

// DISABLED: Frame logging was interfering with stdio_entry.js MCP sessions
// When index.js runs as main process and stdio_entry.js is exec'd separately,
// frame logging from index.js corrupts the stdio streams for stdio_entry.js
if (false && (__transportMode === 'stdio' || __transportMode === 'stdio-only')) {
    // ... frame logging disabled
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

// Keep only essential health check endpoint - remove HTTP tool endpoints
// Tools should ONLY be accessed via stdio MCP protocol through MCP client

// Health check endpoint (required for Docker health checks)
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', service: 'healthcare-mcp', timestamp: new Date().toISOString() });
});

// IMPORTANT: All tool access must go through stdio MCP protocol
// HTTP endpoints for tools have been removed to enforce proper MCP client usage

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