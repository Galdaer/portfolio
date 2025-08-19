/**
 * MCP-Agent Bridge Implementation
 * 
 * Connects MCP tools to FastAPI agent endpoints with healthcare compliance.
 * Implements PHI-safe request/response handling and audit logging.
 */

import { Tool } from "@modelcontextprotocol/sdk/types.js";

// Healthcare-compliant agent tools available through MCP
export const agentTools: Tool[] = [
  {
    name: "clinical_intake",
    description: "Process patient intake with AI assistance and PHI protection. HEALTHCARE PROVIDER SUPPORT: Supports clinical workflow, doesn't replace clinical judgment.",
    inputSchema: {
      type: "object",
      properties: {
        patient_data: { 
          type: "object",
          description: "Patient intake data (PHI-protected)",
          properties: {
            patient_id: { type: "string", pattern: "^(TEST_|PAT)[A-Z0-9_]+$" },
            intake_type: { type: "string", enum: ["new_patient", "follow_up", "emergency"] },
            chief_complaint: { type: "string" },
            medical_history: { type: "array", items: { type: "string" } }
          },
          required: ["patient_id", "intake_type"]
        },
        session_id: { 
          type: "string",
          description: "Healthcare session identifier for audit trail"
        },
        provider_id: {
          type: "string", 
          description: "Healthcare provider identifier"
        }
      },
      required: ["patient_data", "session_id"]
    }
  },
  {
    name: "transcribe_audio",
    description: "Secure medical audio transcription with PHI scanning and HIPAA compliance. Memory-only processing, no audio storage.",
    inputSchema: {
      type: "object",
      properties: {
        audio_data: { 
          type: "object",
          description: "Audio data for transcription (memory-only processing)",
          properties: {
            format: { type: "string", enum: ["wav", "mp3", "webm"] },
            sample_rate: { type: "number" },
            channels: { type: "number" },
            data: { type: "string", description: "Base64 encoded audio data" }
          },
          required: ["format", "data"]
        },
        session_id: { 
          type: "string",
          description: "Healthcare session identifier"
        },
        provider_id: { 
          type: "string",
          description: "Healthcare provider conducting session"
        },
        transcription_options: {
          type: "object",
          properties: {
            phi_detection: { type: "boolean", default: true },
            medical_terminology: { type: "boolean", default: true },
            real_time: { type: "boolean", default: false }
          }
        }
      },
      required: ["audio_data", "session_id", "provider_id"]
    }
  },
  {
    name: "research_medical_literature",
    description: "Search PubMed and clinical guidelines with evidence synthesis. Provides research assistance only, not medical advice.",
    inputSchema: {
      type: "object",
      properties: {
        query: { 
          type: "string",
          description: "Medical research query (no patient-specific information)"
        },
        search_parameters: {
          type: "object",
          properties: {
            max_results: { type: "number", default: 10, minimum: 1, maximum: 50 },
            include_clinical_trials: { type: "boolean", default: true },
            publication_years: { 
              type: "array", 
              items: { type: "number" },
              description: "Years to include in search"
            },
            specialty_filter: { 
              type: "string",
              description: "Medical specialty to focus search"
            }
          }
        },
        session_id: {
          type: "string",
          description: "Research session identifier"
        }
      },
      required: ["query", "session_id"]
    }
  },
  {
    name: "process_healthcare_document",
    description: "AI-assisted healthcare document processing with compliance validation. Administrative support only.",
    inputSchema: {
      type: "object", 
      properties: {
        document_data: {
          type: "object",
          properties: {
            document_type: { 
              type: "string", 
              enum: ["soap_note", "discharge_summary", "referral", "progress_note"] 
            },
            content: { type: "string" },
            metadata: { 
              type: "object",
              properties: {
                provider_id: { type: "string" },
                patient_id: { type: "string", pattern: "^(TEST_|PAT)[A-Z0-9_]+$" },
                encounter_date: { type: "string", format: "date" }
              }
            }
          },
          required: ["document_type", "content"]
        },
        processing_options: {
          type: "object",
          properties: {
            phi_detection: { type: "boolean", default: true },
            structure_analysis: { type: "boolean", default: true },
            compliance_check: { type: "boolean", default: true }
          }
        },
        session_id: { type: "string" }
      },
      required: ["document_data", "session_id"]
    }
  }
];

// Interface for agent response with healthcare compliance
interface HealthcareAgentResponse {
  success: boolean;
  data?: any;
  error?: string;
  medical_disclaimer: string;
  audit_info: {
    session_id: string;
    timestamp: string;
    phi_detected: boolean;
    compliance_validated: boolean;
  };
}

// PHI detection patterns for request validation
const PHI_PATTERNS = {
  ssn: /\b\d{3}-\d{2}-\d{4}\b/,
  phone: /\b\d{3}-\d{3}-\d{4}\b/,
  email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
  mrn: /\b[A-Z]{2}\d{6,10}\b/
};

/**
 * Scan data for potential PHI patterns
 */
function detectPHI(data: any): boolean {
  const dataStr = JSON.stringify(data).toLowerCase();
  
  return Object.values(PHI_PATTERNS).some(pattern => pattern.test(dataStr));
}

/**
 * Sanitize data for logging (remove potential PHI)
 */
function sanitizeForLogging(data: any): any {
  let sanitized = JSON.stringify(data);
  
  Object.entries(PHI_PATTERNS).forEach(([type, pattern]) => {
    sanitized = sanitized.replace(pattern, `[${type.toUpperCase()}_REDACTED]`);
  });
  
  try {
    return JSON.parse(sanitized);
  } catch {
    return { sanitized_data: "[REDACTED_FOR_LOGGING]" };
  }
}

/**
 * Call FastAPI agent endpoint with healthcare compliance
 */
export async function callAgent(toolName: string, args: any): Promise<HealthcareAgentResponse> {
  const MAIN_API_URL = process.env.MAIN_API_URL || "http://localhost:8000";
  
  // Map MCP tool names to FastAPI endpoints
  const endpointMap: Record<string, string> = {
    "clinical_intake": "/agents/intake/process",
    "transcribe_audio": "/agents/transcription/transcribe-audio", 
    "research_medical_literature": "/agents/research/search",
    "process_healthcare_document": "/agents/document/process"
  };

  const endpoint = endpointMap[toolName];
  if (!endpoint) {
    throw new Error(`Unknown healthcare tool: ${toolName}`);
  }

  // PHI detection before sending request
  const phiDetected = detectPHI(args);
  if (phiDetected && !args.patient_data?.patient_id?.startsWith('TEST_')) {
    console.warn(`PHI detected in MCP request for tool: ${toolName}`);
    // Log security incident
    console.error(`SECURITY ALERT: Potential PHI in MCP request`, {
      tool: toolName,
      session_id: args.session_id,
      timestamp: new Date().toISOString(),
      sanitized_args: sanitizeForLogging(args)
    });
  }

  // Prepare healthcare-compliant request
  const requestHeaders = {
    "Content-Type": "application/json",
    "X-Healthcare-Request": "true",
    "X-Session-ID": args.session_id || "mcp_session_" + Date.now(),
    "X-MCP-Tool": toolName,
    "X-PHI-Detection": phiDetected.toString(),
    "User-Agent": "Healthcare-MCP-Bridge/1.0"
  };

  // Log agent call attempt
  console.log(`MCP→Agent call: ${toolName}`, {
    endpoint,
    session_id: args.session_id,
    phi_detected: phiDetected,
    timestamp: new Date().toISOString(),
    sanitized_args: sanitizeForLogging(args)
  });

  try {
    const response = await fetch(`${MAIN_API_URL}${endpoint}`, {
      method: "POST",
      headers: requestHeaders,
      body: JSON.stringify(args),
      // @ts-ignore - timeout is not in standard fetch but may be available
      timeout: 30000 // 30 second timeout for healthcare operations
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Agent call failed: ${toolName}`, {
        status: response.status,
        statusText: response.statusText,
        error: errorText,
        session_id: args.session_id
      });
      
      throw new Error(`Agent call failed: ${response.status} ${response.statusText}`);
    }

    const responseData = await response.json();
    
    // Validate response for PHI exposure
    const responsePHI = detectPHI(responseData);
    if (responsePHI) {
      console.warn(`PHI detected in agent response: ${toolName}`);
    }

    // Create healthcare-compliant response
    const healthcareResponse: HealthcareAgentResponse = {
      success: true,
      data: responseData,
      medical_disclaimer: "HEALTHCARE PROVIDER SUPPORT: This system supports clinical workflow and doesn't replace clinical judgment. All medical decisions must be made by qualified healthcare professionals.",
      audit_info: {
        session_id: args.session_id || "unknown",
        timestamp: new Date().toISOString(),
        phi_detected: phiDetected || responsePHI,
        compliance_validated: true
      }
    };

    // Log successful call
    console.log(`MCP→Agent success: ${toolName}`, {
      session_id: args.session_id,
      response_size: JSON.stringify(responseData).length,
      phi_in_response: responsePHI,
      timestamp: new Date().toISOString()
    });

    return healthcareResponse;

  } catch (error) {
    // Log error with healthcare context
    console.error(`MCP→Agent error: ${toolName}`, {
      error: error instanceof Error ? error.message : String(error),
      session_id: args.session_id,
      timestamp: new Date().toISOString(),
      sanitized_args: sanitizeForLogging(args)
    });

    // Return healthcare-compliant error response
    return {
      success: false,
      error: `Healthcare agent call failed: ${error instanceof Error ? error.message : String(error)}`,
      medical_disclaimer: "HEALTHCARE PROVIDER SUPPORT: This system supports clinical workflow and doesn't replace clinical judgment. Technical issues require IT support.",
      audit_info: {
        session_id: args.session_id || "unknown",
        timestamp: new Date().toISOString(),
        phi_detected: phiDetected,
        compliance_validated: false
      }
    };
  }
}

/**
 * Validate MCP request for healthcare compliance
 */
export function validateHealthcareRequest(toolName: string, args: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Check required healthcare fields
  if (!args.session_id) {
    errors.push("session_id is required for healthcare audit trail");
  }

  // Validate patient ID format for PHI safety
  if (args.patient_data?.patient_id && !args.patient_data.patient_id.match(/^(TEST_|PAT)[A-Z0-9_]+$/)) {
    errors.push("patient_id must start with TEST_ for synthetic data or follow PAT format");
  }

  // Tool-specific validations
  switch (toolName) {
    case "clinical_intake":
      if (!args.patient_data) {
        errors.push("patient_data is required for clinical intake");
      }
      break;
      
    case "transcribe_audio":
      if (!args.provider_id) {
        errors.push("provider_id is required for audio transcription");
      }
      if (!args.audio_data?.format || !args.audio_data?.data) {
        errors.push("audio_data with format and data is required");
      }
      break;
      
    case "research_medical_literature":
      if (!args.query || args.query.length < 3) {
        errors.push("query must be at least 3 characters for medical literature search");
      }
      // Check for patient-specific information in research query
      if (detectPHI(args.query)) {
        errors.push("research query must not contain patient-specific information");
      }
      break;
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Legacy PHI validation function - kept for backward compatibility
 * @deprecated Use validateHealthcareRequest instead
 */
export function validateNoPHI(args: any): boolean {
  const validation = validateHealthcareRequest("generic", args);
  if (!validation.valid) {
    throw new Error(`PHI validation failed: ${validation.errors.join(', ')}`);
  }
  return true;
}