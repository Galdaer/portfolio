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
    },
    {
        name: 'search-dailymed-labels',
        description: 'Search FDA DailyMed drug labels for detailed prescribing information, warnings, and dosing.',
        inputSchema: {
            type: 'object',
            properties: {
                genericName: { type: 'string', description: 'Generic drug name to search' },
                brandName: { type: 'string', description: 'Brand drug name to search' },
                manufacturer: { type: 'string', description: 'Drug manufacturer' },
                ndc: { type: 'string', description: 'National Drug Code' },
                maxResults: { type: 'number', description: 'Maximum number of labels to return (default 10)' }
            },
            required: []
        }
    },
    {
        name: 'get-dailymed-drug-interactions',
        description: 'Get drug interaction information from DailyMed labels.',
        inputSchema: {
            type: 'object',
            properties: {
                genericName: { type: 'string', description: 'Generic drug name' }
            },
            required: ['genericName']
        }
    },
    {
        name: 'get-dailymed-pregnancy-info',
        description: 'Get pregnancy and lactation information from DailyMed labels.',
        inputSchema: {
            type: 'object',
            properties: {
                genericName: { type: 'string', description: 'Generic drug name' }
            },
            required: ['genericName']
        }
    },
    {
        name: 'search-rxclass-classifications',
        description: 'Search RxClass therapeutic drug classifications (ATC, MOA, PE, etc.).',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name to classify' },
                className: { type: 'string', description: 'Classification name to search' },
                classType: { type: 'string', description: 'Classification type (ATC, MOA, PE, EPC, etc.)' },
                maxResults: { type: 'number', description: 'Maximum number of classifications to return (default 25)' }
            },
            required: []
        }
    },
    {
        name: 'get-rxclass-drug-mechanism',
        description: 'Get mechanism of action classifications for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'get-rxclass-similar-drugs',
        description: 'Find drugs with similar therapeutic classifications.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Reference drug name' },
                classType: { type: 'string', description: 'Classification type to compare (default ATC)' },
                maxResults: { type: 'number', description: 'Maximum number of similar drugs (default 20)' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'search-drugcentral-drugs',
        description: 'Search DrugCentral comprehensive pharmaceutical database for drugs, targets, and pharmacology.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name to search' },
                targetName: { type: 'string', description: 'Drug target name' },
                indication: { type: 'string', description: 'Medical indication' },
                mechanismOfAction: { type: 'string', description: 'Mechanism of action' },
                maxResults: { type: 'number', description: 'Maximum number of drugs to return (default 25)' }
            },
            required: []
        }
    },
    {
        name: 'get-drugcentral-pharmacokinetics',
        description: 'Get pharmacokinetic data (absorption, metabolism, elimination) for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'get-drugcentral-drug-targets',
        description: 'Get molecular targets and binding information for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'get-drugcentral-structural-data',
        description: 'Get chemical structure data (SMILES, InChI, molecular weight) for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'search-ddinter-interactions',
        description: 'Search DDInter database for comprehensive drug-drug interactions.',
        inputSchema: {
            type: 'object',
            properties: {
                drugA: { type: 'string', description: 'First drug name' },
                drugB: { type: 'string', description: 'Second drug name' },
                severity: { type: 'string', description: 'Interaction severity (major, moderate, minor)' },
                mechanism: { type: 'string', description: 'Interaction mechanism' },
                includeMinor: { type: 'boolean', description: 'Include minor interactions (default false)' },
                maxResults: { type: 'number', description: 'Maximum number of interactions to return (default 50)' }
            },
            required: []
        }
    },
    {
        name: 'check-drug-interaction',
        description: 'Check for specific interactions between two drugs.',
        inputSchema: {
            type: 'object',
            properties: {
                drugA: { type: 'string', description: 'First drug name' },
                drugB: { type: 'string', description: 'Second drug name' }
            },
            required: ['drugA', 'drugB']
        }
    },
    {
        name: 'get-drug-interaction-profile',
        description: 'Get comprehensive interaction profile for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'check-polypharmacy-interactions',
        description: 'Analyze drug interactions for multiple medications (polypharmacy).',
        inputSchema: {
            type: 'object',
            properties: {
                drugList: { type: 'array', items: { type: 'string' }, description: 'List of drug names' },
                includeMinor: { type: 'boolean', description: 'Include minor interactions (default false)' }
            },
            required: ['drugList']
        }
    },
    {
        name: 'search-lactmed-drugs',
        description: 'Search LactMed database for breastfeeding safety information.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name to search' },
                riskCategory: { type: 'string', description: 'Lactation risk category' },
                maxResults: { type: 'number', description: 'Maximum number of drugs to return (default 25)' }
            },
            required: []
        }
    },
    {
        name: 'get-lactation-risk-assessment',
        description: 'Get comprehensive lactation risk assessment for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'get-breastfeeding-safe-drugs',
        description: 'Get list of drugs considered safe during breastfeeding.',
        inputSchema: {
            type: 'object',
            properties: {
                drugClass: { type: 'string', description: 'Therapeutic drug class' },
                maxResults: { type: 'number', description: 'Maximum number of drugs to return (default 50)' }
            },
            required: []
        }
    },
    {
        name: 'get-lactmed-safer-alternatives',
        description: 'Find safer alternatives for breastfeeding mothers.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Current drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'search-faers-adverse-events',
        description: 'Search FDA FAERS database for adverse drug events and safety signals.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' },
                adverseReaction: { type: 'string', description: 'Adverse reaction term' },
                ageGroup: { type: 'string', description: 'Patient age group' },
                gender: { type: 'string', description: 'Patient gender' },
                seriousOnly: { type: 'boolean', description: 'Show only serious adverse events' },
                maxResults: { type: 'number', description: 'Maximum number of events to return (default 50)' }
            },
            required: []
        }
    },
    {
        name: 'get-drug-safety-profile',
        description: 'Get comprehensive safety profile for a drug from FAERS data.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'get-serious-adverse-events',
        description: 'Get serious adverse events for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' },
                maxResults: { type: 'number', description: 'Maximum number of events to return (default 100)' }
            },
            required: ['drugName']
        }
    },
    {
        name: 'get-faers-age-group-analysis',
        description: 'Analyze adverse events by age group for a drug.',
        inputSchema: {
            type: 'object',
            properties: {
                drugName: { type: 'string', description: 'Drug name' }
            },
            required: ['drugName']
        }
    }
]; 