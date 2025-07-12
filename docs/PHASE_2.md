# Phase 2: Business Services and Personalization

**Duration:** 4-5 weeks  
**Goal:** Implement business-critical healthcare services (insurance, billing, compliance) and doctor-specific personalization through fine-tuning.

## Service Configuration Format

**All service configurations are compatible with the universal service runner.**

Service configuration files use lowercase keys that map directly to Docker arguments:
- `image=` - Docker image name (required)
- `port=` - Port mappings (e.g., "8080:80" or "8080:80 9090:90")
- `volumes=` - Volume mounts (e.g., "./data:/data ./config:/config:ro")
- `env=` - Environment variables (e.g., "VAR1=value1 VAR2=value2")
- `restart=` - Restart policy (e.g., "unless-stopped")
- `network=` - Docker network name
- `health_cmd=` - Health check command
- `memory_limit=` - Memory limit (e.g., "2g", "512m")
- `working_dir=` - Working directory inside container
- `command=` - Override container command

**Service names come from the CLI, not the config file:**
```bash
# Start a service by passing the service name as an argument
./universal-service-runner.sh insurance-verify /services/user/insurance-verify/insurance-verify.conf
```

**Notes on removed fields:**
- `NAME=` and `CONTAINER_NAME=` - Not needed (service name from CLI)
- `BUILD_CONTEXT=` - Handled separately by build system
- `DEPENDS_ON=` - Managed by orchestration layer

---

## Week 1: Business Infrastructure Services

### 1.1 Insurance Verification Service

**Insurance verification service (`/services/user/insurance-verify/insurance-verify.conf`):**
```bash
# Service: insurance-verify - Healthcare insurance verification and eligibility checking
image="python:3.11-slim"
# Note: Build context handled separately by build system
port="8003:8000"
volumes="./app:/app:rw"
env="FLASK_ENV=production REDIS_URL=redis://redis:6379"
restart="unless-stopped"
network="clinical-net"
# Note: Dependencies managed by orchestration layer
health_cmd="python /app/health_check.py"
memory_limit="1g"
working_dir="/app"
command="python server.py"
```

**Insurance verification server (`/services/user/insurance-verify/app/server.py`):**
```python
from flask import Flask, request, jsonify
import redis
import json
from datetime import datetime, timedelta
import requests
import logging

app = Flask(__name__)
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InsuranceVerificationEngine:
    """Healthcare insurance verification and eligibility checking"""
    
    def __init__(self):
        self.cache_duration = 3600  # 1 hour cache
        
    def verify_eligibility(self, member_id: str, provider_id: str, 
                         service_codes: list) -> dict:
        """Verify insurance eligibility for specific services"""
        
        # Check cache first
        cache_key = f"insurance:{member_id}:{provider_id}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for insurance verification: {member_id}")
            return json.loads(cached_result)
        
        # Simulate real-time eligibility check
        verification_result = {
            "member_id": member_id,
            "provider_id": provider_id,
            "verification_date": datetime.now().isoformat(),
            "eligibility_status": "active",
            "coverage_details": {
                "deductible_remaining": 1500.00,
                "copay_amount": 25.00,
                "out_of_pocket_max": 5000.00,
                "covered_services": service_codes
            },
            "authorization_required": self._check_authorization_required(service_codes),
            "effective_date": "2024-01-01",
            "termination_date": "2024-12-31"
        }
        
        # Cache the result
        redis_client.setex(cache_key, self.cache_duration, 
                          json.dumps(verification_result))
        
        logger.info(f"Insurance verified for member: {member_id}")
        return verification_result
    
    def _check_authorization_required(self, service_codes: list) -> bool:
        """Check if any services require prior authorization"""
        high_cost_procedures = ['99213', '99214', 'G0442', 'G0443']
        return any(code in high_cost_procedures for code in service_codes)

verification_engine = InsuranceVerificationEngine()

@app.route('/verify', methods=['POST'])
def verify_insurance():
    """Verify insurance eligibility endpoint"""
    try:
        data = request.get_json()
        
        required_fields = ['member_id', 'provider_id', 'service_codes']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        result = verification_engine.verify_eligibility(
            data['member_id'],
            data['provider_id'], 
            data['service_codes']
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Insurance verification error: {str(e)}")
        return jsonify({"error": "Verification failed"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        return jsonify({"status": "healthy", "service": "insurance-verify"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

### 1.2 Billing and Revenue Cycle Management

**Billing service configuration (`/services/user/billing/billing.conf`):**
```bash
# Service: billing - Healthcare billing and revenue cycle management
image="python:3.11-slim"
# Note: Build context handled separately by build system
port="8004:8000"
volumes="./app:/app:rw"
env="FLASK_ENV=production POSTGRES_URL=postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
restart="unless-stopped"
network="clinical-net"
# Note: Dependencies managed by orchestration layer
health_cmd="python /app/health_check.py"
memory_limit="1g"
working_dir="/app"
command="python billing_engine.py"
```

**Billing engine (`/services/user/billing/app/billing_engine.py`):**
```python
from flask import Flask, request, jsonify
import psycopg2
import json
from datetime import datetime, timedelta
import logging
import requests

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BillingEngine:
    """Healthcare billing and revenue cycle management"""
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
        )
        self.insurance_verify_url = "http://insurance-verify:8000"
        
    def create_claim(self, patient_data: dict, services: list) -> dict:
        """Create insurance claim for services rendered"""
        
        # Verify insurance eligibility first
        eligibility = self._verify_insurance_eligibility(
            patient_data.get('member_id'),
            patient_data.get('provider_id'),
            [service['code'] for service in services]
        )
        
        if not eligibility.get('eligibility_status') == 'active':
            return {"error": "Patient not eligible for coverage", "claim_id": None}
        
        # Calculate claim totals
        claim_total = sum(service.get('amount', 0) for service in services)
        patient_responsibility = self._calculate_patient_responsibility(
            claim_total, eligibility['coverage_details']
        )
        
        # Generate claim
        claim_data = {
            "claim_id": f"CLM{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "patient_id": patient_data['patient_id'],
            "provider_id": patient_data['provider_id'],
            "member_id": patient_data['member_id'],
            "service_date": datetime.now().isoformat(),
            "services": services,
            "claim_total": claim_total,
            "patient_responsibility": patient_responsibility,
            "insurance_responsibility": claim_total - patient_responsibility,
            "status": "submitted",
            "created_date": datetime.now().isoformat()
        }
        
        # Store claim in database
        self._store_claim(claim_data)
        
        logger.info(f"Claim created: {claim_data['claim_id']}")
        return claim_data
    
    def _verify_insurance_eligibility(self, member_id: str, provider_id: str, 
                                    service_codes: list) -> dict:
        """Verify insurance eligibility via insurance service"""
        try:
            response = requests.post(f"{self.insurance_verify_url}/verify", 
                                   json={
                                       "member_id": member_id,
                                       "provider_id": provider_id,
                                       "service_codes": service_codes
                                   })
            return response.json()
        except Exception as e:
            logger.error(f"Insurance verification failed: {str(e)}")
            return {"eligibility_status": "unknown"}
    
    def _calculate_patient_responsibility(self, claim_total: float, 
                                        coverage_details: dict) -> float:
        """Calculate patient's financial responsibility"""
        copay = coverage_details.get('copay_amount', 0)
        deductible_remaining = coverage_details.get('deductible_remaining', 0)
        
        # Simple calculation - enhance based on actual insurance rules
        patient_pays = min(copay + min(claim_total, deductible_remaining), claim_total)
        return round(patient_pays, 2)
    
    def _store_claim(self, claim_data: dict) -> None:
        """Store claim in database"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO claims (claim_id, patient_id, provider_id, member_id, 
                              service_date, claim_data, claim_total, 
                              patient_responsibility, status, created_date)
            VALUES (%(claim_id)s, %(patient_id)s, %(provider_id)s, %(member_id)s,
                   %(service_date)s, %(claim_data)s, %(claim_total)s,
                   %(patient_responsibility)s, %(status)s, %(created_date)s)
        """, {
            **claim_data,
            'claim_data': json.dumps(claim_data)
        })
        self.db_conn.commit()

billing_engine = BillingEngine()

@app.route('/create_claim', methods=['POST'])
def create_claim():
    """Create insurance claim endpoint"""
    try:
        data = request.get_json()
        
        required_fields = ['patient_data', 'services']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        result = billing_engine.create_claim(
            data['patient_data'],
            data['services']
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Billing error: {str(e)}")
        return jsonify({"error": "Billing failed"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        cursor = billing_engine.db_conn.cursor()
        cursor.execute("SELECT 1")
        return jsonify({"status": "healthy", "service": "billing"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

### 1.3 HIPAA Compliance and Audit Monitoring

**Compliance service configuration (`/services/user/compliance/compliance.conf`):**
```bash
# Service: compliance - HIPAA compliance monitoring and audit logging
image="python:3.11-slim"
# Note: Build context handled separately by build system
port="8005:8000"
volumes="./app:/app:rw"
env="FLASK_ENV=production POSTGRES_URL=postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
restart="unless-stopped"
network="clinical-net"
# Note: Dependencies managed by orchestration layer
health_cmd="python /app/health_check.py"
memory_limit="512m"
working_dir="/app"
command="python hipaa_monitor.py"
```

**HIPAA compliance monitor (`/services/user/compliance/app/hipaa_monitor.py`):**
```python
from flask import Flask, request, jsonify
import psycopg2
import json
from datetime import datetime, timedelta
import logging
import re

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HIPAAComplianceMonitor:
    """HIPAA compliance monitoring and audit logging"""
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
        )
        self.pii_patterns = {
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'phone': r'\b\d{3}-\d{3}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'date_of_birth': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'medical_record': r'\bMRN\s*:?\s*\d+\b'
        }
    
    def log_access_attempt(self, user_id: str, resource: str, 
                          action: str, success: bool, ip_address: str = None) -> dict:
        """Log all access attempts for HIPAA audit trail"""
        
        audit_entry = {
            "audit_id": f"AUD{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "ip_address": ip_address,
            "timestamp": datetime.now().isoformat(),
            "compliance_flags": self._check_compliance_flags(action, resource)
        }
        
        # Store audit log
        self._store_audit_log(audit_entry)
        
        # Check for suspicious activity
        if self._detect_suspicious_activity(user_id, action):
            self._trigger_security_alert(audit_entry)
        
        return audit_entry
    
    def scan_for_pii(self, content: str) -> dict:
        """Scan content for PII and flag violations"""
        violations = []
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                violations.append({
                    "type": pii_type,
                    "count": len(matches),
                    "severity": "high" if pii_type in ['ssn', 'medical_record'] else "medium"
                })
        
        return {
            "violations_found": len(violations) > 0,
            "violation_details": violations,
            "scan_timestamp": datetime.now().isoformat()
        }
    
    def _check_compliance_flags(self, action: str, resource: str) -> list:
        """Check for HIPAA compliance concerns"""
        flags = []
        
        if action in ['export', 'download'] and 'patient' in resource:
            flags.append("PHI_EXPORT")
        
        if action == 'bulk_access':
            flags.append("BULK_ACCESS")
        
        return flags
    
    def _detect_suspicious_activity(self, user_id: str, action: str) -> bool:
        """Detect potentially suspicious access patterns"""
        # Check recent access frequency
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM audit_log 
            WHERE user_id = %s 
            AND created_at > NOW() - INTERVAL '1 hour'
        """, (user_id,))
        
        recent_access_count = cursor.fetchone()[0]
        
        # Flag if more than 50 accesses in an hour
        return recent_access_count > 50
    
    def _trigger_security_alert(self, audit_entry: dict) -> None:
        """Trigger security alert for suspicious activity"""
        alert = {
            "alert_type": "SUSPICIOUS_ACTIVITY",
            "user_id": audit_entry['user_id'],
            "timestamp": audit_entry['timestamp'],
            "details": audit_entry
        }
        
        logger.warning(f"Security alert triggered: {json.dumps(alert)}")
        
        # Store security alert
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO security_alerts (alert_type, user_id, details, created_at)
            VALUES (%s, %s, %s, %s)
        """, (alert['alert_type'], alert['user_id'], 
              json.dumps(alert['details']), datetime.now()))
        self.db_conn.commit()
    
    def _store_audit_log(self, audit_entry: dict) -> None:
        """Store audit log entry"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (user_id, action, resource_type, details, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (audit_entry['user_id'], audit_entry['action'], 
              audit_entry['resource'], json.dumps(audit_entry), datetime.now()))
        self.db_conn.commit()

compliance_monitor = HIPAAComplianceMonitor()

@app.route('/log_access', methods=['POST'])
def log_access():
    """Log access attempt endpoint"""
    try:
        data = request.get_json()
        
        required_fields = ['user_id', 'resource', 'action', 'success']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        result = compliance_monitor.log_access_attempt(
            data['user_id'],
            data['resource'],
            data['action'],
            data['success'],
            data.get('ip_address')
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Compliance logging error: {str(e)}")
        return jsonify({"error": "Logging failed"}), 500

@app.route('/scan_pii', methods=['POST'])
def scan_pii():
    """Scan content for PII violations"""
    try:
        data = request.get_json()
        
        if 'content' not in data:
            return jsonify({"error": "Missing content field"}), 400
        
        result = compliance_monitor.scan_for_pii(data['content'])
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"PII scanning error: {str(e)}")
        return jsonify({"error": "Scanning failed"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        cursor = compliance_monitor.db_conn.cursor()
        cursor.execute("SELECT 1")
        return jsonify({"status": "healthy", "service": "compliance"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
```

## Week 2: Advanced MCP Tool Development 

### 2.1 Insurance Tool Framework from Action Plans

**Insurance Tool Base Class (`/services/user/agentcare-mcp/custom-tools/insurance-base.js`):**
```javascript
export class InsuranceTool {
  constructor(name, config) {
    this.name = name;
    this.config = config;
    this.auditLogger = new ComplianceLogger();
  }

  async checkEligibility(patientId, serviceCode) {
    // Log access (no PHI)
    await this.auditLogger.log({
      action: 'eligibility_check',
      tool: this.name,
      timestamp: new Date(),
      serviceCode: serviceCode
    });
    
    // Implementation per insurance provider
    throw new Error('Must implement in subclass');
  }

  async submitClaim(claimData) {
    // Sanitize and validate
    const sanitized = this.sanitizeClaimData(claimData);
    return this.submitToProvider(sanitized);
  }

  sanitizeClaimData(claimData) {
    // Remove any PII and validate structure
    const sanitized = { ...claimData };
    delete sanitized.ssn;
    delete sanitized.full_name;
    return sanitized;
  }
}
```

**Anthem/BCBS Tool (`/services/user/agentcare-mcp/custom-tools/anthem-tool.js`):**
```javascript
import { InsuranceTool } from './insurance-base.js';

export class AnthemTool extends InsuranceTool {
  constructor(config) {
    super('anthem-bcbs', config);
    this.availityClient = new AvailityAPI(config.availity);
  }

  async checkEligibility(patientId, serviceCode) {
    await super.checkEligibility(patientId, serviceCode);
    
    // Use Availity X12 270/271 transaction
    const request = this.buildX12Request(patientId, serviceCode);
    return await this.availityClient.submit270(request);
  }

  buildX12Request(patientId, serviceCode) {
    return {
      memberID: patientId,
      serviceTypeCode: serviceCode,
      providerID: this.config.providerID
    };
  }
}
```

**Generate MCP Tools using create-mcp-tool:**
```bash
# Inside the AgentCare-MCP container
cd /app/tools/custom

# Generate insurance tools
npx create-mcp-tool anthem-bcbs \
  --description "Anthem BCBS eligibility and claims verification" \
  --capabilities "eligibility,claims,authorization"

npx create-mcp-tool unitedhealthcare \
  --description "UnitedHealthcare eligibility and formulary lookup" \
  --capabilities "eligibility,claims,formulary"

npx create-mcp-tool cigna \
  --description "Cigna eligibility and prior authorization" \
  --capabilities "eligibility,claims,prior-auth"
```

### 2.2 CodeGen SDK for Rapid Tool Development

**Install and configure CodeGen SDK for accelerated insurance tool development:**

**Setup CodeGen development environment (`/services/user/codegen-dev/codegen-dev.conf`):**
```bash
# Service: codegen-dev - CodeGen SDK development environment
image="node:20"
port="3200:3200 9229:9229"
volumes="./workspace:/workspace ./specs:/specs ./output:/output"
env="NODE_ENV=development CODEGEN_API_KEY=${CODEGEN_API_KEY}"
command="tail -f /dev/null"
restart="unless-stopped"
network="clinical-net"
working_dir="/workspace"
memory_limit="2g"
```

**CodeGen SDK setup script (`/services/user/codegen-dev/setup-codegen.sh`):**
```bash
#!/bin/bash
# Install CodeGen SDK for rapid tool development
npm install -g @codegen/cli
npm install --save-dev @codegen/sdk

# Initialize CodeGen in the MCP tools directory
mkdir -p /workspace/generated-tools
cd /workspace
codegen init --framework mcp --language typescript
```

**Insurance API template (`/services/user/codegen-dev/templates/insurance-api.yaml`):**
```yaml
name: InsuranceAPITool
type: mcp-tool
description: Generate insurance integration tools
templates:
  - eligibility-check
  - claim-submission  
  - prior-authorization
  - formulary-lookup

providers:
  - name: anthem-bcbs
    api_style: rest
    auth: oauth2
    base_url: https://api.availity.com
    
  - name: unitedhealthcare
    api_style: soap
    auth: wsse
    base_url: https://api.optum.com
    
  - name: cigna
    api_style: rest
    auth: api_key
    base_url: https://api.cignaforhcp.com

generate:
  - models
  - clients
  - mcp-handlers
  - tests
  - documentation
```

**Automated tool generator (`/services/user/codegen-dev/generators/insurance-tool-generator.js`):**
```javascript
import { CodeGen } from '@codegen/sdk';

const generator = new CodeGen({
  outputDir: './generated-tools',
  framework: 'mcp',
  typescript: true
});

export async function generateInsuranceTool(providerConfig) {
  // Generate Anthem BCBS tool
  await generator.generate({
    template: 'insurance-api',
    provider: providerConfig.name,
    operations: [
      {
        name: 'checkEligibility',
        method: 'POST',
        endpoint: '/eligibility/v1/check',
        mcp: {
          description: 'Check patient insurance eligibility',
          parameters: {
            memberId: { type: 'string', required: true },
            serviceDate: { type: 'string', format: 'date' },
            cptCodes: { type: 'array', items: { type: 'string' } }
          }
        }
      },
      {
        name: 'submitClaim',
        method: 'POST', 
        endpoint: '/claims/v1/submit',
        mcp: {
          description: 'Submit insurance claim',
          parameters: {
            claim: { $ref: '#/definitions/ClaimData' }
          }
        }
      }
    ]
  });
}

// Rapid prototyping workflow
export async function prototypeNewTool(apiSpec, toolName) {
  const generator = new CodeGen();
  
  // Generate base tool structure
  const tool = await generator.createMCPTool({
    name: toolName,
    spec: apiSpec,
    includeTests: true,
    includeMocks: true
  });
  
  // Export to AgentCare-MCP
  await tool.export('./generated-tools/' + toolName);
  
  // Generate mock server for testing
  await generator.createMockServer({
    spec: apiSpec,
    port: 3100 + Math.floor(Math.random() * 100)
  });
}
```

**Development workflow for new insurance provider:**
```bash
# 1. Get API specification from new provider
curl https://new-insurance.com/api-spec > /workspace/specs/new-insurance.yaml

# 2. Generate MCP tool using CodeGen
docker exec codegen-dev codegen generate mcp-tool \
  --spec /specs/new-insurance.yaml \
  --name new-insurance \
  --output /output/

# 3. Copy generated tool to AgentCare-MCP
cp /services/user/codegen-dev/output/new-insurance.mcp.js \
   /services/user/agentcare-mcp/custom-tools/

# 4. Test with mock server
docker exec codegen-dev npm test new-insurance

# 5. Deploy to AgentCare-MCP
docker restart agentcare-mcp
```

**Auto-loader for generated tools (`/services/user/agentcare-mcp/src/auto-loader.js`):**
```javascript
import { readdirSync } from 'fs';
import { join } from 'path';

export async function loadGeneratedTools() {
  const toolsDir = './custom-tools/generated-tools';
  const tools = [];
  
  try {
    for (const file of readdirSync(toolsDir)) {
      if (file.endsWith('.mcp.js')) {
        const tool = await import(join(toolsDir, file));
        tools.push(tool.default);
        console.log(`Loaded generated tool: ${tool.default.name}`);
      }
    }
  } catch (error) {
    console.warn('No generated tools directory found, skipping auto-load');
  }
  
  return tools;
}
```

**Benefits of CodeGen SDK integration:**
- **Rapid Tool Development**: Generate boilerplate from API specs
- **MCP Compliance**: Automatic compliance checking
- **Freelance Efficiency**: Quick prototyping for client integrations
- **Consistency**: Standardized patterns across all tools
- **Testing**: Built-in test generation and mock servers

## Week 3: Secure Audio Pipeline (from Action Plans)

### 3.1 Windows Audio Client

**Directory:** `/clients/windows/intelluxe-audio-client/`

**main.py**
```python
import asyncio
import websockets
import pyaudio
import time
import json
from cryptography.fernet import Fernet

class IntelluxeAudioClient:
    def __init__(self, config):
        self.server_url = config['server_url']
        self.doctor_id = config['doctor_id']
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)
        
    async def stream_audio(self):
        """Stream encrypted audio to Ubuntu server"""
        
        # Audio configuration
        chunk = 1024
        format = pyaudio.paInt16
        channels = 1
        rate = 44100
        
        p = pyaudio.PyAudio()
        stream = p.open(format=format,
                       channels=channels,
                       rate=rate,
                       input=True,
                       frames_per_buffer=chunk)
        
        # Connect to server with authentication
        headers = {
            "Authorization": f"Bearer {self.doctor_id}",
            "X-Doctor-ID": self.doctor_id
        }
        
        async with websockets.connect(f"wss://{self.server_url}", 
                                     extra_headers=headers) as websocket:
            print(f"Connected to {self.server_url}")
            
            try:
                while True:
                    # Read audio data
                    data = stream.read(chunk)
                    
                    # Encrypt audio
                    encrypted_data = self.cipher.encrypt(data)
                    
                    # Send to server
                    message = {
                        "type": "audio",
                        "data": encrypted_data.hex(),
                        "timestamp": time.time(),
                        "doctor_id": self.doctor_id
                    }
                    
                    await websocket.send(json.dumps(message))
                    
                    # Brief pause to prevent overwhelming
                    await asyncio.sleep(0.1)
                    
            except KeyboardInterrupt:
                print("Stopping audio stream...")
            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

# Usage example:
if __name__ == "__main__":
    config = {
        "server_url": "clinic-server.local:8443",
        "doctor_id": "dr_smith",
        "encryption_key": "your_base64_key_here"
    }
    client = IntelluxeAudioClient(config)
    asyncio.run(client.stream_audio())
```

### 3.2 Ubuntu Audio Receiver & Transcription Service

**Directory:** `/services/user/audio-receiver/`

**audio-receiver.conf**
```bash
# Service: audio-receiver - Secure audio processing and transcription
image="audio-receiver:latest"
# Note: Build context handled separately by build system
port="8443:8443"
volumes="./certs:/app/certs:ro ./app:/app:rw"
env="NODE_ENV=production WHISPER_MODEL=large"
restart="unless-stopped"
network="clinical-net"
health_cmd="python /app/health_check.py"
memory_limit="6g"
tmpfs="/tmp:size=512M"
# Note: Dependencies managed by orchestration layer
```

**main.py (core logic for the receiver)**
```python
import asyncio
import websockets
import whisper
import json
import ssl
from cryptography.fernet import Fernet
import psycopg2
from datetime import datetime

# Per-doctor encryption keys (stored securely in production)
DOCTOR_KEYS = {
    "dr_smith": "BASE64_FERNET_KEY_1",
    "dr_jones": "BASE64_FERNET_KEY_2"
}

class AudioTranscriptionServer:
    def __init__(self):
        self.model = whisper.load_model("large")
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
        )
    
    async def handle_audio(self, websocket, path):
        """Handle incoming audio stream from Windows client"""
        doctor_id = None
        
        try:
            # Authenticate connection
            auth_header = websocket.request_headers.get("Authorization")
            doctor_id = websocket.request_headers.get("X-Doctor-ID")
            
            if not doctor_id or doctor_id not in DOCTOR_KEYS:
                await websocket.close(code=4001, reason="Authentication failed")
                return
            
            # Get encryption key for this doctor
            cipher = Fernet(DOCTOR_KEYS[doctor_id].encode())
            
            print(f"Audio session started for {doctor_id}")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data["type"] == "audio":
                        # Decrypt audio data
                        encrypted_data = bytes.fromhex(data["data"])
                        audio_data = cipher.decrypt(encrypted_data)
                        
                        # Transcribe audio (placeholder - implement actual transcription)
                        transcription = await self.transcribe_audio(audio_data)
                        
                        # Log transcription with compliance
                        await self.log_transcription(doctor_id, transcription)
                        
                        # Send transcription back to client
                        response = {
                            "type": "transcription",
                            "text": transcription,
                            "timestamp": datetime.now().isoformat(),
                            "confidence": 0.95  # Placeholder
                        }
                        
                        await websocket.send(json.dumps(response))
                        
                except Exception as e:
                    print(f"Error processing audio: {e}")
                    
        except Exception as e:
            print(f"WebSocket error for {doctor_id}: {e}")
    
    async def transcribe_audio(self, audio_data):
        """Transcribe audio using Whisper (simplified)"""
        # In production, implement proper audio processing
        return "Sample transcription text"
    
    async def log_transcription(self, doctor_id: str, transcription: str):
        """Log transcription for audit compliance"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (user_id, action, resource_type, details, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (doctor_id, "transcription", "audio_session", 
              json.dumps({"transcription_length": len(transcription)}), datetime.now()))
        self.db_conn.commit()

async def main():
    server = AudioTranscriptionServer();
    
    # SSL context for secure WebSocket
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);
    ssl_context.load_cert_chain("/app/certs/cert.pem", "/app/certs/key.pem");
    
    start_server = websockets.serve(
        server.handle_audio, "0.0.0.0", 8443, ssl=ssl_context
    );
    
    print("Audio transcription server starting on wss://0.0.0.0:8443");
    await start_server;

if __name__ == "__main__":
    asyncio.run(main());
```

## Week 4: Personalization Infrastructure

### 4.1 Training Data Collection

**Enhanced training data collection service (`core/training/data_collector.py`):**

_Enhancement: Model adapters in the database schema now include a `performance_metrics` JSONB field for tracking accuracy, latency, and user feedback. Agent router and plugin registry support performance tracking and recommendations for optimization. Summary and transcription plugins can be registered for doctor-specific documentation styles (e.g., SOAP notes, custom summaries)._
```python
from typing import Dict, Any, List
import json
from datetime import datetime
from pathlib import Path
import asyncio
import psycopg2

class TrainingDataCollector:
    """Collect and curate training data from user interactions"""
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@postgres:5432/intelluxe"
        )
        self.min_samples_for_training = 50
        
    async def collect_writing_sample(self, user_id: str, content: str, 
                                   content_type: str, metadata: Dict[str, Any]) -> None:
        """Collect user writing samples for future fine-tuning"""
        
        # Store in database for future training
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO user_writing_samples (
                user_id, content, content_type, metadata, created_at
            ) VALUES (%s, %s, %s, %s, %s)
        """, (user_id, content, content_type, json.dumps(metadata), datetime.now()))
        self.db_conn.commit()
        
        # Check if user has enough samples for training
        cursor.execute("""
            SELECT COUNT(*) FROM user_writing_samples WHERE user_id = %s
        """, (user_id,))
        sample_count = cursor.fetchone()[0]
        
        if sample_count >= self.min_samples_for_training:
            await self._mark_user_ready_for_training(user_id)
    
    async def _mark_user_ready_for_training(self, user_id: str) -> None:
        """Mark user as ready for personalization training"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            UPDATE user_preferences 
            SET preference_data = jsonb_set(
                COALESCE(preference_data, '{}'), 
                '{training_ready}', 
                'true'
            )
            WHERE user_id = %s AND preference_type = 'personalization'
        """, (user_id,))
        
        if cursor.rowcount == 0:
            # Insert new preference record
            cursor.execute("""
                INSERT INTO user_preferences (user_id, preference_type, preference_data)
                VALUES (%s, %s, %s)
            """, (user_id, 'personalization', json.dumps({"training_ready": True})))
        
        self.db_conn.commit()
    
    async def get_training_readiness(self, user_id: str) -> Dict[str, Any]:
        """Check if user is ready for personalization training"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM user_writing_samples WHERE user_id = %s
        """, (user_id,))
        sample_count = cursor.fetchone()[0]
        
        return {
            "user_id": user_id,
            "samples_collected": sample_count,
            "samples_needed": self.min_samples_for_training,
            "ready_for_training": sample_count >= self.min_samples_for_training,
            "completion_percentage": min(100, (sample_count / self.min_samples_for_training) * 100)
        }
```

### 4.2 Enhanced Database Schema for Business and Personalization

**Update PostgreSQL schema (`/services/user/postgres/init/02-business-schema.sql`):**
```sql
-- Business services tables
CREATE TABLE claims (
    claim_id VARCHAR(255) PRIMARY KEY,
    patient_id VARCHAR(255) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    member_id VARCHAR(255) NOT NULL,
    service_date TIMESTAMP WITH TIME ZONE NOT NULL,
    claim_data JSONB NOT NULL,
    claim_total DECIMAL(10,2) NOT NULL,
    patient_responsibility DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'submitted',
    created_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_date TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security alerts
CREATE TABLE security_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    details JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Insurance eligibility cache
CREATE TABLE insurance_eligibility (
    member_id VARCHAR(255),
    provider_id VARCHAR(255),
    eligibility_data JSONB NOT NULL,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    expiry_date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (member_id, provider_id)
);

-- User writing samples for personalization
CREATE TABLE user_writing_samples (
    sample_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User preferences (now with actual data)
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(255),
    preference_type VARCHAR(100),
    preference_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, preference_type)
);

-- Model adapters for personalization
CREATE TABLE IF NOT EXISTS model_adapters (
    adapter_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    base_model_id VARCHAR(255) NOT NULL,
    adapter_type VARCHAR(100) NOT NULL,
    model_path TEXT,
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT false
);

-- Convert time-series tables to hypertables
SELECT create_hypertable('security_alerts', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('user_writing_samples', 'created_at', if_not_exists => TRUE);

-- Business indexes
CREATE INDEX idx_claims_patient_id ON claims(patient_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_service_date ON claims(service_date);
CREATE INDEX idx_security_alerts_user_id ON security_alerts(user_id);
CREATE INDEX idx_insurance_eligibility_expiry ON insurance_eligibility(expiry_date);
CREATE INDEX idx_user_writing_samples_user_id ON user_writing_samples(user_id);
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_model_adapters_user_id ON model_adapters(user_id);
```

### 4.3 Agent Orchestration Preparation

**Extensible agent routing system for future multi-agent capabilities:**

_Configuration management supports feature toggling for advanced reasoning (Chain of Thought, Majority Voting, Tree of Thought)._

**Agent router configuration (`config/agent_routing.yml`):**
```yaml
# Configurable routing for future multi-agent capabilities
transcription:
  default: whisper_local
  sensitive: whisper_local
  non_sensitive: whisper_local  # Could use cloud in future
  voting_enabled: false  # Enable for critical transcripts
  voting_threshold: 3  # Number of transcribers for voting

post_processing:
  default: basic_formatter
  medical_reports: medical_formatter
  chain_of_thought: false  # Enable for complex reasoning
  tree_of_thought: false   # Enable for treatment planning

agent_selection:
  enabled: false  # Enable when multiple agents available
  selection_strategy: performance  # or 'cost', 'accuracy'
  
# Future orchestration capabilities (inspired by Motia)
orchestration:
  multi_agent_enabled: false
  task_routing_enabled: false
  memory_coordination: simple  # simple, distributed, advanced
  
# Advanced reasoning capabilities (inspired by research)
reasoning:
  chain_of_thought_enabled: false
  majority_voting_enabled: false
  tree_of_thought_enabled: false
  confidence_threshold: 0.85
```

**Extensible agent router (`core/orchestration/agent_router.py`):**
```python
from typing import Dict, Any, Optional, List
import yaml
import asyncio
from pathlib import Path
from core.plugins import plugin_registry

class AgentRouter:
    """Configurable router for future multi-agent orchestration (Motia-inspired)"""
    
    def __init__(self, config_path: str = "config/agent_routing.yml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.performance_metrics = {}
        
    def _load_config(self) -> Dict[str, Any]:
        """Load routing configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for basic operation"""
        return {
            'transcription': {'default': 'whisper_local'},
            'post_processing': {'default': 'basic_formatter'},
            'agent_selection': {'enabled': False},
            'orchestration': {'multi_agent_enabled': False},
            'reasoning': {'chain_of_thought_enabled': False}
        }
    
    async def route_transcription(self, audio_data: bytes, 
                                metadata: Dict[str, Any]) -> str:
        """Route to appropriate transcription service with future voting support"""
        sensitivity = metadata.get('sensitivity', 'sensitive')
        
        # Always use local for sensitive healthcare data
        if sensitivity == 'sensitive':
            service = self.config['transcription']['default']
        else:
            service = self.config['transcription'].get('non_sensitive', 'whisper_local')
        
        # Future: Add majority voting for critical transcripts
        if self.config['transcription'].get('voting_enabled'):
            return await self._majority_vote_transcription(audio_data, metadata)
        
        return await self._single_transcription(audio_data, service, metadata)
    
    async def route_processing(self, text: str, 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate post-processing with future CoT support"""
        content_type = metadata.get('content_type', 'general')
        
        # Select processor based on content type
        if content_type == 'medical_report':
            processor = self.config['post_processing'].get('medical_reports', 'basic_formatter')
        else:
            processor = self.config['post_processing']['default']
        
        # Future: Add Chain of Thought reasoning for complex tasks
        if (self.config['reasoning'].get('chain_of_thought_enabled') and 
            content_type in ['medical_diagnosis', 'treatment_plan']):
            return await self._process_with_chain_of_thought(text, processor, metadata)
        
        # Future: Add Tree of Thought for multiple treatment options
        if (self.config['reasoning'].get('tree_of_thought_enabled') and 
            content_type == 'treatment_options'):
            return await self._process_with_tree_of_thought(text, processor, metadata)
        
        return await self._single_processing(text, processor, metadata)
    
    async def route_agent_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route tasks to specialized agents (future multi-agent orchestration)"""
        task_type = task.get('type', 'general')
        
        if not self.config['orchestration'].get('multi_agent_enabled'):
            # Single agent mode - route to appropriate agent
            return await self._route_to_single_agent(task)
        
        # Future: Multi-agent orchestration (Motia-inspired)
        return await self._orchestrate_multi_agent_task(task)
    
    async def _single_transcription(self, audio_data: bytes, service: str,
                                  metadata: Dict[str, Any]) -> str:
        """Single transcription service"""
        transcriber = plugin_registry.transcribers.get(service)
        if not transcriber:
            raise ValueError(f"Transcriber {service} not found")
        
        result = await transcriber.transcribe(audio_data, metadata)
        
        # Track performance for future optimization (Opik-inspired)
        await self._track_performance(service, 'transcription', metadata, len(result))
        
        return result
    
    async def _single_processing(self, text: str, processor: str,
                               metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Single processing service"""
        processor_plugin = plugin_registry.processors.get(processor)
        if not processor_plugin:
            raise ValueError(f"Processor {processor} not found")
        
        result = await processor_plugin.process(text, metadata)
        
        # Track performance
        await self._track_performance(processor, 'processing', metadata, 
                                    result.get('confidence', 0))
        
        return result
    
    async def _majority_vote_transcription(self, audio_data: bytes,
                                         metadata: Dict[str, Any]) -> str:
        """Majority voting transcription (future implementation)"""
        # Future: Run multiple transcribers and vote on results
        # Useful for high-stakes medical transcriptions
        voting_threshold = self.config['transcription'].get('voting_threshold', 3)
        
        # For now, use single transcription
        # TODO: Implement actual voting when multiple transcribers available
        return await self._single_transcription(audio_data, 'whisper_local', metadata)
    
    async def _process_with_chain_of_thought(self, text: str, processor: str,
                                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Chain of Thought processing (future implementation)"""
        # Future: Step-by-step reasoning for complex medical tasks
        # Example: "First, identify symptoms... Then, consider differential diagnosis..."
        
        # For now, use regular processing
        # TODO: Implement CoT when advanced medical reasoning is needed
        result = await self._single_processing(text, processor, metadata)
        result['reasoning_type'] = 'chain_of_thought'
        result['reasoning_steps'] = []  # Future: Add reasoning steps
        
        return result
    
    async def _process_with_tree_of_thought(self, text: str, processor: str,
                                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Tree of Thought processing (future implementation)"""
        # Future: Explore multiple reasoning paths for treatment planning
        # Example: Branch out different treatment options, evaluate each
        
        # For now, use regular processing
        # TODO: Implement ToT when treatment planning features are needed
        result = await self._single_processing(text, processor, metadata)
        result['reasoning_type'] = 'tree_of_thought'
        result['explored_paths'] = []  # Future: Add explored reasoning paths
        
        return result
    
    async def _route_to_single_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route to single agent based on task type"""
        task_type = task.get('type', 'general')
        
        # Simple routing to existing agents
        agent_map = {
            'document_processing': 'document_processor',
            'medical_research': 'research_assistant',
            'insurance_verification': 'billing_helper',
            'scheduling': 'scheduling_optimizer'
        }
        
        agent_name = agent_map.get(task_type, 'intake')
        agent = plugin_registry.agents.get(agent_name)
        
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")
        
        return await agent.execute(task, task.get('context', {}))
    
    async def _orchestrate_multi_agent_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Multi-agent orchestration (future implementation - Motia-inspired)"""
        # Future: Coordinate multiple agents for complex workflows
        # Example: Document processing → Medical research → Insurance verification
        
        # For now, route to single agent
        # TODO: Implement when complex multi-agent workflows are needed
        return await self._route_to_single_agent(task)
    
    async def _track_performance(self, service: str, service_type: str,
                               metadata: Dict[str, Any], metric: float) -> None:
        """Track service performance for future optimization (Opik-inspired)"""
        if service not in self.performance_metrics:
            self.performance_metrics[service] = {
                'total_requests': 0,
                'average_performance': 0,
                'type': service_type
            }
        
        current = self.performance_metrics[service]
        current['total_requests'] += 1
        
        # Simple moving average
        current['average_performance'] = (
            (current['average_performance'] * (current['total_requests'] - 1) + metric) / 
            current['total_requests']
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for all services"""
        return {
            'performance_metrics': self.performance_metrics,
            'config': self.config,
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations (Opik-inspired)"""
        recommendations = []
        
        # Future: Analyze performance and suggest improvements
        # Example: "Consider enabling voting for transcription accuracy"
        
        return recommendations

# Global agent router
agent_router = AgentRouter()
```

**Future orchestration capabilities documentation:**
```markdown
# Agent Orchestration Roadmap

## Current Capabilities (Phase 2)
- Basic routing to appropriate services
- Performance tracking for optimization
- Configuration-driven service selection
- Plugin-based architecture for extensibility

## Future Capabilities (Phase 3+)

### Multi-Agent Orchestration (Motia-inspired)
- **Complex Workflow Coordination**: Chain document processing → research → billing
- **Agent Communication**: Shared memory and context between agents
- **Task Decomposition**: Break complex requests into agent-specific subtasks
- **Result Synthesis**: Combine outputs from multiple agents

### Advanced Reasoning (Research-inspired)
- **Chain of Thought**: Step-by-step reasoning for medical decisions
  - Use case: Complex diagnosis, treatment planning
  - Implementation: LLM prompting with reasoning steps
- **Majority Voting**: Multiple model consensus for critical outputs
  - Use case: High-stakes transcriptions, critical reports
  - Implementation: Run multiple agents, vote on results
- **Tree of Thought**: Explore multiple reasoning paths
  - Use case: Treatment option evaluation, clinical decision support
  - Implementation: Branch reasoning, evaluate paths, rank options

### Performance Optimization (Opik-inspired)
- **Automatic Agent Selection**: Choose best agent based on performance
- **A/B Testing**: Compare agent performance on similar tasks
- **Cost-Performance Optimization**: Balance accuracy vs computational cost
- **User-Specific Optimization**: Adapt to individual doctor preferences

## When to Enable These Features

### Enable Chain of Thought When:
- Adding clinical decision support
- Implementing SOAP note generation
- Building complex medical report analysis
- Need explainable AI reasoning

### Enable Majority Voting When:
- Transcribing critical medical conversations
- Processing high-stakes insurance claims
- Generating regulatory compliance reports
- Need maximum accuracy over speed

### Enable Multi-Agent Orchestration When:
- Workflow requires multiple specialized tools
- Building complex clinical automation
- Need coordination between different AI models
- Scaling beyond single-doctor practices

## Implementation Priority
1. **Phase 2**: Basic routing and performance tracking ✅
2. **Phase 3**: Advanced reasoning for clinical decision support
3. **Phase 4**: Multi-agent orchestration for complex workflows
4. **Phase 5**: Full optimization and agent selection automation
```
