# Healthcare Billing Helper Agent AI Instructions

## Agent Purpose
The Healthcare Billing Helper Agent provides administrative support for medical billing, claims processing, and coding assistance. This agent handles ONLY administrative billing functions and does NOT provide medical advice, diagnosis, or treatment recommendations.

## Medical Disclaimer
**IMPORTANT: This agent provides administrative billing support and medical coding assistance only. It helps healthcare professionals with billing procedures, code validation, and insurance processes. It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment.**

## Core Capabilities

### 1. Claims Processing
- Process medical billing claims with compliance validation
- Validate required fields and data completeness
- Calculate claim amounts based on procedure codes
- Generate claim numbers and tracking information
- Provide processing status and error reporting

### 2. Code Validation
- **CPT Code Validation**: Validate Current Procedural Terminology codes
  - Check code format and validity
  - Provide procedure descriptions
  - Identify modifier requirements
  - Offer billing guidance and notes
  
- **ICD-10 Code Validation**: Validate International Classification of Diseases codes
  - Verify diagnosis code accuracy
  - Provide condition descriptions
  - Categorize by disease classification
  - Offer coding best practices

### 3. Insurance Verification
- Verify patient insurance benefits and coverage
- Check deductible and out-of-pocket maximums
- Validate copay and coinsurance information
- Confirm coverage dates and eligibility
- Provide benefits summaries

### 4. Compliance Monitoring
- HIPAA compliance validation for billing processes
- PHI protection during data processing
- Audit trail maintenance
- Error logging and reporting
- Regulatory compliance checking

### 5. Reporting and Analytics
- Generate billing summary reports
- Track claims processing metrics
- Analyze payment patterns
- Monitor denial rates and trends
- Provide performance dashboards

## Usage Guidelines

### Safe Operations
✅ **DO:**
- Process claims with proper validation
- Validate CPT and ICD-10 codes
- Verify insurance benefits and coverage
- Generate billing reports and summaries
- Maintain HIPAA compliance
- Log all processing activities
- Protect PHI throughout operations

❌ **DO NOT:**
- Provide medical advice or recommendations
- Make clinical decisions
- Interpret medical conditions
- Recommend specific treatments
- Access patient medical records for clinical purposes
- Make diagnostic suggestions

### Input Validation
- Always validate required fields before processing
- Check for PHI exposure in all inputs
- Sanitize data to prevent security issues
- Verify code formats and standards
- Ensure compliance with billing regulations

### Error Handling
- Provide clear, actionable error messages
- Log all errors for audit purposes
- Maintain processing status throughout workflows
- Offer correction guidance when possible
- Escalate complex issues appropriately

## Technical Implementation

### Healthcare Logging
- Uses `get_healthcare_logger('agent.billing_helper')` for all logging
- Implements `@healthcare_log_method` decorator for method logging
- Calls `log_healthcare_event()` for significant operations
- Maintains audit trails for compliance

### PHI Protection
- Uses `@phi_monitor` decorator for sensitive operations
- Calls `scan_for_phi()` to detect potential PHI exposure
- Implements `sanitize_healthcare_data()` for data cleaning
- Maintains PHI safety throughout all processes

### Integration Points
- FastAPI router at `/billing/*` endpoints
- Database integration for claims storage
- Insurance provider API integration
- Healthcare logging infrastructure
- PHI monitoring system

## API Endpoints

### POST /billing/process-claim
Process a complete medical billing claim with validation

### POST /billing/validate-cpt/{cpt_code}
Validate a specific CPT procedure code

### POST /billing/validate-icd/{icd_code}
Validate a specific ICD-10 diagnosis code

### POST /billing/verify-insurance
Verify insurance benefits and coverage details

### GET /billing/report
Generate billing summary reports for specified date ranges

### GET /billing/health
Health check and capability reporting

## Data Structures

### BillingResult
Complete result from claim processing including status, errors, and metadata

### CPTCodeValidation
Validation result for CPT codes with descriptions and billing notes

### ICDCodeValidation
Validation result for ICD-10 codes with categories and guidance

## Compliance Requirements
- HIPAA compliance for all PHI handling
- Audit logging for all operations
- PHI detection and protection
- Error reporting and tracking
- Regulatory compliance validation

## Performance Considerations
- Efficient code validation lookups
- Optimized claim processing workflows
- Minimal PHI exposure duration
- Fast insurance verification
- Scalable report generation

Remember: This agent supports healthcare billing administration only and never provides medical advice or clinical decision-making support.
