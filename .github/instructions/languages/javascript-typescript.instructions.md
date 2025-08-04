# JavaScript/TypeScript Healthcare Instructions

## Purpose

Modern JavaScript and TypeScript development patterns for healthcare AI systems, emphasizing type safety, healthcare compliance, and integration with existing Python infrastructure.

## TypeScript-First Development

### Healthcare Type Safety Framework

```typescript
// ✅ CRITICAL: Healthcare data type definitions
interface PatientData {
  readonly patientId: string;
  readonly phi: PHIData;
  readonly nonPhi: NonPHIData;
  readonly encryptionMeta: EncryptionMetadata;
}

interface PHIData {
  readonly name: string;
  readonly dateOfBirth: Date;
  readonly ssn: string; // Encrypted in transit/storage
  readonly medicalRecordNumber: string;
}

interface NonPHIData {
  readonly appointmentPreferences: AppointmentPreference[];
  readonly communicationPreferences: CommunicationPreference[];
  readonly insuranceType: InsuranceType;
}

interface EncryptionMetadata {
  readonly encryptedFields: readonly string[];
  readonly encryptionAlgorithm: string;
  readonly keyRotationDate: Date;
}
```

### Healthcare-Specific ESLint Rules

```json
// .eslintrc.healthcare.json
{
  "extends": ["@typescript-eslint/recommended", "prettier"],
  "rules": {
    // Healthcare compliance rules
    "no-console": ["error", { "allow": ["warn", "error"] }],
    "no-eval": "error",
    "no-implied-eval": "error",

    // PHI protection rules
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/explicit-function-return-type": "error",
    "@typescript-eslint/strict-boolean-expressions": "error",

    // Healthcare-specific custom rules
    "healthcare/no-phi-in-logs": "error",
    "healthcare/require-encryption-metadata": "error",
    "healthcare/no-external-api-phi": "error"
  },
  "overrides": [
    {
      "files": ["**/*.healthcare.ts", "**/*.medical.ts"],
      "rules": {
        "healthcare/medical-disclaimer-required": "error"
      }
    }
  ]
}
```

## Healthcare Data Handling Patterns

### PHI-Safe Data Processing

```typescript
// ✅ CORRECT: PHI-aware data processing
import { createHash } from "crypto";
import { Logger } from "../core/logging";

class HealthcareDataProcessor {
  private readonly logger: Logger;

  constructor(logger: Logger) {
    this.logger = logger;
  }

  /**
   * Process patient data with PHI protection
   * HEALTHCARE PROVIDER SUPPORT: Supports clinical workflow, doesn't replace clinical judgment
   */
  public async processPatientData(
    patientData: PatientData,
  ): Promise<ProcessedPatientData> {
    // Hash PHI for logging
    const patientHash = this.hashPHI(patientData.patientId);

    this.logger.info("Processing patient data", {
      patientHash,
      dataTypes: Object.keys(patientData.nonPhi),
      timestamp: new Date().toISOString(),
    });

    try {
      const processed = await this.performProcessing(patientData);

      this.logger.info("Patient data processed successfully", {
        patientHash,
        processingDuration: performance.now(),
      });

      return processed;
    } catch (error) {
      this.logger.error("Patient data processing failed", {
        patientHash,
        error: error instanceof Error ? error.message : "Unknown error",
      });
      throw new HealthcareProcessingError("Data processing failed", {
        patientHash,
      });
    }
  }

  private hashPHI(phi: string): string {
    return createHash("sha256").update(phi).digest("hex").substring(0, 8);
  }

  private async performProcessing(
    data: PatientData,
  ): Promise<ProcessedPatientData> {
    // Implementation here - no PHI in processing logs
    return {} as ProcessedPatientData;
  }
}
```

### n8n Workflow Integration

```typescript
// ✅ CORRECT: n8n healthcare workflow patterns
interface N8nHealthcareWorkflowNode {
  readonly nodeType:
    | "patient-intake"
    | "insurance-verification"
    | "appointment-scheduling";
  readonly phiHandling: PHIHandlingLevel;
  readonly auditRequired: boolean;
}

enum PHIHandlingLevel {
  NONE = "none", // No PHI processing
  HASH_ONLY = "hash_only", // Only hashed PHI identifiers
  ENCRYPTED = "encrypted", // Encrypted PHI allowed
  FULL_PHI = "full_phi", // Full PHI access (restricted nodes)
}

class N8nHealthcareWorkflow {
  /**
   * Configure n8n workflow with healthcare compliance
   * HEALTHCARE PROVIDER SUPPORT: Automates administrative workflows
   */
  public configureWorkflow(
    nodes: N8nHealthcareWorkflowNode[],
  ): WorkflowConfiguration {
    const auditNodes = nodes.filter((node) => node.auditRequired);
    const phiNodes = nodes.filter(
      (node) => node.phiHandling !== PHIHandlingLevel.NONE,
    );

    return {
      workflow: this.buildWorkflow(nodes),
      auditConfiguration: this.configureAudit(auditNodes),
      phiProtection: this.configurePHIProtection(phiNodes),
      complianceMetadata: {
        hipaaCompliant: true,
        auditTrailEnabled: true,
        encryptionRequired: phiNodes.length > 0,
      },
    };
  }
}
```

## Healthcare JavaScript Patterns

### Browser-Based Healthcare UIs

```javascript
// ✅ CORRECT: Healthcare-compliant frontend patterns
class HealthcareDashboard {
  constructor(config) {
    this.config = config;
    this.logger = new HealthcareLogger(config.logging);
    this.dataProtection = new PHIProtection();
  }

  /**
   * Display patient summary with PHI protection
   * HEALTHCARE PROVIDER SUPPORT: Displays clinical data for provider decision support
   */
  async displayPatientSummary(patientId) {
    const patientHash = this.dataProtection.hashPHI(patientId);

    try {
      // Fetch only necessary data
      const summary = await this.fetchPatientSummary(patientId);

      // Render with PHI protection
      this.renderSummary(summary, { patientHash });

      this.logger.audit("Patient summary displayed", {
        patientHash,
        timestamp: new Date().toISOString(),
        userId: this.config.currentUser.id,
      });
    } catch (error) {
      this.logger.error("Failed to display patient summary", {
        patientHash,
        error: error.message,
      });

      this.showErrorMessage("Unable to load patient data. Please try again.");
    }
  }

  renderSummary(summary, context) {
    // Ensure no PHI in DOM attributes or console
    const sanitizedSummary = this.dataProtection.sanitizeForUI(summary);

    // Render using framework of choice (React, Vue, etc.)
    this.updateUI(sanitizedSummary, context);
  }
}
```

## Development Tooling Configuration

### Prettier Healthcare Configuration

```json
// .prettierrc.healthcare.json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "overrides": [
    {
      "files": ["*.healthcare.ts", "*.medical.ts"],
      "options": {
        "printWidth": 120,
        "plugins": ["prettier-plugin-healthcare-compliance"]
      }
    }
  ]
}
```

### Healthcare Testing Patterns

```typescript
// ✅ CORRECT: Healthcare-specific testing
import { describe, it, expect, beforeEach } from "vitest";
import { HealthcareDataProcessor } from "../healthcare-data-processor";
import { createMockPatientData, createMockLogger } from "../test-utils";

describe("HealthcareDataProcessor", () => {
  let processor: HealthcareDataProcessor;
  let mockLogger: MockLogger;

  beforeEach(() => {
    mockLogger = createMockLogger();
    processor = new HealthcareDataProcessor(mockLogger);
  });

  describe("PHI Protection", () => {
    it("should hash PHI identifiers in logs", async () => {
      const patientData = createMockPatientData({
        patientId: "PATIENT-123",
        phi: { name: "Test Patient" },
      });

      await processor.processPatientData(patientData);

      // Verify no raw PHI in logs
      const logEntries = mockLogger.getAllEntries();
      expect(logEntries).not.toContainPHI(["PATIENT-123", "Test Patient"]);

      // Verify hashed identifier present
      expect(logEntries).toContainHashedIdentifier();
    });

    it("should encrypt PHI in processing results", async () => {
      const patientData = createMockPatientData();
      const result = await processor.processPatientData(patientData);

      expect(result.encryptionMeta.encryptedFields).toContain("patientId");
      expect(result.phi).toBeEncrypted();
    });
  });

  describe("Healthcare Compliance", () => {
    it("should maintain audit trail", async () => {
      const patientData = createMockPatientData();
      await processor.processPatientData(patientData);

      expect(mockLogger.auditEntries).toHaveLength(1);
      expect(mockLogger.auditEntries[0]).toMatchObject({
        action: "patient_data_processed",
        timestamp: expect.any(String),
        patientHash: expect.stringMatching(/^[a-f0-9]{8}$/),
      });
    });
  });
});
```

## Package Management & Dependencies

### Healthcare-Specific Dependencies

```json
// package.json
{
  "name": "@intelluxe/healthcare-frontend",
  "dependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0",

    // Healthcare-specific utilities
    "crypto-js": "^4.1.1",
    "joi": "^17.9.0",
    "class-validator": "^0.14.0",

    // Logging and monitoring
    "winston": "^3.10.0",
    "pino": "^8.15.0"
  },
  "devDependencies": {
    // Healthcare testing
    "vitest": "^0.34.0",
    "@vitest/ui": "^0.34.0",

    // Healthcare linting
    "eslint": "^8.50.0",
    "@typescript-eslint/eslint-plugin": "^6.7.0",
    "eslint-plugin-healthcare": "file:./local-plugins/eslint-plugin-healthcare",

    // Healthcare formatting
    "prettier": "^3.0.0",
    "prettier-plugin-healthcare-compliance": "file:./local-plugins/prettier-healthcare"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "lint": "eslint . --ext .ts,.tsx --config .eslintrc.healthcare.json",
    "lint:fix": "eslint . --ext .ts,.tsx --config .eslintrc.healthcare.json --fix",
    "format": "prettier --write . --config .prettierrc.healthcare.json",
    "healthcare:audit": "npm audit && node scripts/healthcare-dependency-check.js"
  }
}
```

## Security & Compliance Integration

### Healthcare-Specific Security Headers

```typescript
// ✅ CORRECT: Healthcare security middleware
export function healthcareSecurityMiddleware() {
  return (req: Request, res: Response, next: NextFunction) => {
    // HIPAA-compliant security headers
    res.setHeader(
      "Strict-Transport-Security",
      "max-age=31536000; includeSubDomains",
    );
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-Frame-Options", "DENY");
    res.setHeader("X-XSS-Protection", "1; mode=block");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
    res.setHeader(
      "Content-Security-Policy",
      "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
    );

    // Healthcare-specific headers
    res.setHeader("X-Healthcare-Version", process.env.HEALTHCARE_API_VERSION);
    res.setHeader("X-PHI-Protected", "true");

    next();
  };
}
```

## Implementation Priorities

### Phase 1: Core JavaScript/TypeScript Infrastructure

1. **TypeScript configuration** with strict healthcare compliance rules
2. **ESLint healthcare plugin** for PHI protection validation
3. **Basic n8n workflow integration** for administrative tasks
4. **PHI-safe logging utilities** for frontend applications

### Phase 2: Advanced Healthcare Features

1. **Healthcare-specific React/Vue components** with built-in PHI protection
2. **Advanced n8n workflow patterns** for clinical workflow automation
3. **Real-time healthcare dashboards** with audit trail integration
4. **Healthcare data validation** and sanitization libraries

### Phase 3: Production Deployment

1. **Healthcare security middleware** for production environments
2. **Performance monitoring** with healthcare compliance metrics
3. **Advanced testing patterns** for healthcare JavaScript applications
4. **CI/CD integration** with healthcare-specific security scanning

---

**Healthcare Compliance Note**: All JavaScript/TypeScript development must maintain the same PHI protection and audit standards as the Python infrastructure, with particular attention to browser security and data handling.
