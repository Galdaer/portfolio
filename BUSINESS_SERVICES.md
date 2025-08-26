# Business Services - Intelluxe AI Healthcare System

This document explains the business microservices layer of the Intelluxe AI Healthcare System. These services handle specialized business logic that has been extracted from the core healthcare API to provide focused, scalable functionality.

## Overview

The business services layer consists of 5 specialized microservices that work together to provide comprehensive healthcare business functionality:

1. **Insurance Verification Service** - Multi-provider insurance verification with Chain-of-Thought reasoning
2. **Billing Engine Service** - Medical billing and claims processing with Tree of Thoughts reasoning  
3. **Compliance Monitor Service** - HIPAA compliance monitoring and audit tracking
4. **Business Intelligence Service** - Healthcare analytics and reporting
5. **Doctor Personalization Service** - AI personalization using LoRA adapters

## Architecture

### Service Communication
All business services operate on the `intelluxe-net` Docker network with static IP allocations:

```
172.20.0.23 - Insurance Verification Service (port 8003)
172.20.0.24 - Billing Engine Service (port 8004)
172.20.0.25 - Compliance Monitor Service (port 8005)
172.20.0.26 - Business Intelligence Service (port 8006)
172.20.0.27 - Doctor Personalization Service (port 8007)
```

### Shared Infrastructure
- **Database**: PostgreSQL at `172.20.0.13:5432` (intelluxe_public database)
- **Cache**: Redis at `172.20.0.12:6379`  
- **AI Inference**: Ollama at `172.20.0.10:11434`
- **Core API**: Healthcare API at `172.20.0.11:8000`

### Communication Patterns
- RESTful APIs for service-to-service communication
- Circuit breaker patterns for fault tolerance
- JWT-based authentication between services
- Comprehensive audit logging for all interactions
- Health check endpoints at `/health` for all services

## Service Details

## 1. Insurance Verification Service

**Purpose**: Multi-provider insurance verification with advanced error prevention using Chain-of-Thought reasoning.

**Port**: 8003 | **IP**: 172.20.0.23

### Key Features
- **Chain-of-Thought Reasoning**: Logical step-by-step verification process
- **Multi-Provider Support**: Integration with multiple insurance providers
- **Error Prevention**: Advanced validation and verification steps
- **PHI Protection**: Built-in PHI detection and sanitization
- **Real-time Verification**: Immediate insurance status checking

### Core Functionality
- Patient insurance eligibility verification
- Benefits and coverage analysis
- Prior authorization checking
- Claims pre-validation
- Provider network verification

### API Endpoints
```
GET  /health                    - Service health check
POST /verify-insurance         - Verify patient insurance
POST /check-eligibility        - Check treatment eligibility  
POST /verify-benefits          - Verify insurance benefits
POST /check-prior-auth         - Check prior authorization status
GET  /provider-network         - Check provider network status
```

### Chain-of-Thought Integration
The service uses CoT reasoning for complex verification decisions:
1. **Information Gathering** - Collect patient and insurance data
2. **Validation Steps** - Verify data completeness and accuracy  
3. **Provider Checks** - Confirm insurance provider connectivity
4. **Eligibility Analysis** - Analyze coverage and benefits
5. **Error Detection** - Identify potential issues or conflicts
6. **Final Verification** - Provide confident verification result

### Usage Example
```python
# Verify patient insurance
response = requests.post('http://172.20.0.23:8003/verify-insurance', json={
    'patient_id': 'P123456',
    'insurance_id': 'INS789',
    'provider_id': 'PROV001',
    'service_date': '2024-01-15'
})
```

### Configuration
- `COT_REASONING_ENABLED=true` - Enable Chain-of-Thought reasoning
- `PHI_DETECTION_ENABLED=true` - Enable PHI protection
- `HEALTHCARE_API_URL` - Core API integration endpoint

---

## 2. Billing Engine Service  

**Purpose**: Medical billing and claims processing with Tree of Thoughts reasoning for complex billing scenarios.

**Port**: 8004 | **IP**: 172.20.0.24

### Key Features
- **Tree of Thoughts Reasoning**: Multi-path analysis for complex billing decisions
- **Claims Processing**: Complete medical claims lifecycle management
- **Code Validation**: Medical code verification (ICD-10, CPT, HCPCS)
- **Payment Tracking**: Comprehensive payment and reimbursement tracking
- **Automated Workflows**: Streamlined billing processes

### Core Functionality
- Medical claims creation and submission
- Billing code validation and optimization
- Payment processing and tracking
- Claims denial analysis and resubmission
- Revenue cycle management
- Compliance reporting

### API Endpoints
```
GET  /health                    - Service health check
POST /create-claim             - Create new medical claim
POST /submit-claim             - Submit claim to insurance
POST /validate-codes           - Validate medical billing codes
POST /process-payment          - Process payment transaction
GET  /claim-status/{claim_id}  - Check claim processing status
POST /analyze-denial           - Analyze claim denial reasons
GET  /revenue-report           - Generate revenue reports
```

### Tree of Thoughts Integration
The service uses ToT reasoning for complex billing scenarios:
1. **Multiple Coding Paths** - Explore different coding strategies
2. **Reimbursement Analysis** - Analyze potential reimbursement outcomes
3. **Risk Assessment** - Evaluate denial risk for different approaches
4. **Optimization Strategies** - Find optimal billing approach
5. **Compliance Validation** - Ensure regulatory compliance
6. **Best Path Selection** - Choose optimal billing strategy

### Usage Example
```python
# Create and validate a medical claim
response = requests.post('http://172.20.0.24:8004/create-claim', json={
    'patient_id': 'P123456',
    'provider_id': 'PROV001', 
    'services': [
        {'code': '99213', 'description': 'Office visit', 'amount': 150.00}
    ],
    'insurance_info': {...}
})
```

### Configuration
- `TOT_REASONING_ENABLED=true` - Enable Tree of Thoughts reasoning
- `INSURANCE_VERIFICATION_URL` - Integration with insurance verification
- `HEALTHCARE_API_URL` - Core API integration

---

## 3. Compliance Monitor Service

**Purpose**: Automated HIPAA compliance monitoring with audit trail tracking and violation detection.

**Port**: 8005 | **IP**: 172.20.0.25

### Key Features
- **Real-time Monitoring**: Continuous compliance monitoring across all services
- **Audit Trail Tracking**: Comprehensive audit logging and analysis
- **Violation Detection**: Automated detection of HIPAA violations
- **Compliance Dashboards**: Real-time compliance metrics and reporting
- **Automated Alerts**: Immediate notification of compliance issues

### Core Functionality
- HIPAA compliance rule enforcement
- Audit log aggregation and analysis
- Violation pattern detection
- Compliance score calculation
- Regulatory reporting generation
- Risk assessment and mitigation

### API Endpoints
```
GET  /health                    - Service health check
POST /track-audit              - Track audit events
GET  /compliance-status        - Get overall compliance status
GET  /violations               - List detected violations
POST /generate-report          - Generate compliance reports
GET  /audit-trail/{entity_id}  - Get audit trail for entity
POST /risk-assessment          - Perform compliance risk assessment
GET  /dashboard-metrics        - Get compliance dashboard metrics
```

### Monitoring Capabilities
- **PHI Access Tracking** - Monitor all PHI access events
- **Data Breach Detection** - Identify potential data breaches
- **User Behavior Analysis** - Detect anomalous user behavior
- **System Integrity Checks** - Verify system security controls
- **Compliance Scoring** - Real-time compliance score calculation

### Usage Example
```python
# Track a PHI access event
response = requests.post('http://172.20.0.25:8005/track-audit', json={
    'event_type': 'PHI_ACCESS',
    'user_id': 'U123',
    'patient_id': 'P456', 
    'action': 'VIEW_RECORD',
    'timestamp': '2024-01-15T10:30:00Z'
})
```

### Configuration
- `AUDIT_RETENTION_DAYS=2555` - Audit log retention period (7 years)
- `HEALTHCARE_API_URL` - Monitor healthcare API events
- `BILLING_ENGINE_URL` - Monitor billing events
- `INSURANCE_VERIFICATION_URL` - Monitor verification events

---

## 4. Business Intelligence Service

**Purpose**: Healthcare business intelligence with analytics and reporting capabilities.

**Port**: 8006 | **IP**: 172.20.0.26

### Key Features
- **Healthcare Analytics** - Comprehensive healthcare data analysis
- **Performance Metrics** - Service and system performance tracking
- **Financial Reporting** - Revenue and billing analytics
- **Compliance Analytics** - HIPAA compliance trend analysis
- **Predictive Analytics** - Forecasting and trend prediction

### Core Functionality
- Revenue cycle analytics
- Patient flow analysis
- Provider performance metrics
- Compliance trend analysis
- Cost optimization insights
- Predictive modeling

### API Endpoints
```
GET  /health                    - Service health check
GET  /financial-dashboard      - Financial performance dashboard
GET  /operational-metrics      - Operational performance metrics
GET  /compliance-analytics     - Compliance trend analysis
POST /custom-report            - Generate custom analytics report
GET  /predictive-insights      - Get predictive analytics
POST /data-export             - Export analytics data
GET  /performance-trends       - System performance trends
```

### Analytics Capabilities
- **Revenue Analysis** - Track billing and payment trends
- **Patient Analytics** - Patient demographics and behavior analysis
- **Provider Analytics** - Provider performance and efficiency metrics
- **Compliance Trends** - HIPAA compliance patterns over time
- **System Performance** - Infrastructure and service performance

### Usage Example
```python
# Get financial dashboard data
response = requests.get('http://172.20.0.26:8006/financial-dashboard', params={
    'date_range': '30d',
    'provider_id': 'PROV001'
})
```

### Configuration
- `REPORT_RETENTION_DAYS=365` - Analytics report retention period
- `COMPLIANCE_MONITOR_URL` - Integration with compliance monitoring
- `BILLING_ENGINE_URL` - Integration with billing data
- `INSURANCE_VERIFICATION_URL` - Integration with verification data

---

## 5. Doctor Personalization Service

**Purpose**: AI personalization service for healthcare providers using LoRA (Low-Rank Adaptation) for model customization.

**Port**: 8007 | **IP**: 172.20.0.27

### Key Features
- **LoRA-Based Adaptation** - Personalized AI models for each healthcare provider
- **Learning from Interactions** - Continuous learning from provider interactions
- **Specialty-Specific Models** - Customization based on medical specialty
- **Preference Learning** - Adapt to provider communication and workflow preferences
- **Performance Optimization** - Efficient model serving and caching

### Core Functionality
- Provider-specific AI model adaptation
- Interaction pattern learning
- Specialty-based customization
- Preference-based responses
- Model performance optimization
- Continuous improvement

### API Endpoints
```
GET  /health                    - Service health check
POST /personalize-model        - Create personalized model for provider
POST /train-adaptation         - Train LoRA adapter from interactions
GET  /model-status/{provider_id} - Get personalization model status
POST /generate-personalized    - Generate personalized AI response
POST /update-preferences       - Update provider preferences
GET  /adaptation-metrics       - Get adaptation performance metrics
POST /deploy-model             - Deploy personalized model
```

### Personalization Features
- **Communication Style** - Adapt to provider's communication preferences
- **Clinical Focus** - Emphasize relevant medical specialties
- **Workflow Integration** - Adapt to provider's workflow patterns
- **Decision Support** - Personalized clinical decision support
- **Documentation Style** - Match provider's documentation preferences

### Usage Example
```python
# Create personalized model for a provider
response = requests.post('http://172.20.0.27:8007/personalize-model', json={
    'provider_id': 'PROV001',
    'specialty': 'cardiology',
    'preferences': {
        'communication_style': 'detailed',
        'focus_areas': ['heart_disease', 'hypertension']
    }
})
```

### Configuration
- `PERSONALIZATION_ENABLED=true` - Enable AI personalization
- `MODEL_CACHE_SIZE=5` - Number of models to cache in memory
- `LORA_ADAPTER_PATH=/app/models/adapters` - LoRA adapter storage path
- `OLLAMA_HOST` - AI inference server integration

---

## Service Communication & Integration

### Inter-Service Communication
Services communicate using RESTful APIs with the following patterns:

```python
# Example: Billing Engine calling Insurance Verification
verification_response = requests.post(
    'http://172.20.0.23:8003/verify-insurance',
    json={'patient_id': patient_id, 'insurance_id': insurance_id}
)

if verification_response.json()['verified']:
    # Proceed with billing
    billing_response = process_billing(claim_data)
```

### Circuit Breaker Pattern
All services implement circuit breaker patterns for fault tolerance:
- **Closed State**: Normal operation
- **Open State**: Service calls fail fast when downstream service is down
- **Half-Open State**: Limited calls allowed to test service recovery

### Authentication & Security
- JWT-based authentication between services
- PHI detection and sanitization in all data flows
- Comprehensive audit logging for all service interactions
- Security headers and HTTPS enforcement

## Deployment & Management

### Building Services
```bash
# Build individual services
make insurance-verification-build
make billing-engine-build  
make compliance-monitor-build
make business-intelligence-build
make doctor-personalization-build

# Build all business services
make business-services-build
```

### Service Management
```bash
# Check service health
make insurance-verification-health
make billing-engine-health
make compliance-monitor-health
make business-intelligence-health
make doctor-personalization-health

# View service logs
make insurance-verification-logs
make billing-engine-logs
make compliance-monitor-logs
make business-intelligence-logs
make doctor-personalization-logs
```

### Testing Services
```bash
# Test individual services
make insurance-verification-test
make billing-engine-test
make compliance-monitor-test
make business-intelligence-test
make doctor-personalization-test

# Test all business services
make business-services-test
```

## Monitoring & Health Checks

### Health Check Endpoints
All services provide health check endpoints at `/health`:

```bash
curl http://172.20.0.23:8003/health  # Insurance Verification
curl http://172.20.0.24:8004/health  # Billing Engine
curl http://172.20.0.25:8005/health  # Compliance Monitor
curl http://172.20.0.26:8006/health  # Business Intelligence
curl http://172.20.0.27:8007/health  # Doctor Personalization
```

### Service Dependencies
```
Insurance Verification → PostgreSQL, Redis, Healthcare API
Billing Engine → PostgreSQL, Redis, Insurance Verification
Compliance Monitor → PostgreSQL, Redis
Business Intelligence → PostgreSQL, Redis, All other services
Doctor Personalization → PostgreSQL, Redis, Ollama
```

## Configuration Management

All services use environment-based configuration:

- **Database**: `POSTGRES_URL` for persistent storage
- **Cache**: `REDIS_URL` for session and temporary data
- **Logging**: `LOG_LEVEL` for logging configuration
- **Integration**: Service-specific URLs for inter-service communication
- **Security**: PHI detection and compliance features
- **AI Features**: Reasoning and personalization capabilities

## Best Practices

### Development
1. Follow FastAPI patterns for all service implementations
2. Use async/await for all I/O operations
3. Implement comprehensive error handling
4. Include extensive logging and monitoring
5. Follow HIPAA compliance patterns

### Security
1. Enable PHI detection in all services
2. Implement audit logging for all operations
3. Use JWT authentication between services
4. Apply security headers and HTTPS
5. Regular security assessments

### Monitoring
1. Monitor all service health endpoints
2. Track performance metrics and trends
3. Monitor compliance scores and violations
4. Set up alerts for critical issues
5. Regular performance optimization

## Troubleshooting

### Common Issues
- **Service Communication**: Check network connectivity between static IPs
- **Database Issues**: Verify PostgreSQL connection and permissions
- **Authentication**: Check JWT token validity and service authentication
- **Health Checks**: Monitor `/health` endpoints for service status
- **Performance**: Check Redis cache performance and database query optimization

### Diagnostic Commands
```bash
# Check service status
docker ps | grep intelluxe

# Check network connectivity
docker network inspect intelluxe-net

# View service logs
docker logs <service_container>

# Test service endpoints
curl -f http://<service_ip>:<port>/health
```

This business services layer provides a comprehensive, scalable foundation for healthcare business operations while maintaining the highest standards of security, compliance, and performance required for healthcare applications.