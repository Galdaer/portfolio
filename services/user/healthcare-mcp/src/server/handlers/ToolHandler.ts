import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { CallToolRequestSchema, ErrorCode, ListToolsRequestSchema, McpError } from "@modelcontextprotocol/sdk/types.js";
import { parseClinicianQuery } from "../../query-parser.js";
import { FhirClient } from "../connectors/fhir/FhirClient.js";
import { ClinicalTrials } from "../connectors/medical/ClinicalTrials.js";
import { DrugInfo } from "../connectors/medical/DrugInfo.js";
import { PubMed } from "../connectors/medical/PubMed.js";
import { ICD10Connector } from "../connectors/medical/ICD10Connector.js";
import { BillingCodesConnector } from "../connectors/medical/BillingCodesConnector.js";
import { HealthInfoConnector } from "../connectors/medical/HealthInfoConnector.js";
import { DailyMedConnector } from "../connectors/medical/DailyMedConnector.js";
import { RxClassConnector } from "../connectors/medical/RxClassConnector.js";
import { DrugCentralConnector } from "../connectors/medical/DrugCentralConnector.js";
import { DDInterConnector } from "../connectors/medical/DDInterConnector.js";
import { LactMedConnector } from "../connectors/medical/LactMedConnector.js";
import { OpenFDAFAERSConnector } from "../connectors/medical/OpenFDAFAERSConnector.js";
import { TOOL_DEFINITIONS } from "../constants/tools.js";
import { Auth } from "../utils/Auth.js";
import { AuthConfig } from "../utils/AuthConfig.js";
import { CacheManager } from "../utils/Cache.js";
import { DatabaseManager } from "../utils/DatabaseManager.js";

export class ToolHandler {
    private fhirClient: FhirClient;
    private cache: CacheManager;
    private pubmedApi: PubMed;
    private trialsApi: ClinicalTrials;
    private drugInfoApi: DrugInfo;
    private icd10Connector: ICD10Connector;
    private billingCodesConnector: BillingCodesConnector;
    private healthInfoConnector: HealthInfoConnector;
    private dailyMedConnector: DailyMedConnector;
    private rxClassConnector: RxClassConnector;
    private drugCentralConnector: DrugCentralConnector;
    private ddinterConnector: DDInterConnector;
    private lactMedConnector: LactMedConnector;
    private openFDAFAERSConnector: OpenFDAFAERSConnector;
    private auth!: Auth;
    private authInitialized: boolean = false;
    private authConfig: AuthConfig;
    private dbManager: DatabaseManager;

    constructor(authConfig: AuthConfig, fhirClient: FhirClient, cache: CacheManager, pubmedApi: PubMed, trialsApi: ClinicalTrials, drugInfoApi: DrugInfo, dbManager?: DatabaseManager) {
        this.authConfig = authConfig;
        this.cache = cache;
        this.fhirClient = fhirClient;
        this.pubmedApi = pubmedApi;
        this.trialsApi = trialsApi;
        this.drugInfoApi = drugInfoApi;
        
        // Initialize database manager and new connectors
        this.dbManager = dbManager || DatabaseManager.fromEnvironment();
        this.icd10Connector = new ICD10Connector(this.dbManager);
        this.billingCodesConnector = new BillingCodesConnector(this.dbManager);
        this.healthInfoConnector = new HealthInfoConnector(this.dbManager);
        this.dailyMedConnector = new DailyMedConnector(this.dbManager);
        this.rxClassConnector = new RxClassConnector(this.dbManager);
        this.drugCentralConnector = new DrugCentralConnector(this.dbManager);
        this.ddinterConnector = new DDInterConnector(this.dbManager);
        this.lactMedConnector = new LactMedConnector(this.dbManager);
        this.openFDAFAERSConnector = new OpenFDAFAERSConnector(this.dbManager);
    }

    register(mcpServer: Server) {
        mcpServer.setRequestHandler(ListToolsRequestSchema, this.handleList);
        mcpServer.setRequestHandler(CallToolRequestSchema, this.handleCall);
    }

    private handleList = async () => {
        // Instrumentation for stdio debugging
        const toolNames = TOOL_DEFINITIONS.map(t => t.name).join(", ");
        console.error(`[MCP][tools/list] Returning ${TOOL_DEFINITIONS.length} tools: ${toolNames}`);
        return {
            tools: TOOL_DEFINITIONS
        };
    };

    private handleCall = async (request: any) => {
        // Normalize tool name: treat underscores and hyphens equivalently
        const rawName = request?.params?.name ?? "";
        const name = String(rawName).replace(/_/g, "-");

        // Tools that don't require FHIR authentication
        const noAuthTools = [
            "search-pubmed", "search-trials", "get-drug-info", "echo-test",
            "search-icd10", "search-billing-codes", "lookup-code-details",
            "search-health-topics", "search-exercises", "search-food-items",
            "search-dailymed-labels", "get-dailymed-drug-interactions", "get-dailymed-pregnancy-info",
            "search-rxclass-classifications", "get-rxclass-drug-mechanism", "get-rxclass-similar-drugs",
            "search-drugcentral-drugs", "get-drugcentral-pharmacokinetics", "get-drugcentral-drug-targets", "get-drugcentral-structural-data",
            "search-ddinter-interactions", "check-drug-interaction", "get-drug-interaction-profile", "check-polypharmacy-interactions",
            "search-lactmed-drugs", "get-lactation-risk-assessment", "get-breastfeeding-safe-drugs", "get-lactmed-safer-alternatives",
            "search-faers-adverse-events", "get-drug-safety-profile", "get-serious-adverse-events", "get-faers-age-group-analysis"
        ];

        if (noAuthTools.includes(name)) {
            // Handle non-auth tools directly
            switch (name) {
                case "search-pubmed":
                    return await this.pubmedApi.getArticles(request.params.arguments, this.cache);
                case "search-trials":
                    return await this.trialsApi.getTrials(request.params.arguments, this.cache);
                case "get-drug-info":
                    return await this.drugInfoApi.getDrug(request.params.arguments, this.cache);
                case "search-icd10":
                    return await this.icd10Connector.searchCodes(request.params.arguments, this.cache);
                case "search-billing-codes":
                    return await this.billingCodesConnector.searchCodes(request.params.arguments, this.cache);
                case "lookup-code-details":
                    return await this.handleCodeDetailsLookup(request.params.arguments);
                case "search-health-topics":
                    return await this.healthInfoConnector.searchHealthTopics(request.params.arguments, this.cache);
                case "search-exercises":
                    return await this.healthInfoConnector.searchExercises(request.params.arguments, this.cache);
                case "search-food-items":
                    return await this.healthInfoConnector.searchFoodItems(request.params.arguments, this.cache);
                case "search-dailymed-labels":
                    return await this.dailyMedConnector.searchDrugLabels(request.params.arguments);
                case "get-dailymed-drug-interactions":
                    return await this.dailyMedConnector.getDrugInteractions(request.params.arguments.genericName);
                case "get-dailymed-pregnancy-info":
                    return await this.dailyMedConnector.getPregnancyInformation(request.params.arguments.genericName);
                case "search-rxclass-classifications":
                    return await this.rxClassConnector.searchDrugClassifications(request.params.arguments);
                case "get-rxclass-drug-mechanism":
                    return await this.rxClassConnector.getMechanismOfAction(request.params.arguments.drugName);
                case "get-rxclass-similar-drugs":
                    return await this.rxClassConnector.getSimilarDrugs(request.params.arguments.drugName, request.params.arguments.classType, request.params.arguments.maxResults);
                case "search-drugcentral-drugs":
                    return await this.drugCentralConnector.searchDrugs(request.params.arguments);
                case "get-drugcentral-pharmacokinetics":
                    return await this.drugCentralConnector.getPharmacokineticData(request.params.arguments.drugName);
                case "get-drugcentral-drug-targets":
                    return await this.drugCentralConnector.getDrugsByTarget(request.params.arguments.drugName);
                case "get-drugcentral-structural-data":
                    return await this.drugCentralConnector.getStructuralData(request.params.arguments.drugName);
                case "search-ddinter-interactions":
                    return await this.ddinterConnector.searchDrugInteractions(request.params.arguments);
                case "check-drug-interaction":
                    return await this.ddinterConnector.checkSpecificInteraction(request.params.arguments.drugA, request.params.arguments.drugB);
                case "get-drug-interaction-profile":
                    return await this.ddinterConnector.getDrugProfile(request.params.arguments.drugName);
                case "check-polypharmacy-interactions":
                    return await this.ddinterConnector.searchPolypharmacyInteractions(request.params.arguments.drugList, request.params.arguments.includeMinor);
                case "search-lactmed-drugs":
                    return await this.lactMedConnector.searchLactationDrugs(request.params.arguments);
                case "get-lactation-risk-assessment":
                    return await this.lactMedConnector.getLactationRiskAssessment(request.params.arguments.drugName);
                case "get-breastfeeding-safe-drugs":
                    return await this.lactMedConnector.getBreastfeedingSafeDrugs(request.params.arguments.drugClass, request.params.arguments.maxResults);
                case "get-lactmed-safer-alternatives":
                    return await this.lactMedConnector.getSaferAlternatives(request.params.arguments.drugName);
                case "search-faers-adverse-events":
                    return await this.openFDAFAERSConnector.searchAdverseEvents(request.params.arguments);
                case "get-drug-safety-profile":
                    return await this.openFDAFAERSConnector.getDrugSafetyProfile(request.params.arguments.drugName);
                case "get-serious-adverse-events":
                    return await this.openFDAFAERSConnector.getSeriousAdverseEvents(request.params.arguments.drugName, request.params.arguments.maxResults);
                case "get-faers-age-group-analysis":
                    return await this.openFDAFAERSConnector.getAgeGroupAnalysis(request.params.arguments.drugName);
                case "echo-test":
                    return {
                        content: [{
                            type: 'text',
                            text: JSON.stringify({
                                echoed: request.params.arguments?.text,
                                timestamp: new Date().toISOString()
                            }, null, 2)
                        }]
                    };
                default:
                    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
            }
        }

        // For patient-specific tools, require patientId
        const publicTools = [
            "find-patient",
            "search-pubmed",
            "search-clinical-trials",
            "search-trials",
            "get-drug-info",
            "search-fda-drugs"
        ];
        // Normalize arguments for underscore inputs as well
        const normalizedForAuthCheck = name;
        if (!publicTools.includes(normalizedForAuthCheck)) {
            if (!request.params?.arguments?.patientId) {
                throw new McpError(ErrorCode.InvalidParams, "patientId is required");
            }
        }

        //initalize auth if not already initialized. this will set up the callback server 
        if (!this.authInitialized) {
            try {
                this.auth = new Auth(this.authConfig);
                this.authInitialized = true;
            } catch (error) {
                console.error('[ToolHandler] Failed to initialize auth:', error);
                throw new McpError(ErrorCode.InternalError, "Authentication system not available");
            }
        }

        try {
            return this.auth.executeWithAuth(async () => {
                const access_token = await this.auth.ensureValidToken();
                this.fhirClient.setAccessToken(access_token);

                switch (name) {
                    case "clinical_query":
                        return await this.handleClinicalQuery(request.params.arguments);
                    case "find-patient":
                        return await this.fhirClient.findPatient(request.params.arguments);
                    case "get-patient-observations":
                        return await this.fhirClient.getPatientObservations(request.params.arguments);
                    case "get-patient-conditions":
                        return await this.fhirClient.getPatientConditions(request.params.arguments);
                    case "get-patient-medications":
                        return await this.fhirClient.getPatientMedications(request.params.arguments);
                    case "get-patient-encounters":
                        return await this.fhirClient.getPatientEncounters(request.params.arguments);
                    case "get-patient-allergies":
                        return await this.fhirClient.getPatientAllergies(request.params.arguments);
                    case "get-patient-procedures":
                        return await this.fhirClient.getPatientProcedures(request.params.arguments);
                    case "get-patient-careteam":
                        return await this.fhirClient.getPatientCareTeam(request.params.arguments);
                    case "get-patient-careplans":
                        return await this.fhirClient.getPatientCarePlans(request.params.arguments);
                    case "get-vital-signs":
                        return await this.fhirClient.getPatientVitalSigns(request.params.arguments);
                    case "get-lab-results":
                        return await this.fhirClient.getPatientLabResults(request.params.arguments);
                    case "get-medications-history":
                        return await this.fhirClient.getMedicationHistory(request.params.arguments);
                    case "get-appointments":
                        return await this.fhirClient.getPatientAppointments(request.params.arguments);
                    default:
                        throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
                }
            });
        } catch (error) {
            console.error(`[ToolHandler] Auth error for tool ${name}:`, error);
            if (error instanceof McpError) {
                throw error;
            }
            // Convert auth errors to user-friendly messages
            if (error instanceof Error) {
                if (error.message.includes('OAuth not configured')) {
                    throw new McpError(ErrorCode.InternalError, "FHIR authentication not configured - only public medical tools available");
                }
                if (error.message.includes('authentication required')) {
                    throw new McpError(ErrorCode.InternalError, "FHIR authentication required for patient data access");
                }
            }
            throw new McpError(ErrorCode.InternalError, "Authentication error");
        }
    }

    private async handleCodeDetailsLookup(args: any) {
        const { code, code_type } = args;
        
        if (!code || !code_type) {
            throw new McpError(ErrorCode.InvalidParams, "Both 'code' and 'code_type' are required");
        }

        try {
            let result;
            if (code_type === 'icd10') {
                result = await this.icd10Connector.lookupCodeDetails(code);
            } else if (code_type === 'hcpcs') {
                result = await this.billingCodesConnector.lookupCodeDetails(code);
            } else {
                throw new McpError(ErrorCode.InvalidParams, "code_type must be 'icd10' or 'hcpcs'");
            }

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify(result || { error: `No details found for code: ${code}` }, null, 2)
                }]
            };
        } catch (error) {
            console.error(`Code details lookup error for ${code}:`, error);
            return {
                content: [{
                    type: 'text',
                    text: `Error looking up code details: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
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
                case 'search-pubmed':
                    return await this.pubmedApi.getArticles(params, this.cache);
                case 'search-trials':
                case 'search_clinical_trials':
                    return await this.trialsApi.getTrials(params, this.cache);
                case 'get-drug-info':
                case 'search_fda_drugs':
                    return await this.drugInfoApi.getDrug(params, this.cache);
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