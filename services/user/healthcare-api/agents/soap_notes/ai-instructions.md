# SOAP Notes Agent - AI Instructions

## Agent Purpose
The SOAP Notes Agent transforms raw medical transcriptions into structured clinical documentation following standard medical note formats (SOAP, Progress Notes, H&P, etc.).

## Core Capabilities

### 1. SOAP Note Generation
- **Input**: Raw transcription text from medical encounters
- **Output**: Structured SOAP note with S.O.A.P. sections
- **Quality**: Includes completeness scoring and improvement recommendations

### 2. Progress Note Generation  
- **Input**: Follow-up visit transcriptions
- **Output**: Formatted progress notes with interval history, exam, and plan
- **Focus**: Efficient documentation for routine follow-ups

### 3. Clinical Documentation Formatting
- **Input**: Existing clinical note data
- **Output**: Properly formatted notes according to templates
- **Standards**: EHR-compatible formatting with medical terminology

### 4. Live Session Integration
- **Input**: Full transcription from live doctor-patient sessions
- **Output**: Real-time SOAP note generation
- **Integration**: Works with WebSocket transcription sessions

## Medical Compliance

### PHI Protection
- All transcription data is scanned for PHI before processing
- PHI sanitization applied to generated notes
- Secure handling of patient information throughout

### Medical Disclaimers
- Agent provides **administrative support only**
- Does NOT provide medical advice, diagnosis, or treatment recommendations
- All clinical content must be reviewed by qualified healthcare professionals
- Documentation assistance only - not clinical decision support

### Quality Assurance
- Completeness scoring for generated notes
- Missing section identification
- Quality improvement recommendations
- Medical terminology validation

## Technical Integration

### Agent Architecture
- Inherits from `BaseHealthcareAgent`
- Healthcare logging with phi_monitor decorators
- Async processing for real-time performance
- Database integration for note storage

### API Endpoints
- `/soap-notes/generate-soap` - Generate SOAP notes
- `/soap-notes/generate-progress` - Generate progress notes  
- `/soap-notes/session-to-soap` - Convert live sessions to SOAP
- `/soap-notes/format-note` - Format existing notes
- `/soap-notes/templates` - Get available templates

### Multi-Agent Integration
- Receives transcription data from Transcription Agent
- Processes live session data from WebSocket endpoints
- Provides structured output for EHR integration

## Note Templates

### SOAP Note Template
- **S**ubjective: Patient history, symptoms, concerns
- **O**bjective: Physical exam, vitals, test results
- **A**ssessment: Clinical impression, diagnosis
- **P**lan: Treatment plan, follow-up, patient education

### Progress Note Template
- Interval History: Changes since last visit
- Current Medications: Medication review and changes
- Physical Exam: Focused examination findings
- Assessment and Plan: Clinical status and ongoing treatment

### Quality Metrics
- Completeness Score (0.0-1.0)
- Missing Sections List
- Improvement Recommendations
- Medical Terminology Validation

## Best Practices

### Content Extraction
- Uses NLP patterns to identify clinical sections
- Preserves medical terminology accuracy
- Maintains clinical context and relationships

### Format Standardization
- Consistent section headers and organization
- Medical terminology preservation
- EHR-compatible formatting

### Error Handling
- Graceful degradation for incomplete transcriptions
- Clear error messages for missing required data
- Fallback content generation for missing sections

## Development Guidelines

### Code Organization
- Section extraction methods for different note types
- Template management system
- Quality assessment algorithms
- Format generation utilities

### Healthcare Compliance
- All methods decorated with healthcare logging
- PHI monitoring on all patient data processing
- Audit trails for all note generation activities
- Compliance validation throughout processing

### Performance Optimization
- Async processing for real-time note generation
- Efficient pattern matching for section extraction
- Caching of templates and formatting rules
- Minimal processing delays for live sessions