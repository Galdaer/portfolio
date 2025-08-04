import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { ListToolsRequestSchema, CallToolRequestSchema, McpError, ErrorCode } from "@modelcontextprotocol/sdk/types.js";
import { FhirClient } from "../connectors/fhir/FhirClient.js"
import { TOOL_DEFINITIONS } from "../constants/tools.js"
import { parseClinicianQuery } from "../../query-parser.js";
import { PubMed } from "../connectors/medical/PubMed.js"
import { ClinicalTrials } from "../connectors/medical/ClinicalTrials.js"
import { FDA } from "../connectors/medical/FDA.js"
import { CacheManager } from "../utils/Cache.js"
import { Auth } from "../utils/Auth.js"
import { AuthConfig } from "../utils/AuthConfig.js"

export class ToolHandler {
    private fhirClient: FhirClient;
    private cache: CacheManager;
    private pubmedApi: PubMed;
    private trialsApi: ClinicalTrials;
    private fdaApi: FDA;
    private auth!: Auth;
    private authInitialized: boolean = false;
    private authConfig: AuthConfig;

    constructor(authConfig: AuthConfig, fhirClient: FhirClient, cache: CacheManager, pubmedApi: PubMed, trialsApi: ClinicalTrials, fdaApi: FDA) {
        this.authConfig = authConfig;
        this.cache = cache;
        this.fhirClient = fhirClient;
        this.pubmedApi = pubmedApi;
        this.trialsApi = trialsApi;
        this.fdaApi = fdaApi;
    }

    register(mcpServer: Server) {
        mcpServer.setRequestHandler(ListToolsRequestSchema, this.handleList);
        mcpServer.setRequestHandler(CallToolRequestSchema, this.handleCall);
    }

    private handleList = async () => ({
        tools: TOOL_DEFINITIONS
    });

    private handleCall = async (request: any) => {
        if (request.params?.name != "find_patient" && request.params?.name != "get-drug-info"
            && request.params?.name != "search-trials" && request.params?.name != "search-pubmed") {
            if (!request.params?.arguments?.patientId) {
                throw new McpError(ErrorCode.InvalidParams, "patientId is required");
            }
        }

        //initalize auth if not already initialized. this will set up the callback server 
        if (!this.authInitialized) {
            this.auth = new Auth(this.authConfig);
            this.authInitialized = true;
        }

        return this.auth.executeWithAuth(async () => {

            const access_token = await this.auth.ensureValidToken();

            this.fhirClient.setAccessToken(access_token);

            switch (request.params.name) {
                case "clinical_query":
                    return await this.handleClinicalQuery(request.params.arguments);
                case "find_patient":
                    return await this.fhirClient.findPatient(request.params.arguments);
                case "get_patient_observations":
                    return await this.fhirClient.getPatientObservations(request.params.arguments);
                case "get_patient_conditions":
                    return await this.fhirClient.getPatientConditions(request.params.arguments);
                case "get_patient_medications":
                    return await this.fhirClient.getPatientMedications(request.params.arguments);
                case "get_patient_encounters":
                    return await this.fhirClient.getPatientEncounters(request.params.arguments);
                case "get_patient_allergies":
                    return await this.fhirClient.getPatientAllergies(request.params.arguments);
                case "get_patient_procedures":
                    return await this.fhirClient.getPatientProcedures(request.params.arguments);
                case "get_patient_careteam":
                    return await this.fhirClient.getPatientCareTeam(request.params.arguments);
                case "get_patient_careplans":
                    return await this.fhirClient.getPatientCarePlans(request.params.arguments);
                case "get_vital_signs":
                    return await this.fhirClient.getPatientVitalSigns(request.params.arguments);
                case "get_lab_results":
                    return await this.fhirClient.getPatientLabResults(request.params.arguments);
                case "get_medications_history":
                    return await this.fhirClient.getMedicationHistory(request.params.arguments);
                case "get_appointments":
                    return await this.fhirClient.getPatientAppointments(request.params.arguments);
                case "search-pubmed":
                    return await this.pubmedApi.getArticles(request.params.arguments, this.cache);
                case "search-trials":
                    return await this.trialsApi.getTrials(request.params.arguments, this.cache);
                case "get-drug-info":
                    return await this.fdaApi.getDrug(request.params.arguments, this.cache);
                default:
                    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
            }
        });
    }

    private async handleClinicalQuery(args: any) {
        if (!args.query) {
            throw new McpError(ErrorCode.InvalidParams, "Query is required");
        }

        try {
            const queryParams = await parseClinicianQuery(args.query);
            return await this.fhirClient.executeQuery(queryParams);
        } catch (error) {
            return this.fhirClient.handleError(error);
        }
    }

    getRegisteredTools() {
        // Return the same tools that are defined in TOOL_DEFINITIONS to ensure consistency
        return TOOL_DEFINITIONS;
    }

    // Handle tool calls from HTTP mode - maps to the same tools as the MCP handlers
    async handleToolCall(toolName: string, params: any) {
        try {
            // Map HTTP tool names to MCP tool names if needed
            switch (toolName) {
                case 'health_check':
                    return this.handleHealthCheck();
                case 'find_patient':
                    return await this.fhirClient.findPatient(params);
                case 'get_patient_observations':
                    return await this.fhirClient.getPatientObservations(params);
                case 'get_patient_conditions':
                    return await this.fhirClient.getPatientConditions(params);
                case 'get_patient_medications':
                    return await this.fhirClient.getPatientMedications(params);
                case 'get_patient_encounters':
                    return await this.fhirClient.getPatientEncounters(params);
                case 'get_patient_allergies':
                    return await this.fhirClient.getPatientAllergies(params);
                case 'get_patient_procedures':
                    return await this.fhirClient.getPatientProcedures(params);
                case 'get_patient_careplans':
                    return await this.fhirClient.getPatientCarePlans(params);
                case 'get_vital_signs':
                    return await this.fhirClient.getPatientVitalSigns(params);
                case 'get_lab_results':
                    return await this.fhirClient.getPatientLabResults(params);
                case 'get_medications_history':
                    return await this.fhirClient.getMedicationHistory(params);
                case 'get_appointments':
                    return await this.fhirClient.getPatientAppointments(params);
                case 'search-pubmed':
                case 'search_pubmed':
                    return await this.pubmedApi.getArticles(params, this.cache);
                case 'search-trials':
                case 'search_clinical_trials':
                    return await this.trialsApi.getTrials(params, this.cache);
                case 'get-drug-info':
                case 'search_fda_drugs':
                    return await this.fdaApi.getDrug(params, this.cache);
                case 'get_fhir_patient':
                    return await this.handleFHIRPatientGet(params);
                case 'search_fhir_resources':
                    return await this.handleFHIRResourceSearch(params);
                default:
                    throw new Error(`Unknown tool: ${toolName}`);
            }
        } catch (error) {
            return {
                content: [{
                    type: 'text',
                    text: `Error executing ${toolName}: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    // Helper methods for HTTP mode
    private handleHealthCheck() {
        return {
            content: [{
                type: 'text',
                text: JSON.stringify({
                    status: 'healthy',
                    timestamp: new Date().toISOString()
                }, null, 2)
            }]
        };
    }

    private async handleFHIRPatientGet(params: any) {
        const results = await this.fhirClient.getPatient(params.patient_id || params.identifier);
        return {
            content: [{
                type: 'text',
                text: JSON.stringify(results, null, 2)
            }]
        };
    }

    private async handleFHIRResourceSearch(params: any) {
        const results = await this.fhirClient.searchResources(params.resource_type, params.search_params, params.max_results);
        return {
            content: [{
                type: 'text',
                text: JSON.stringify(results, null, 2)
            }]
        };
    }
}