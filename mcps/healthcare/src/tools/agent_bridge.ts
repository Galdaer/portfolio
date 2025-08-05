/**
 * MCP-Agent Bridge Implementation
 * Connects MCP tools to FastAPI healthcare agents with PHI protection
 */

import { Tool } from "@modelcontextprotocol/sdk/types.js";

export const agentTools: Tool[] = [
  {
    name: "clinical_intake",
    description: "Process patient intake with AI assistance and PHI protection",
    inputSchema: {
      type: "object",
      properties: {
        patient_data: { 
          type: "object",
          description: "Patient data for intake processing (PHI-protected)"
        },
        intake_type: { 
          type: "string", 
          enum: ["new_patient", "follow_up", "emergency"],
          default: "new_patient"
        },
        session_id: { 
          type: "string",
          description: "Session identifier for audit tracking"
        }
      },
      required: ["patient_data", "session_id"]
    }
  },
  {
    name: "transcribe_audio",
    description: "Secure medical audio transcription with PHI scanning",
    inputSchema: {
      type: "object",
      properties: {
        audio_data: { 
          type: "object",
          description: "Audio data for transcription (memory-only processing)"
        },
        session_id: { 
          type: "string",
          description: "Session identifier for audit tracking"
        },
        doctor_id: { 
          type: "string",
          description: "Healthcare provider identifier"
        },
        encounter_type: {
          type: "string",
          enum: ["consultation", "dictation", "note_taking"],
          default: "consultation"
        }
      },
      required: ["audio_data", "session_id", "doctor_id"]
    }
  },
  {
    name: "research_medical_literature",
    description: "Search PubMed and clinical guidelines with evidence synthesis",
    inputSchema: {
      type: "object",
      properties: {
        query: { 
          type: "string",
          description: "Medical research query (no PHI allowed)"
        },
        max_results: { 
          type: "number", 
          default: 10,
          minimum: 1,
          maximum: 50
        },
        include_clinical_trials: { 
          type: "boolean", 
          default: true 
        },
        specialty_filter: {
          type: "string",
          description: "Medical specialty context for filtering results"
        },
        session_id: {
          type: "string",
          description: "Session identifier for audit tracking"
        }
      },
      required: ["query"]
    }
  }
];

/**
 * Call healthcare agent through FastAPI endpoint
 * @param toolName - Name of the tool to call
 * @param args - Arguments to pass to the agent
 * @returns Agent response with healthcare compliance
 */
export async function callAgent(toolName: string, args: any): Promise<any> {
  const MAIN_API_URL = process.env.MAIN_API_URL || "http://localhost:8000";
  
  const endpointMap: Record<string, string> = {
    "clinical_intake": "/agents/intake/process",
    "transcribe_audio": "/agents/transcription/transcribe-audio", 
    "research_medical_literature": "/agents/research/search"
  };

  const endpoint = endpointMap[toolName];
  if (!endpoint) {
    throw new Error(`Unknown healthcare tool: ${toolName}`);
  }

  try {
    console.log(`[MCP-Agent Bridge] Calling ${toolName} at ${MAIN_API_URL}${endpoint}`);
    
    const response = await fetch(`${MAIN_API_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Healthcare-Request": "true",
        "X-Session-ID": args.session_id || "unknown",
        "X-PHI-Protected": "true",
        "User-Agent": "Healthcare-MCP-Bridge/1.0.0"
      },
      body: JSON.stringify(args)
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Agent call failed: ${response.status} ${response.statusText} - ${error}`);
    }

    const result = await response.json();
    
    // Add healthcare compliance metadata
    return {
      ...result,
      _mcp_metadata: {
        tool_name: toolName,
        endpoint_called: endpoint,
        timestamp: new Date().toISOString(),
        phi_protected: true,
        medical_disclaimer: "This response provides healthcare administrative support only. It does not provide medical advice, diagnosis, or treatment recommendations."
      }
    };

  } catch (error) {
    console.error(`[MCP-Agent Bridge] Error calling agent ${toolName}:`, error);
    
    // Return healthcare-compliant error response
    return {
      error: true,
      message: `Healthcare agent ${toolName} encountered an error`,
      details: error instanceof Error ? error.message : "Unknown error",
      _mcp_metadata: {
        tool_name: toolName,
        endpoint_called: endpoint,
        timestamp: new Date().toISOString(),
        phi_protected: true,
        medical_disclaimer: "This system provides healthcare administrative support only."
      }
    };
  }
}

/**
 * Validate that arguments don't contain PHI patterns
 * @param args - Arguments to validate
 * @returns true if safe, throws error if PHI detected
 */
export function validateNoPHI(args: any): boolean {
  const phiPatterns = [
    /\b\d{3}-\d{2}-\d{4}\b/, // SSN pattern
    /\b\d{3}-\d{3}-\d{4}\b/, // Phone pattern  
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/ // Email pattern
  ];

  const argStr = JSON.stringify(args);
  
  for (const pattern of phiPatterns) {
    if (pattern.test(argStr)) {
      throw new Error("Potential PHI detected in arguments - request blocked for compliance");
    }
  }
  
  return true;
}