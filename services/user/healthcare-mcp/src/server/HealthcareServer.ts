import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { FhirClient } from "./connectors/fhir/FhirClient.js";
import { ClinicalTrials } from "./connectors/medical/ClinicalTrials.js";
import { DrugInfo } from "./connectors/medical/DrugInfo.js";
import { PubMed } from "./connectors/medical/PubMed.js";
import { OllamaHandler } from "./handlers/OllamaHandler.js";
import { ToolHandler } from "./handlers/ToolHandler.js";
import { AuthConfig } from "./utils/AuthConfig.js";
import { CacheManager } from "./utils/Cache.js";

export class HealthcareServer {
    private mcpServer: Server;
    private toolHandler: ToolHandler;
    private fhirClient: FhirClient;
    private cache: CacheManager;
    private pubmedApi: PubMed;
    private trialsApi: ClinicalTrials;
    private drugInfoApi: DrugInfo;
    private ollamaHandler: OllamaHandler;

    constructor(
        mcpServer: Server,
        authConfig: AuthConfig,
        fhirURL: string,
        pubmedAPIKey?: string,
        trialsAPIKey?: string,
        drugInfoAPIKey?: string,
        ollamaApiUrl: string = process.env.OLLAMA_URL || "http://172.20.0.10:11434",
        ollamaModel: string = (process.env.OLLAMA_MODEL || "llama3.1:8b")
    ) {
        this.mcpServer = mcpServer;
        this.fhirClient = new FhirClient(fhirURL);
        this.cache = new CacheManager();
        this.pubmedApi = new PubMed(pubmedAPIKey || "optional_for_higher_rate_limits");
        this.trialsApi = new ClinicalTrials(trialsAPIKey);
        this.drugInfoApi = new DrugInfo(drugInfoAPIKey);
        this.ollamaHandler = new OllamaHandler(ollamaApiUrl, ollamaModel);

        this.toolHandler = new ToolHandler(authConfig, this.fhirClient, this.cache, this.pubmedApi, this.trialsApi, this.drugInfoApi);

        this.setupHandlers();
        this.setupErrorHandling();
    }
    /**
     * Generates administrative documentation using Ollama LLM.
     * Healthcare compliance disclaimer: For documentation support only. No medical advice or diagnosis.
     */
    async generateDocumentation(prompt: string, model?: string): Promise<string> {
        return await this.ollamaHandler.generateText(prompt, model);
    }

    // Method to get tools for HTTP mode
    /**
     * Returns the list of registered tools.
     * Healthcare compliance disclaimer: This function provides administrative and documentation support only. No medical advice or diagnosis is given.
     */
    getTools() {
        return this.toolHandler.getRegisteredTools();
    }

    // Expose APIs for REST endpoints
    get pubmedApiClient() { return this.pubmedApi; }
    get trialsApiClient() { return this.trialsApi; }
    get fdaApiClient() { return this.fdaApi; }
    get cacheManager() { return this.cache; }

    /**
     * Returns detailed trial information for a given trial ID.
     * Healthcare compliance disclaimer: For administrative use only. No medical advice or patient matching.
     */
    async getTrialDetails(trialId: string): Promise<Record<string, any>> {
        // Synthetic example
        return {
            trialId,
            title: "Diabetes Management Study",
            phase: "Phase 3",
            enrollmentStatus: "Recruiting",
            sponsor: "NIH",
            locations: ["Boston, MA", "San Francisco, CA"],
            startDate: "2025-09-01",
            endDate: "2026-09-01"
        };
    }

    /**
     * Matches a patient to eligible clinical trials based on demographics and conditions.
     * Healthcare compliance disclaimer: For workflow testing only. No real patient data or medical advice.
     */
    async matchPatientToTrials(patientId: string): Promise<Array<Record<string, any>>> {
        // Synthetic example
        return [
            {
                trialId: "NCT123456",
                title: "Diabetes Management Study",
                eligible: true,
                reason: "Meets age and condition criteria"
            }
        ];
    }

    /**
     * Finds clinical trial locations for a condition and zip code.
     * Healthcare compliance disclaimer: For administrative support only.
     */
    async findTrialLocations(condition: string, zipCode: string): Promise<string[]> {
        // Synthetic example
        return ["Boston Medical Center", "UCSF Medical Center"];
    }

    /**
     * Returns enrollment status for a clinical trial.
     * Healthcare compliance disclaimer: For workflow automation only.
     */
    async getEnrollmentStatus(trialId: string): Promise<string> {
        // Synthetic example
        return "Recruiting";
    }

    /**
     * Fuzzy patient search by name, DOB, or insurance.
     * Healthcare compliance disclaimer: For administrative/documentation support only. No medical advice.
     */
    async searchPatients(name?: string, dob?: string, insurance?: string): Promise<Array<Record<string, any>>> {
        // Synthetic example
        return [
            {
                patientId: "P12345",
                name: "Jane Smith",
                dob: "1980-01-01",
                insurance: "Aetna"
            }
        ];
    }

    /**
     * Returns a summary of recent patient encounters.
     * Healthcare compliance disclaimer: For documentation support only.
     */
    async getPatientEncounterSummary(patientId: string, limit: number = 5): Promise<Array<Record<string, any>>> {
        // Synthetic example
        return [
            {
                date: "2025-07-01",
                type: "Office Visit",
                provider: "Dr. John Doe"
            }
        ];
    }

    /**
     * Returns recent abnormal lab results for a patient.
     * Healthcare compliance disclaimer: For workflow testing only. No medical advice.
     */
    async getRecentLabResults(patientId: string, abnormalOnly: boolean = true): Promise<Array<Record<string, any>>> {
        // Synthetic example
        return [
            {
                test: "Hemoglobin A1c",
                value: "8.2",
                referenceRange: "4.0-6.0",
                abnormal: true,
                date: "2025-07-01"
            }
        ];
    }

    /**
     * Verifies patient insurance coverage and returns payer details.
     * Healthcare compliance disclaimer: For administrative use only.
     */
    async verifyPatientInsurance(patientId: string): Promise<Record<string, any>> {
        // Synthetic example
        return {
            patientId,
            verified: true,
            payer: "Aetna",
            plan: "Gold PPO",
            coverageStart: "2025-01-01",
            coverageEnd: "2025-12-31"
        };
    }

    // Method to handle tool calls in HTTP mode
    async callTool(toolName: string, params: any) {
        return await this.toolHandler.handleToolCall(toolName, params);
    }

    // Add method to get server status
    getServerStatus() {
        return {
            status: 'healthy',
            service: 'healthcare-mcp',
            timestamp: new Date().toISOString(),
            apis: {
                fhir: this.fhirClient.isConnected(), // This method needs to be implemented
                pubmed: !!this.pubmedApi,
                trials: !!this.trialsApi,
                fda: !!this.fdaApi
            },
            cache: {
                size: this.cache.size(), // This method needs to be implemented
                hitRate: this.cache.getHitRate() // This method needs to be implemented
            }
        };
    }

    private setupHandlers() {
        // Register tool handlers
        // Debug instrumentation: snapshot tool definitions at registration time
        try {
            const snapshot = this.toolHandler.getRegisteredTools().map(t => t.name);
            console.error(`[MCP][debug] Registering handlers with ${snapshot.length} tools: ${JSON.stringify(snapshot)}`);
        } catch (e) {
            console.error('[MCP][debug] Failed to snapshot tools during setupHandlers', e);
        }
        this.toolHandler.register(this.mcpServer);

        // Custom initialize handler temporarily disabled to allow SDK default handshake.
        // This is for debugging stdio tool discovery (zero tools). If default handshake works,
        // we can reintroduce a minimal wrapper that only adds logging.
        // Previous handler advertised tools.listChanged=true but client never triggered list.
        // Leaving capability stub created during Server instantiation.
    }

    private setupErrorHandling() {
        this.mcpServer.onerror = (error) => {
            console.error("[MCP Error]", error);
        };

        process.on("SIGINT", async () => {
            await this.mcpServer.close();
            process.exit(0);
        });
    }

    async run() {
        const transport = new StdioServerTransport();

        // DISABLED: Frame logging corrupts stdio when index.js and stdio_entry.js both run
        // Only stdio_entry.js should handle MCP stdio; index.js should not interfere
        if (false) {
            // ... frame logging disabled
        }

        await this.mcpServer.connect(transport);
        const tools = this.getTools();
        console.error(`[MCP][startup] FHIR MCP server running on stdio with ${tools.length} registered tools: ${tools.map(t => t.name).join(', ')}`);
        // Proactively emit a tools/list style log so we know registration happened before any client request
        console.error(`[MCP][debug] Tool registry snapshot at startup: ${JSON.stringify(tools.map(t => t.name))}`);
    }
}