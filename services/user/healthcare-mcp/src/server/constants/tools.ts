export const TOOL_DEFINITIONS = [
    {
        name: "echo_test",
        description: "Echo back provided text (diagnostic tool to validate MCP stdio tool listing)",
        inputSchema: {
            type: "object",
            properties: {
                text: { type: "string", description: "Arbitrary text to echo" }
            },
            required: ["text"]
        }
    },
    {
        name: "find_patient",
        description: "Search for a patient by demographics",
        inputSchema: {
            type: "object",
            properties: {
                lastName: { type: "string" },
                firstName: { type: "string" },
                birthDate: { type: "string", description: "YYYY-MM-DD format" },
                gender: {
                    type: "string",
                    enum: ["male", "female", "other", "unknown"]
                }
            },
            required: ["lastName"]
        }
    },
    {
        name: "get_patient_observations",
        description: "Get observations (vitals, labs) for a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                code: { type: "string", description: "LOINC or SNOMED code" },
                dateFrom: { type: "string", description: "YYYY-MM-DD" },
                dateTo: { type: "string", description: "YYYY-MM-DD" },
                status: {
                    type: "string",
                    enum: ["registered", "preliminary", "final", "amended", "corrected", "cancelled"]
                }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_patient_conditions",
        description: "Get medical conditions/diagnoses for a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                status: {
                    type: "string",
                    enum: ["active", "inactive", "resolved"]
                },
                onsetDate: { type: "string", description: "YYYY-MM-DD" }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_patient_medications",
        description: "Get medication orders for a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                status: {
                    type: "string",
                    enum: ["active", "completed", "stopped", "on-hold"]
                }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_patient_encounters",
        description: "Get healthcare encounters/visits for a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                status: {
                    type: "string",
                    enum: ["planned", "arrived", "in-progress", "finished", "cancelled"]
                },
                dateFrom: { type: "string", description: "YYYY-MM-DD" },
                dateTo: { type: "string", description: "YYYY-MM-DD" }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_patient_allergies",
        description: "Get allergies and intolerances for a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                status: {
                    type: "string",
                    enum: ["active", "inactive", "resolved"]
                },
                type: {
                    type: "string",
                    enum: ["allergy", "intolerance"]
                },
                category: {
                    type: "string",
                    enum: ["food", "medication", "environment", "biologic"]
                }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_patient_procedures",
        description: "Get procedures performed on a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                status: {
                    type: "string",
                    enum: ["preparation", "in-progress", "completed", "entered-in-error"]
                },
                dateFrom: { type: "string", description: "YYYY-MM-DD" },
                dateTo: { type: "string", description: "YYYY-MM-DD" }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_patient_careplans",
        description: "Get care plans for a patient",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                status: {
                    type: "string",
                    enum: ["draft", "active", "suspended", "completed", "cancelled"]
                },
                category: { type: "string" },
                dateFrom: { type: "string", description: "YYYY-MM-DD" },
                dateTo: { type: "string", description: "YYYY-MM-DD" }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_vital_signs",
        description: "Get patient's vital signs history",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                timeframe: {
                    type: "string",
                    description: "e.g., 3m, 6m, 1y, all"
                }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_lab_results",
        description: "Get patient's lab results",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                category: {
                    type: "string",
                    description: "e.g., CBC, METABOLIC, LIPIDS, ALL"
                },
                timeframe: { type: "string" }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_medications_history",
        description: "Get patient's medication history including changes",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                includeDiscontinued: { type: "boolean" }
            },
            required: ["patientId"]
        }
    },
    {
        name: "get_appointments",
        description: "Get patient's Appointments",
        inputSchema: {
            type: "object",
            properties: {
                patientId: { type: "string" },
                dateFrom: { type: "string", description: "YYYY-MM-DD" },
                dateTo: { type: "string", description: "YYYY-MM-DD" }
            },
            required: ["patientId"]
        }
    },
    {
        name: 'search-pubmed',
        description: 'Search PubMed for peer‑reviewed biomedical articles. Use for literature searches (reviews, RCTs, meta‑analyses). Not for clinical trial registry or FDA drug labels.',
        inputSchema: {
            type: 'object',
            properties: {
                query: { type: 'string' },
                maxResults: { type: 'number' }
            },
            required: ['query']
        }
    },
    {
        name: 'search-trials',
        description: 'Search ClinicalTrials.gov for clinical studies. Use when the user asks about trials, phases, recruiting status or NCT IDs. Not for journal articles.',
        inputSchema: {
            type: 'object',
            properties: {
                condition: { type: 'string' },
                location: { type: 'string' },
                maxResults: { type: 'number', description: 'Maximum number of trials to return (default 25)' }
            },
            required: ['condition']
        }
    },
    {
        name: 'get-drug-info',
        description: 'Get FDA drug product/label info by generic name. Use for regulatory/label details (NDC, manufacturer, ingredients). Not for literature or clinical trials.',
        inputSchema: {
            type: 'object',
            properties: {
                genericName: { type: 'string' },
            },
            required: ['genericName']
        }
    },
    {
        name: 'search-icd10',
        description: 'Search ICD-10 diagnostic codes. Use for finding diagnosis codes by condition name or validating existing codes.',
        inputSchema: {
            type: 'object',
            properties: {
                query: { type: 'string', description: 'Diagnostic term or ICD-10 code to search' },
                max_results: { type: 'number', description: 'Maximum number of codes to return (default 10)' },
                exact_match: { type: 'boolean', description: 'Require exact code match (default false)' }
            },
            required: ['query']
        }
    },
    {
        name: 'search-billing-codes',
        description: 'Search medical billing codes (HCPCS/CPT). Use for finding procedure and billing codes.',
        inputSchema: {
            type: 'object',
            properties: {
                query: { type: 'string', description: 'Procedure term or billing code to search' },
                code_type: { type: 'string', enum: ['hcpcs', 'cpt', 'all'], description: 'Type of codes to search (default all)' },
                max_results: { type: 'number', description: 'Maximum number of codes to return (default 10)' }
            },
            required: ['query']
        }
    },
    {
        name: 'lookup-code-details',
        description: 'Get detailed information for specific medical codes (ICD-10 or HCPCS).',
        inputSchema: {
            type: 'object',
            properties: {
                code: { type: 'string', description: 'Specific medical code to lookup' },
                code_type: { type: 'string', enum: ['icd10', 'hcpcs'], description: 'Type of code' }
            },
            required: ['code', 'code_type']
        }
    },
    {
        name: 'search-health-topics',
        description: 'Search health information topics. Use for patient education and health guidance.',
        inputSchema: {
            type: 'object',
            properties: {
                query: { type: 'string', description: 'Health topic or condition to search' },
                max_results: { type: 'number', description: 'Maximum number of topics to return (default 10)' }
            },
            required: ['query']
        }
    },
    {
        name: 'search-exercises',
        description: 'Search exercise recommendations. Use for physical therapy and fitness guidance.',
        inputSchema: {
            type: 'object',
            properties: {
                query: { type: 'string', description: 'Exercise type or muscle group to search' },
                muscle_group: { type: 'string', description: 'Specific muscle group to target' },
                max_results: { type: 'number', description: 'Maximum number of exercises to return (default 10)' }
            },
            required: ['query']
        }
    },
    {
        name: 'search-food-items',
        description: 'Search nutritional information. Use for dietary guidance and nutrition data.',
        inputSchema: {
            type: 'object',
            properties: {
                query: { type: 'string', description: 'Food item to search' },
                max_results: { type: 'number', description: 'Maximum number of food items to return (default 10)' }
            },
            required: ['query']
        }
    }
]; 