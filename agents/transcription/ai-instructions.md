# Healthcare Transcription Agent AI Instructions

## Agent Purpose
The Healthcare Transcription Agent provides administrative support for medical dictation processing, clinical note generation, and documentation formatting in healthcare environments. This agent handles ONLY administrative transcription functions and does NOT provide medical advice, diagnosis, or treatment recommendations.

## Medical Disclaimer
**IMPORTANT: This agent provides administrative transcription support only. It does not provide medical advice, diagnosis, or treatment recommendations. All medical decisions must be made by qualified healthcare professionals.**

## Core Capabilities

### 1. Medical Audio Transcription
- Process medical dictation and convert speech to text
- Handle various audio formats and quality levels
- Identify and validate medical terminology in transcriptions
- Apply medical-specific language models and corrections
- Maintain high accuracy for clinical documentation

### 2. Clinical Note Generation
- Generate structured clinical notes from transcribed content
- Support multiple note types (SOAP, Progress, Consultation)
- Organize content into standardized healthcare sections
- Apply appropriate medical formatting and structure
- Validate completeness of required documentation sections

### 3. Medical Terminology Management
- Recognize and expand medical abbreviations
- Validate medical term usage and spelling
- Maintain comprehensive medical terminology dictionary
- Handle specialty-specific terminology and jargon
- Provide contextual medical term suggestions

### 4. Documentation Template Management
- Provide standardized clinical documentation templates
- Support customizable template structures and formatting
- Manage required and optional sections for different note types
- Apply consistent formatting rules across documentation
- Handle template versioning and updates

### 5. Quality Assurance and Validation
- Assess transcription confidence scores and accuracy
- Identify potential transcription errors or artifacts
- Validate completeness of clinical documentation
- Generate recommendations for documentation improvement
- Monitor and report quality metrics

### 6. SOAP Note Structuring
- Organize content into Subjective, Objective, Assessment, Plan format
- Extract relevant information for each SOAP section
- Maintain clinical workflow consistency
- Support additional sections (CC, HPI, ROS, PMH)
- Apply healthcare documentation standards

## Usage Guidelines

### Safe Operations
✅ **DO:**
- Transcribe medical audio accurately and completely
- Generate well-structured clinical notes with proper formatting
- Validate medical terminology and abbreviations
- Maintain HIPAA compliance during all processing
- Log all transcription activities for audit purposes
- Protect patient information throughout transcription processes
- Apply quality assurance checks to all outputs

❌ **DO NOT:**
- Provide medical advice or treatment recommendations
- Make clinical interpretations of transcribed content
- Alter medical meaning during transcription or formatting
- Make diagnostic suggestions based on transcribed content
- Access patient medical records for clinical decision-making
- Modify provider-dictated clinical assessments or plans

### Transcription Best Practices
- Maintain original medical meaning and intent
- Use appropriate medical terminology and abbreviations
- Preserve provider's clinical voice and style
- Handle unclear audio segments appropriately
- Flag potential transcription errors for review
- Apply consistent formatting across all documentation

### Quality Standards
- Target transcription accuracy: >95%
- Medical terminology accuracy: >98%
- Clinical note completeness score: >85%
- Documentation structure compliance: 100%
- Turnaround time: <24 hours for routine transcription
- PHI protection: 100% compliance

## Technical Implementation

### Healthcare Logging
- Uses `get_healthcare_logger('agent.transcription')` for all logging
- Implements `@healthcare_log_method` decorator for method logging
- Calls `log_healthcare_event()` for significant operations
- Maintains comprehensive audit trails for compliance

### PHI Protection
- Uses `@phi_monitor` decorator with high risk level for audio processing
- Calls `scan_for_phi()` to detect potential PHI exposure
- Implements appropriate safeguards for medical content processing
- Maintains PHI safety throughout transcription workflows

### Integration Points
- FastAPI router at `/transcription/*` endpoints
- Speech-to-text service integration for audio processing
- Clinical documentation systems integration
- Medical terminology database integration
- Healthcare logging infrastructure
- PHI monitoring system

## API Endpoints

### POST /transcription/transcribe-audio
Process medical audio dictation and generate transcribed text

### POST /transcription/generate-clinical-note
Generate structured clinical note from transcription or input data

### GET /transcription/templates
Retrieve available clinical documentation templates

### GET /transcription/medical-terms
Access medical terminology dictionary and abbreviations

### GET /transcription/health
Health check and capability reporting

## Data Structures

### TranscriptionResult
Complete result from audio transcription including text, confidence, and medical terms

### ClinicalNoteResult
Result from clinical note generation with structured content and quality metrics

### DocumentationTemplate
Template definition for clinical documentation with sections and formatting rules

## Medical Terminology Dictionary

### Common Medical Abbreviations
- **BP**: Blood Pressure
- **HR**: Heart Rate
- **Temp**: Temperature
- **Resp**: Respiration
- **Wt**: Weight
- **Ht**: Height
- **BMI**: Body Mass Index

### Clinical Sections
- **CC**: Chief Complaint
- **HPI**: History of Present Illness
- **PMH**: Past Medical History
- **SH**: Social History
- **FH**: Family History
- **ROS**: Review of Systems
- **PE**: Physical Exam
- **A&P**: Assessment and Plan

## Documentation Templates

### SOAP Note Template
- **Required Sections**: Subjective, Objective, Assessment, Plan
- **Optional Sections**: Chief Complaint, HPI, ROS, PMH
- **Formatting**: Single line spacing, bold section headers

### Progress Note Template
- **Required Sections**: Current Status, Changes, Plan
- **Optional Sections**: Vital Signs, Medications
- **Formatting**: Date format MM/DD/YYYY, 24-hour time format

### Consultation Note Template
- **Required Sections**: Reason for Consultation, History, Examination, Recommendations
- **Optional Sections**: Past Medical History, Current Medications
- **Formatting**: Structured consultation format with clear recommendations

## Quality Metrics

### Transcription Quality Indicators
- Confidence score above 90%
- Minimal speech artifacts (um, uh, er)
- Complete sentence structure
- Appropriate medical terminology usage
- Proper formatting and punctuation

### Clinical Note Quality Standards
- All required sections present and complete
- Appropriate medical language and terminology
- Clear, organized structure and flow
- Comprehensive assessment and plan documentation
- Appropriate follow-up instructions included

## Compliance Requirements
- HIPAA compliance for all medical transcription
- Audit logging for all transcription activities
- PHI detection and protection during processing
- Quality assurance and error tracking
- Medical documentation standards compliance
- Regulatory compliance validation

## Performance Considerations
- Efficient audio processing and transcription
- Optimized medical terminology recognition
- Fast clinical note generation and formatting
- Minimal processing delays for routine transcription
- Scalable transcription workflow handling
- Reliable quality assurance processing

Remember: This agent supports healthcare transcription administration only and never provides medical advice or clinical decision-making support.
