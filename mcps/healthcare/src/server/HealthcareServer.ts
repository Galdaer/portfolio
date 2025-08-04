import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ToolHandler } from "./handlers/ToolHandler.js"
import { FhirClient } from "./connectors/fhir/FhirClient.js"
import { PubMed } from "./connectors/medical/PubMed.js"
import { ClinicalTrials } from "./connectors/medical/ClinicalTrials.js"
import { FDA } from "./connectors/medical/FDA.js"
import { CacheManager } from "./utils/Cache.js"
import { AuthConfig } from "./utils/AuthConfig.js"

export class HealthcareServer {
    private mcpServer: Server;
    private toolHandler: ToolHandler;
    private fhirClient: FhirClient;
    private cache: CacheManager;
    private pubmedApi: PubMed;
    private trialsApi: ClinicalTrials;
    private fdaApi: FDA;

    constructor(mcpServer: Server, authConfig: AuthConfig, fhirURL: string, pubmedAPIKey: string, trialsAPIKey: string, fdaAPIKey: string) {
        this.mcpServer = mcpServer;
        this.fhirClient = new FhirClient(fhirURL);
        this.cache = new CacheManager();
        this.pubmedApi = new PubMed(pubmedAPIKey);
        this.trialsApi = new ClinicalTrials(trialsAPIKey);
        this.fdaApi = new FDA(fdaAPIKey);

        this.toolHandler = new ToolHandler(authConfig, this.fhirClient, this.cache, this.pubmedApi, this.trialsApi, this.fdaApi);

        this.setupHandlers();
        this.setupErrorHandling();
    }

    // Method to get tools for HTTP mode
    getTools() {
        return this.toolHandler.getRegisteredTools();
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
        this.toolHandler.register(this.mcpServer);
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

        await this.mcpServer.connect(transport);
        console.error("FHIR MCP server running on stdio");
    }
}