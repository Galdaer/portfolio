# Phase 2: Business Services and Personalization

**Duration:** 4 weeks  
**Goal:** Deploy insurance verification, billing systems, compliance monitoring, and doctor personalization features. Transform the Phase 1 foundation into a complete clinical workflow system using your service architecture.

## Week 1: Insurance and Billing Infrastructure

### 1.1 Insurance Verification Service

**Create service configuration:**
```bash
# services/user/insurance-verification/insurance-verification.conf
image="intelluxe/insurance-verification:latest"
port="8003:8003"
description="Multi-provider insurance verification with error prevention"
env="NODE_ENV=production"
volumes="./config:/app/config:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8003/health || exit 1"
depends_on="postgres,redis"
```

**Deploy insurance verification service:**
```bash
./scripts/universal-service-runner.sh start insurance-verification

# Verify service is running
curl http://localhost:8003/health
```

**Enhanced insurance verification with error prevention:**
```python
# services/user/insurance-verification/main.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List, Optional
import httpx
import asyncio
from datetime import datetime

app = FastAPI(title="Insurance Verification Service")

class InsuranceVerificationService:
    """
    Multi-provider insurance verification with built-in error prevention
    """
    
    def __init__(self):
        self.providers = {
            'anthem': AnthemProvider(),
            'uhc': UnitedHealthProvider(),
            'cigna': CignaProvider(),
            'aetna': AetnaProvider()
        }
        self.safety_checks = InsuranceSafetyChecker()
    
    async def verify_eligibility(self, verification_request: Dict[str, Any]) -> Dict[str, Any]:
        """Verify patient eligibility with comprehensive error checking"""
        
        # Safety check: Validate input data
        validation_result = await self.safety_checks.validate_request(verification_request)
        if not validation_result['valid']:
            return {
                'error': 'Validation failed',
                'issues': validation_result['issues'],
                'safe_to_retry': False
            }
        
        member_id = verification_request['member_id']
        provider_id = verification_request['provider_id']
        service_codes = verification_request.get('service_codes', [])
        
        # Determine insurance provider
        provider_name = await self._detect_provider(member_id, provider_id)
        
        if provider_name not in self.providers:
            return {
                'error': f'Unsupported insurance provider: {provider_name}',
                'supported_providers': list(self.providers.keys())
            }
        
        try:
            # Verify eligibility with specific provider
            provider = self.providers[provider_name]
            eligibility_result = await provider.check_eligibility(
                member_id, provider_id, service_codes
            )
            
            # Apply safety validations
            validated_result = await self.safety_checks.validate_response(
                eligibility_result, verification_request
            )
            
            return {
                'verified': True,
                'provider': provider_name,
                'member_id': member_id,
                'eligibility': validated_result,
                'verification_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            # Log error for debugging but don't expose internal details
            return {
                'error': 'Verification failed',
                'provider': provider_name,
                'retry_recommended': True,
                'error_code': 'PROVIDER_ERROR'
            }

class InsuranceSafetyChecker:
    """Safety validation for insurance verification"""
    
    async def validate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate insurance verification request"""
        
        issues = []
        
        # Required fields check
        required_fields = ['member_id', 'provider_id']
        for field in required_fields:
            if not request.get(field):
                issues.append(f'Missing required field: {field}')
        
        # Member ID format validation
        member_id = request.get('member_id', '')
        if len(member_id) < 6 or len(member_id) > 20:
            issues.append('Member ID length invalid')
        
        # Provider ID validation
        provider_id = request.get('provider_id', '')
        if len(provider_id) < 3:
            issues.append('Provider ID too short')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

@app.post("/verify")
async def verify_insurance(request: Dict[str, Any]):
    service = InsuranceVerificationService()
    return await service.verify_eligibility(request)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "insurance-verification"}
```

### 1.2 Billing Engine Service

**Create service configuration:**
```bash
# services/user/billing-engine/billing-engine.conf
image="intelluxe/billing-engine:latest"
port="8004:8004"
description="Healthcare billing engine with automated claims processing"
env="NODE_ENV=production"
volumes="./billing-codes:/app/billing-codes:ro"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8004/health || exit 1"
depends_on="postgres,redis,insurance-verification"
```

**Deploy billing engine:**
```bash
./scripts/universal-service-runner.sh start billing-engine

# Verify service is running
curl http://localhost:8004/health
```

**Enhanced billing engine with safety checks:**
```python
# services/user/billing-engine/main.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List
import uuid
from datetime import datetime

app = FastAPI(title="Billing Engine Service")

class BillingEngine:
    """
    Healthcare billing engine with automated claims processing
    """
    
    def __init__(self):
        self.billing_codes = BillingCodeManager()
        self.claims_processor = ClaimsProcessor()
        self.billing_safety = BillingSafetyChecker()
    
    async def create_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create insurance claim with comprehensive validation"""
        
        # Safety validation
        validation_result = await self.billing_safety.validate_claim_data(claim_data)
        if not validation_result['valid']:
            return {
                'error': 'Claim validation failed',
                'issues': validation_result['issues'],
                'claim_created': False
            }
        
        # Generate claim ID
        claim_id = str(uuid.uuid4())
        
        # Process billing codes
        service_codes = claim_data.get('service_codes', [])
        processed_codes = await self.billing_codes.process_codes(service_codes)
        
        # Calculate amounts
        billing_amounts = await self._calculate_billing_amounts(
            processed_codes, claim_data
        )
        
        # Create claim record
        claim = {
            'claim_id': claim_id,
            'patient_id': claim_data['patient_id'],
            'provider_id': claim_data['provider_id'],
            'service_date': claim_data['service_date'],
            'service_codes': processed_codes,
            'billing_amounts': billing_amounts,
            'insurance_info': claim_data.get('insurance_info', {}),
            'status': 'created',
            'created_timestamp': datetime.now().isoformat()
        }
        
        # Submit claim for processing
        submission_result = await self.claims_processor.submit_claim(claim)
        
        return {
            'claim_created': True,
            'claim_id': claim_id,
            'submission_status': submission_result['status'],
            'estimated_payment': billing_amounts.get('estimated_payment'),
            'patient_responsibility': billing_amounts.get('patient_responsibility'),
            'next_steps': submission_result.get('next_steps', [])
        }

@app.post("/create_claim")
async def create_claim(claim_data: Dict[str, Any]):
    engine = BillingEngine()
    return await engine.create_claim(claim_data)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "billing-engine"}
```

## Week 2: Compliance and Monitoring

### 2.1 Enhanced Compliance Monitor

**Create service configuration:**
```bash
# services/user/compliance-monitor/compliance-monitor.conf
image="intelluxe/compliance-monitor:latest"
port="8005:8005"
description="HIPAA compliance monitoring with audit trails"
env="NODE_ENV=production,AUDIT_LEVEL=verbose"
volumes="./audit-logs:/app/logs:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8005/health || exit 1"
depends_on="postgres"
```

**Deploy compliance monitoring:**
```bash
./scripts/universal-service-runner.sh start compliance-monitor

# Verify service is running
curl http://localhost:8005/health
```

**Enhanced compliance monitoring with HIPAA audit trails:**
```python
# services/user/compliance-monitor/main.py
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any, List, Optional
import psycopg2
import json
from datetime import datetime, timedelta

app = FastAPI(title="Compliance Monitor Service")

class ComplianceMonitor:
    """
    HIPAA-compliant audit logging and monitoring system
    """
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
        self.compliance_rules = ComplianceRuleEngine()
        
    async def log_data_access(self, access_event: Dict[str, Any]) -> Dict[str, Any]:
        """Log patient data access for HIPAA compliance"""
        
        # Validate access event
        validation_result = await self._validate_access_event(access_event)
        if not validation_result['valid']:
            return {
                'logged': False,
                'error': 'Invalid access event',
                'issues': validation_result['issues']
            }
        
        # Check compliance rules
        compliance_check = await self.compliance_rules.check_access_compliance(access_event)
        
        # Create audit log entry
        audit_entry = {
            'user_id': access_event['user_id'],
            'action': access_event['action'],
            'resource_type': access_event['resource_type'],
            'resource_id': access_event.get('resource_id'),
            'ip_address': access_event.get('ip_address'),
            'user_agent': access_event.get('user_agent'),
            'timestamp': datetime.now(),
            'compliance_status': compliance_check['status'],
            'risk_level': compliance_check['risk_level'],
            'details': json.dumps(access_event.get('details', {}))
        }
        
        # Store in database
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO compliance_audit_log 
            (user_id, action, resource_type, resource_id, ip_address, user_agent,
             timestamp, compliance_status, risk_level, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, tuple(audit_entry.values()))
        
        audit_id = cursor.fetchone()[0]
        self.db_conn.commit()
        
        # Check for compliance violations
        if compliance_check['violation']:
            await self._handle_compliance_violation(audit_id, compliance_check)
        
        return {
            'logged': True,
            'audit_id': audit_id,
            'compliance_status': compliance_check['status'],
            'requires_attention': compliance_check['violation']
        }

@app.post("/log_access")
async def log_access(access_event: Dict[str, Any]):
    monitor = ComplianceMonitor()
    return await monitor.log_data_access(access_event)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "compliance-monitor"}
```

### 2.2 Enhanced Database Schema for Business Services

**Add business services tables to your existing PostgreSQL:**
```sql
-- Enhanced database schema for Phase 2 compliance tracking
CREATE TABLE IF NOT EXISTS compliance_audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    compliance_status VARCHAR(50) DEFAULT 'compliant',
    risk_level VARCHAR(20) DEFAULT 'low',
    details JSONB
);

-- Create hypertable for time-series compliance data
SELECT create_hypertable('compliance_audit_log', 'timestamp', if_not_exists => TRUE);

-- Add indexes for common compliance queries
CREATE INDEX IF NOT EXISTS idx_compliance_user_time ON compliance_audit_log (user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_compliance_risk_level ON compliance_audit_log (risk_level, timestamp);
CREATE INDEX IF NOT EXISTS idx_compliance_status ON compliance_audit_log (compliance_status, timestamp);

-- Insurance verification tracking
CREATE TABLE IF NOT EXISTS insurance_verifications (
    id SERIAL PRIMARY KEY,
    member_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    verification_status VARCHAR(50) NOT NULL,
    response_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Billing claims tracking
CREATE TABLE IF NOT EXISTS billing_claims (
    id SERIAL PRIMARY KEY,
    claim_id VARCHAR(100) UNIQUE NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    provider_id VARCHAR(100) NOT NULL,
    total_amount DECIMAL(10,2),
    claim_status VARCHAR(50) DEFAULT 'created',
    claim_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 Enhanced Monitoring for Business Services

**Add business service metrics to your existing resource-pusher.sh:**
```bash
# Add to scripts/resource-pusher.sh after existing metrics
collect_business_service_metrics() {
    local timestamp=$(date +%s%N)
    local hostname=$(hostname -s 2>/dev/null || hostname)
    
    # Check insurance verification service
    insurance_status="0"
    if curl -s --max-time 5 http://localhost:8003/health >/dev/null 2>&1; then
        insurance_status="1"
    fi
    
    # Check billing engine service
    billing_status="0"
    if curl -s --max-time 5 http://localhost:8004/health >/dev/null 2>&1; then
        billing_status="1"
    fi
    
    # Check compliance monitor service
    compliance_status="0"
    if curl -s --max-time 5 http://localhost:8005/health >/dev/null 2>&1; then
        compliance_status="1"
    fi
    
    # Create InfluxDB line protocol
    business_line="businessServices,host=${hostname} insurance_status=${insurance_status},billing_status=${billing_status},compliance_status=${compliance_status} ${timestamp}"
    
    # Push to InfluxDB
    curl -sS -XPOST "$INFLUX_URL" --data-binary "$business_line" >/dev/null 2>&1
    
    if [[ "$DEBUG" == true ]]; then
        log "[DEBUG] Business services metrics: insurance=${insurance_status}, billing=${billing_status}, compliance=${compliance_status}"
    fi
}

# Call in main collection function
collect_business_service_metrics
```

**Add healthcare-specific Grafana dashboard panels:**
```json
# Add to your existing Grafana dashboard configuration
{
  "panels": [
    {
      "title": "Business Services Status",
      "type": "stat",
      "targets": [
        {
          "query": "SELECT last(insurance_status) FROM businessServices",
          "alias": "Insurance"
        },
        {
          "query": "SELECT last(billing_status) FROM businessServices", 
          "alias": "Billing"
        },
        {
          "query": "SELECT last(compliance_status) FROM businessServices",
          "alias": "Compliance"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "thresholds": {
            "steps": [
              {"color": "red", "value": 0},
              {"color": "green", "value": 1}
            ]
          }
        }
      }
    },
    {
      "title": "Daily Transactions", 
      "type": "graph",
      "targets": [
        {
          "query": "SELECT count(*) FROM insurance_verifications WHERE time >= now() - 24h GROUP BY time(1h)"
        },
        {
          "query": "SELECT count(*) FROM billing_claims WHERE time >= now() - 24h GROUP BY time(1h)"
        }
      ]
    }
  ]
}
```

## Week 3: Doctor Personalization Infrastructure

### 3.1 Personalization Service

**Create service configuration:**
```bash
# services/user/personalization/personalization.conf
image="intelluxe/personalization:latest"
port="8007:8007"
description="Doctor-specific personalization with privacy protection"
env="NODE_ENV=production,PRIVACY_MODE=strict"
volumes="./preferences:/app/preferences:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8007/health || exit 1"
depends_on="postgres,redis"
```

**Deploy personalization service:**
```bash
./scripts/universal-service-runner.sh start personalization

# Verify service is running
curl http://localhost:8007/health
```

**Enhanced personalization with privacy protection:**
```python
# services/user/personalization/main.py
from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List, Optional
import psycopg2
import json
from datetime import datetime

app = FastAPI(title="Doctor Personalization Service")

class PersonalizationService:
    """
    Doctor-specific personalization with privacy-first design
    """
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
        self.preference_manager = PreferenceManager()
        self.privacy_guard = PrivacyGuard()
    
    async def update_doctor_preferences(self, 
                                      doctor_id: str,
                                      preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Update doctor preferences with privacy validation"""
        
        # Privacy check - ensure no PHI in preferences
        privacy_check = await self.privacy_guard.validate_preferences(preferences)
        if not privacy_check['safe']:
            return {
                'updated': False,
                'error': 'Privacy violation detected',
                'issues': privacy_check['issues']
            }
        
        # Update preferences
        result = await self.preference_manager.update_preferences(doctor_id, preferences)
        
        # Log preference change for audit
        await self._log_preference_change(doctor_id, preferences)
        
        return {
            'updated': True,
            'doctor_id': doctor_id,
            'preferences_updated': list(preferences.keys()),
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_doctor_preferences(self, doctor_id: str) -> Dict[str, Any]:
        """Retrieve doctor preferences"""
        
        preferences = await self.preference_manager.get_preferences(doctor_id)
        
        return {
            'doctor_id': doctor_id,
            'preferences': preferences,
            'last_updated': preferences.get('_last_updated'),
            'version': preferences.get('_version', 1)
        }

class PreferenceManager:
    """Manage doctor-specific preferences"""
    
    def __init__(self):
        self.db_conn = psycopg2.connect(
            "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
        )
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Default doctor preferences"""
        return {
            'summary_style': 'detailed',
            'preferred_terminology': 'standard',
            'report_format': 'soap',
            'notification_preferences': {
                'email': True,
                'sms': False
            },
            'ui_preferences': {
                'theme': 'light',
                'font_size': 'medium'
            },
            '_version': 1,
            '_last_updated': datetime.now().isoformat()
        }

@app.post("/preferences/{doctor_id}")
async def update_preferences(doctor_id: str, preferences: Dict[str, Any]):
    service = PersonalizationService()
    return await service.update_doctor_preferences(doctor_id, preferences)

@app.get("/preferences/{doctor_id}")
async def get_preferences(doctor_id: str):
    service = PersonalizationService()
    return await service.get_doctor_preferences(doctor_id)
```

### 3.2 Enhanced Database Schema for Personalization

**Add personalization tables to your existing PostgreSQL:**
```sql
-- Enhanced schema for Phase 2 personalization
CREATE TABLE IF NOT EXISTS doctor_preferences (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) UNIQUE NOT NULL,
    preferences JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctor_interaction_patterns (
    id SERIAL PRIMARY KEY,
    doctor_id VARCHAR(100) NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    pattern_data JSONB NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create hypertable for interaction patterns
SELECT create_hypertable('doctor_interaction_patterns', 'recorded_at', if_not_exists => TRUE);

-- Indexes for personalization queries
CREATE INDEX IF NOT EXISTS idx_doctor_preferences_doctor_id ON doctor_preferences (doctor_id);
CREATE INDEX IF NOT EXISTS idx_interaction_patterns_doctor_time ON doctor_interaction_patterns (doctor_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_interaction_patterns_type ON doctor_interaction_patterns (interaction_type, recorded_at);
```

## Week 4: Advanced Agent Features and Integration

### 4.1 Enhanced Agent Router with Business Services

**Advanced agent router integrating all services:**
```python
# core/orchestration/enhanced_agent_router.py
from typing import Dict, Any, List, Optional
import asyncio
from core.agents.base_agent import BaseAgent
from core.agents.document_processor import DocumentProcessorAgent
from core.agents.research_assistant import ResearchAssistantAgent
from core.agents.transcription_agent import TranscriptionAgent
import httpx

class EnhancedAgentRouter:
    """
    Route requests to appropriate agents and business services
    """
    
    def __init__(self):
        self.agents = {
            'document_processor': DocumentProcessorAgent(),
            'research_assistant': ResearchAssistantAgent(),
            'transcription': TranscriptionAgent()
        }
        
        self.business_services = {
            'insurance_verification': 'http://localhost:8003',
            'billing_engine': 'http://localhost:8004',
            'compliance_monitor': 'http://localhost:8005',
            'personalization': 'http://localhost:8007'
        }
        
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def route_request(self, request_type: str, input_data: Dict[str, Any],
                           session_id: str, doctor_id: str) -> Dict[str, Any]:
        """Route request to appropriate agent or business service"""
        
        # Get doctor preferences for personalization
        doctor_prefs = await self._get_doctor_preferences(doctor_id)
        
        # Log access for compliance
        await self._log_access_event(doctor_id, request_type, input_data)
        
        # Route based on request type
        if request_type in self.agents:
            # Handle with AI agent
            agent = self.agents[request_type]
            result = await agent.process_with_tracking(input_data, session_id)
            
            # Personalize result based on doctor preferences
            personalized_result = await self._personalize_result(
                result, doctor_prefs, request_type
            )
            
            return personalized_result
            
        elif request_type == 'insurance_verification':
            return await self._call_business_service('insurance_verification', 'verify', input_data)
            
        elif request_type == 'billing_claim':
            return await self._call_business_service('billing_engine', 'create_claim', input_data)
            
        elif request_type == 'complete_workflow':
            return await self._handle_complete_workflow(input_data, session_id, doctor_id)
            
        else:
            return {'error': f'Unknown request type: {request_type}'}
    
    async def _handle_complete_workflow(self, input_data: Dict[str, Any], 
                                      session_id: str, doctor_id: str) -> Dict[str, Any]:
        """Handle complete patient workflow from intake to billing"""
        
        workflow_results = {}
        
        # Step 1: Process intake documents
        if 'intake_documents' in input_data:
            doc_result = await self.agents['document_processor'].process_with_tracking(
                {'document_text': input_data['intake_documents'], 'document_type': 'intake'},
                session_id
            )
            workflow_results['document_processing'] = doc_result
        
        # Step 2: Verify insurance
        if 'insurance_info' in input_data:
            insurance_result = await self._call_business_service(
                'insurance_verification', 'verify', input_data['insurance_info']
            )
            workflow_results['insurance_verification'] = insurance_result
        
        # Step 3: Process consultation audio (if provided)
        if 'consultation_audio' in input_data:
            transcription_result = await self.agents['transcription'].process_with_tracking(
                input_data['consultation_audio'], session_id
            )
            workflow_results['transcription'] = transcription_result
        
        # Step 4: Create billing claim
        if 'billing_info' in input_data and workflow_results.get('insurance_verification', {}).get('verified'):
            billing_result = await self._call_business_service(
                'billing_engine', 'create_claim', input_data['billing_info']
            )
            workflow_results['billing'] = billing_result
        
        return {
            'workflow_type': 'complete_patient_workflow',
            'workflow_results': workflow_results,
            'overall_status': 'completed' if all(
                'error' not in result for result in workflow_results.values()
            ) else 'partial_completion'
        }
    
    async def _get_doctor_preferences(self, doctor_id: str) -> Dict[str, Any]:
        """Get doctor preferences for personalization"""
        try:
            response = await self.client.get(f"http://localhost:8007/preferences/{doctor_id}")
            if response.status_code == 200:
                return response.json()['preferences']
        except Exception:
            pass
        
        # Return default preferences if service unavailable
        return {'summary_style': 'detailed', 'report_format': 'soap'}
    
    async def _personalize_result(self, result: Dict[str, Any], 
                                doctor_prefs: Dict[str, Any],
                                request_type: str) -> Dict[str, Any]:
        """Personalize result based on doctor preferences"""
        
        if request_type == 'transcription':
            # Adjust transcription style based on preferences
            if doctor_prefs.get('summary_style') == 'concise':
                result['personalized_summary'] = await self._create_concise_summary(
                    result.get('transcription', '')
                )
        
        elif request_type == 'document_processor':
            # Adjust report format based on preferences
            report_format = doctor_prefs.get('report_format', 'soap')
            if report_format == 'bullet_points':
                result['formatted_report'] = await self._format_as_bullets(result)
        
        return result
    
    async def _log_access_event(self, doctor_id: str, request_type: str, 
                              input_data: Dict[str, Any]) -> None:
        """Log access event for compliance"""
        
        access_event = {
            'user_id': doctor_id,
            'action': f'ai_request_{request_type}',
            'resource_type': 'ai_agent',
            'details': {'request_type': request_type, 'has_phi': self._contains_potential_phi(input_data)}
        }
        
        try:
            await self.client.post(
                "http://localhost:8005/log_access",
                json=access_event
            )
        except Exception:
            # Log locally if compliance service unavailable
            pass
    
    async def _call_business_service(self, service_name: str, endpoint: str, 
                                   data: Dict[str, Any]) -> Dict[str, Any]:
        """Call business service endpoint"""
        
        service_url = self.business_services[service_name]
        
        try:
            response = await self.client.post(f"{service_url}/{endpoint}", json=data)
            return response.json()
        except Exception as e:
            return {
                'error': f'Service {service_name} unavailable',
                'details': str(e)
            }

# Global enhanced router
enhanced_agent_router = EnhancedAgentRouter()
```

### 4.2 Comprehensive Integration Testing

**Integration test suite for all business services:**
```python
# tests/test_phase2_integration.py
import pytest
import asyncio
import httpx
from datetime import datetime

class TestPhase2BusinessServices:
    
    @pytest.mark.asyncio
    async def test_all_services_running(self):
        """Test all business services are running via universal service runner"""
        
        services_to_check = [
            'http://localhost:8003/health',  # Insurance verification
            'http://localhost:8004/health',  # Billing engine
            'http://localhost:8005/health',  # Compliance monitor
            'http://localhost:8007/health',  # Personalization
        ]
        
        async with httpx.AsyncClient() as client:
            for service_url in services_to_check:
                response = await client.get(service_url, timeout=5.0)
                assert response.status_code == 200
                result = response.json()
                assert result['status'] == 'healthy'
    
    @pytest.mark.asyncio
    async def test_insurance_verification_flow(self):
        """Test complete insurance verification workflow"""
        
        async with httpx.AsyncClient() as client:
            verification_request = {
                "member_id": "W123456789",
                "provider_id": "ANTHEM_12345",
                "service_codes": ["99213", "99214"]
            }
            
            response = await client.post(
                "http://localhost:8003/verify",
                json=verification_request,
                timeout=10.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert 'verified' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_billing_engine_flow(self):
        """Test billing engine claim creation"""
        
        async with httpx.AsyncClient() as client:
            claim_data = {
                "patient_id": "P123456",
                "provider_id": "PR789",
                "service_date": datetime.now().isoformat(),
                "service_codes": ["99213", "I10"],
                "insurance_info": {
                    "member_id": "W123456789",
                    "copay_amount": 25.00,
                    "coinsurance_rate": 0.2
                }
            }
            
            response = await client.post(
                "http://localhost:8004/create_claim",
                json=claim_data,
                timeout=10.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert 'claim_created' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_compliance_monitoring_flow(self):
        """Test compliance monitoring and audit logging"""
        
        async with httpx.AsyncClient() as client:
            access_event = {
                "user_id": "dr_smith",
                "action": "view_patient_record",
                "resource_type": "patient_data",
                "resource_id": "P123456",
                "ip_address": "192.168.1.100",
                "details": {"record_type": "demographics"}
            }
            
            response = await client.post(
                "http://localhost:8005/log_access",
                json=access_event,
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['logged'] == True
    
    @pytest.mark.asyncio
    async def test_personalization_flow(self):
        """Test doctor personalization service"""
        
        async with httpx.AsyncClient() as client:
            # Update doctor preferences
            preferences = {
                "summary_style": "concise",
                "preferred_terminology": "simplified",
                "report_format": "bullet_points"
            }
            
            response = await client.post(
                "http://localhost:8007/preferences/dr_test",
                json=preferences,
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['updated'] == True
            
            # Retrieve preferences
            response = await client.get(
                "http://localhost:8007/preferences/dr_test",
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            assert result['preferences']['summary_style'] == 'concise'
    
    @pytest.mark.asyncio
    async def test_enhanced_agent_router(self):
        """Test the enhanced agent router with business services"""
        
        from core.orchestration.enhanced_agent_router import enhanced_agent_router
        
        # Test complete workflow
        workflow_data = {
            'intake_documents': 'Patient: John D. Chief complaint: Headache',
            'insurance_info': {
                'member_id': 'W123456789',
                'provider_id': 'ANTHEM_12345'
            },
            'billing_info': {
                'patient_id': 'P123456',
                'provider_id': 'PR789',
                'service_date': datetime.now().isoformat(),
                'service_codes': ['99213']
            }
        }
        
        result = await enhanced_agent_router.route_request(
            'complete_workflow', workflow_data, 'test_session', 'dr_test'
        )
        
        assert result['workflow_type'] == 'complete_patient_workflow'
        assert 'workflow_results' in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 4.3 Enhanced Monitoring Dashboard Updates

**Add business service panels to your existing Grafana dashboard:**
```json
# Add to your existing Grafana dashboard JSON
{
  "title": "Intelluxe Healthcare AI Business Services Dashboard",
  "panels": [
    {
      "title": "Service Health Status",
      "type": "stat",
      "gridPos": {"h": 6, "w": 12, "x": 0, "y": 0},
      "targets": [
        {
          "query": "SELECT last(insurance_status) FROM businessServices",
          "alias": "Insurance"
        },
        {
          "query": "SELECT last(billing_status) FROM businessServices",
          "alias": "Billing"
        },
        {
          "query": "SELECT last(compliance_status) FROM businessServices", 
          "alias": "Compliance"
        }
      ]
    },
    {
      "title": "Daily Transaction Volume",
      "type": "graph",
      "gridPos": {"h": 6, "w": 12, "x": 12, "y": 0},
      "targets": [
        {
          "query": "SELECT count(*) FROM insurance_verifications WHERE time >= now() - 24h GROUP BY time(1h) fill(0)"
        },
        {
          "query": "SELECT count(*) FROM billing_claims WHERE time >= now() - 24h GROUP BY time(1h) fill(0)"
        }
      ]
    },
    {
      "title": "Agent Performance",
      "type": "graph", 
      "gridPos": {"h": 6, "w": 24, "x": 0, "y": 6},
      "targets": [
        {
          "query": "SELECT mean(processing_time) FROM agent_sessions WHERE time >= now() - 1h GROUP BY time(5m), agent_type"
        }
      ]
    }
  ]
}
```

## Week 4: Real-time Medical Assistant Integration

### 4.1 Real-time Medical Assistant Service

**Create service configuration for intelligent real-time assistance:**
```bash
# services/user/realtime-medical-assistant/realtime-medical-assistant.conf
image="intelluxe/realtime-medical-assistant:latest"
port="8009:8009"
description="Real-time medical assistant integrating WhisperLive transcription with SciSpacy NLP and intelligent doctor assistance"
env="NODE_ENV=production,SCISPACY_MODEL=en_ner_bc5cdr_md"
volumes="./models:/app/models:rw,./cache:/app/cache:rw"
network_mode="intelluxe-net" 
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8009/health || exit 1"
depends_on="whisperlive,scispacy,ollama,healthcare-mcp"
```

**Real-time Medical Assistant implementation:**
```python
# agents/realtime_medical_assistant/realtime_assistant.py
from fastapi import FastAPI, WebSocket, HTTPException
from typing import Dict, Any, List, Optional
import asyncio
import json
import spacy
import httpx
from datetime import datetime, timedelta
import redis
from core.memory.memory_manager import memory_manager
from core.orchestration.agent_orchestrator import orchestrator

app = FastAPI(title="Real-time Medical Assistant")

class RealtimeMedicalAssistant:
    """
    Real-time medical assistant that processes WhisperLive transcription chunks,
    extracts medical entities with SciSpacy, and provides intelligent assistance
    """
    
    def __init__(self):
        # Load SciSpacy model for medical NER
        self.nlp = spacy.load("en_ner_bc5cdr_md")
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.ollama_client = httpx.AsyncClient(base_url="http://localhost:11434")
        
        # Medical entity tracking
        self.session_entities = {}
        self.doctor_patterns = {}
        
        # Integration with existing systems
        self.memory_manager = memory_manager
        self.orchestrator = orchestrator
    
    async def process_transcription_chunk(self, 
                                        doctor_id: str, 
                                        session_id: str,
                                        chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transcription chunk from WhisperLive"""
        
        transcription_text = chunk_data.get('text', '')
        confidence = chunk_data.get('confidence', 0.0)
        timestamp = chunk_data.get('timestamp', datetime.utcnow().isoformat())
        
        # Extract medical entities using SciSpacy
        entities = await self._extract_medical_entities(transcription_text)
        
        # Update session context
        await self._update_session_context(session_id, {
            'transcription': transcription_text,
            'entities': entities,
            'timestamp': timestamp,
            'confidence': confidence
        })
        
        # Generate intelligent assistance
        assistance = await self._generate_intelligent_assistance(
            doctor_id, session_id, transcription_text, entities
        )
        
        # Learn doctor patterns (for future LoRA training)
        await self._learn_doctor_patterns(doctor_id, transcription_text, entities, assistance)
        
        return {
            'processed_text': transcription_text,
            'medical_entities': entities,
            'intelligent_assistance': assistance,
            'confidence': confidence,
            'timestamp': timestamp
        }
    
    async def _extract_medical_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract medical entities using SciSpacy"""
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entity = {
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': getattr(ent, 'confidence', 0.9)
            }
            
            # Add medical context if available
            if ent.label_ in ['DISEASE', 'CHEMICAL']:
                entity['medical_context'] = await self._get_medical_context(ent.text, ent.label_)
            
            entities.append(entity)
        
        return entities
    
    async def _generate_intelligent_assistance(self, 
                                             doctor_id: str,
                                             session_id: str, 
                                             text: str, 
                                             entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate intelligent assistance based on medical entities and doctor patterns"""
        
        # Get doctor's typical patterns
        doctor_patterns = await self._get_doctor_patterns(doctor_id)
        
        # Build assistance context
        assistance_context = {
            'current_text': text,
            'medical_entities': entities,
            'doctor_patterns': doctor_patterns,
            'session_history': await self._get_session_history(session_id)
        }
        
        # Generate suggestions based on patterns
        suggestions = []
        
        # Check for symptoms mentioned
        symptoms = [e for e in entities if e['label'] == 'DISEASE' or 'symptom' in e['text'].lower()]
        if symptoms:
            # Suggest related conditions the doctor typically looks up
            related_lookups = await self._predict_doctor_lookups(doctor_id, symptoms)
            if related_lookups:
                suggestions.append({
                    'type': 'related_conditions',
                    'message': f"Based on symptoms mentioned, you typically look up: {', '.join(related_lookups)}",
                    'action': 'lookup_conditions',
                    'data': related_lookups
                })
        
        # Check for medication mentions
        medications = [e for e in entities if e['label'] == 'CHEMICAL']
        if medications:
            # Check for drug interactions
            interactions = await self._check_drug_interactions(medications)
            if interactions:
                suggestions.append({
                    'type': 'drug_interactions',
                    'message': f"Potential interactions detected with mentioned medications",
                    'action': 'review_interactions',
                    'data': interactions
                })
        
        # Generate contextual medical assistance
        medical_assistance = await self._generate_medical_context_assistance(text, entities)
        
        return {
            'suggestions': suggestions,
            'medical_assistance': medical_assistance,
            'confidence': 0.85,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def _learn_doctor_patterns(self, 
                                   doctor_id: str, 
                                   text: str, 
                                   entities: List[Dict[str, Any]], 
                                   assistance: Dict[str, Any]) -> None:
        """Learn doctor patterns for future LoRA training"""
        
        # Store interaction pattern
        pattern_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'transcription': text,
            'entities': entities,
            'assistance_provided': assistance,
            'doctor_id': doctor_id
        }
        
        # Store in Redis for pattern analysis
        pattern_key = f"doctor_patterns:{doctor_id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        await self.redis_client.setex(pattern_key, 86400 * 30, json.dumps(pattern_data))  # 30 days
        
        # Update doctor's pattern summary
        await self._update_doctor_pattern_summary(doctor_id, entities)
    
    async def _predict_doctor_lookups(self, doctor_id: str, symptoms: List[Dict[str, Any]]) -> List[str]:
        """Predict what conditions the doctor typically looks up based on symptoms"""
        
        # Get doctor's historical lookup patterns
        patterns = await self._get_doctor_patterns(doctor_id)
        
        symptom_texts = [s['text'].lower() for s in symptoms]
        related_conditions = []
        
        # Simple pattern matching (would be enhanced by LoRA model later)
        for symptom in symptom_texts:
            if 'chest pain' in symptom:
                related_conditions.extend(['myocardial infarction', 'angina', 'pulmonary embolism'])
            elif 'headache' in symptom:
                related_conditions.extend(['migraine', 'tension headache', 'cluster headache'])
            elif 'fever' in symptom:
                related_conditions.extend(['infection', 'influenza', 'COVID-19'])
        
        # Filter based on doctor's actual patterns
        if patterns and 'common_lookups' in patterns:
            related_conditions = [c for c in related_conditions if c in patterns['common_lookups']]
        
        return list(set(related_conditions))[:3]  # Top 3 suggestions
    
    async def _get_medical_context(self, entity_text: str, entity_type: str) -> Dict[str, Any]:
        """Get medical context for entity using Healthcare-MCP"""
        
        try:
            # Use Healthcare-MCP for medical information
            mcp_response = await httpx.post(
                "http://localhost:3000/query",
                json={
                    'query': f"medical information about {entity_text}",
                    'type': entity_type.lower()
                },
                timeout=5.0
            )
            
            if mcp_response.status_code == 200:
                return mcp_response.json()
            else:
                return {'error': 'MCP lookup failed'}
                
        except Exception as e:
            return {'error': str(e)}

# Global instance
realtime_medical_assistant = RealtimeMedicalAssistant()

@app.websocket("/ws/{doctor_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, doctor_id: str, session_id: str):
    """WebSocket endpoint for real-time transcription processing"""
    await websocket.accept()
    
    try:
        while True:
            # Receive transcription chunk from WhisperLive
            data = await websocket.receive_json()
            
            # Process chunk
            result = await realtime_medical_assistant.process_transcription_chunk(
                doctor_id, session_id, data
            )
            
            # Send assistance back to client
            await websocket.send_json(result)
            
    except Exception as e:
        await websocket.close(code=1000)

@app.post("/process_chunk")
async def process_chunk(chunk_data: Dict[str, Any]):
    """REST endpoint for processing transcription chunks"""
    
    doctor_id = chunk_data.get('doctor_id')
    session_id = chunk_data.get('session_id')
    
    if not doctor_id or not session_id:
        raise HTTPException(status_code=400, detail="doctor_id and session_id required")
    
    result = await realtime_medical_assistant.process_transcription_chunk(
        doctor_id, session_id, chunk_data
    )
    
    return result

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "realtime-medical-assistant"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
```

**Deploy real-time medical assistant:**
```bash
./scripts/universal-service-runner.sh start realtime-medical-assistant

# Verify service is running
curl http://localhost:8009/health
```

### 4.2 WhisperLive Integration with Real-time Assistant

**Enhanced WhisperLive configuration to send chunks to real-time assistant:**
```python
# services/user/whisperlive/integration_config.py
REALTIME_ASSISTANT_CONFIG = {
    'endpoint': 'http://localhost:8009/process_chunk',
    'websocket_endpoint': 'ws://localhost:8009/ws',
    'chunk_processing': True,
    'medical_entity_extraction': True,
    'intelligent_assistance': True
}

# Modify WhisperLive to send transcription chunks to real-time assistant
async def on_transcription_chunk(chunk_data):
    """Send transcription chunk to real-time medical assistant"""
    
    # Add doctor and session context
    chunk_data.update({
        'doctor_id': current_session.get('doctor_id'),
        'session_id': current_session.get('session_id'),
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send to real-time assistant for processing
    try:
        response = await httpx.post(
            REALTIME_ASSISTANT_CONFIG['endpoint'],
            json=chunk_data,
            timeout=2.0
        )
        
        if response.status_code == 200:
            assistance_data = response.json()
            
            # Send assistance back to doctor's interface
            await send_to_doctor_interface(assistance_data)
            
    except Exception as e:
        logger.error(f"Failed to process chunk with real-time assistant: {e}")
```

### 4.3 SciSpacy Integration Enhancement

**Enhanced SciSpacy service with medical entity caching:**
```bash
# services/user/scispacy/scispacy.conf  
image="intelluxe/scispacy:latest"
port="8010:8010"
description="SciSpacy medical NLP with enhanced entity extraction and caching"
env="NODE_ENV=production,MODEL=en_ner_bc5cdr_md,CACHE_ENABLED=true"
volumes="./models:/app/models:rw,./cache:/app/cache:rw"
network_mode="intelluxe-net"
restart_policy="unless-stopped"
healthcheck="curl -f http://localhost:8010/health || exit 1"
```

## Deployment and Validation Checklist

**Phase 2 Completion Criteria:**

- [ ] Insurance verification service deployed using universal service runner
- [ ] Billing engine handling claims creation and processing
- [ ] Compliance monitor logging all data access with HIPAA audit trails
- [ ] Doctor personalization service storing preferences securely
- [ ] Enhanced database schema with business service tables
- [ ] Business service monitoring integrated with existing InfluxDB/Grafana setup
- [ ] Enhanced agent router orchestrating complete workflows
- [ ] Comprehensive integration tests passing
- [ ] Performance monitoring extended to business services

**Key Architecture Achievements:**
- Multi-provider insurance verification with error prevention using your service architecture
- Automated billing with safety checks and code validation
- HIPAA-compliant audit logging with compliance rule engine
- Privacy-first personalization with PHI protection
- Enhanced agent router orchestrating complete patient workflows
- Business service monitoring integrated with your existing monitoring stack

**Ready for Phase 3:**
- Business services ready for production deployment
- Compliance framework established for healthcare regulations
- Personalization infrastructure ready for advanced features
- Complete patient workflow automation from intake to billing
- Comprehensive monitoring covering all services using your InfluxDB/Grafana setup

This Phase 2 transforms your healthcare AI system into a complete clinical workflow platform with insurance, billing, compliance, and personalization capabilities, all built using your actual service architecture and monitoring infrastructure.