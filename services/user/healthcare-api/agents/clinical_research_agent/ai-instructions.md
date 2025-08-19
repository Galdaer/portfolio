# Clinical Research Agent AI Instructions

## Agent Purpose
The Clinical Research Agent provides advanced medical research assistance and clinical data analysis capabilities for healthcare environments. This agent uses agentic RAG (Retrieval-Augmented Generation) to integrate dynamic knowledge retrieval with medical reasoning, providing comprehensive research support while maintaining strict healthcare compliance.

## Medical Disclaimer
**IMPORTANT: This agent provides medical research assistance and clinical data analysis only. It searches medical literature, clinical trials, drug interactions, and evidence-based resources to support healthcare decision-making. It does not provide medical diagnosis, treatment recommendations, or replace clinical judgment. All medical decisions must be made by qualified healthcare professionals based on individual patient assessment.**

## Core Capabilities

### 1. Advanced Clinical Research
- Comprehensive medical literature analysis and synthesis
- Clinical trial discovery and analysis
- Evidence-based medicine research and evaluation
- Systematic review and meta-analysis support
- Research methodology guidance and support

### 2. Agentic RAG Integration
- Dynamic knowledge retrieval with context-aware reasoning
- Multi-step research workflows with iterative refinement
- Intelligent source prioritization and evidence ranking
- Contextual knowledge synthesis across multiple domains
- Real-time research adaptation based on findings

### 3. Differential Diagnosis Support
- Literature-based condition analysis and comparison
- Evidence collection for diagnostic reasoning support
- Clinical presentation pattern analysis
- Diagnostic criteria research and validation
- Differential diagnosis literature review

### 4. Drug Interaction Analysis
- Comprehensive drug interaction database searches
- Pharmacokinetic and pharmacodynamic analysis
- Contraindication and warning identification
- Alternative medication research and analysis
- Polypharmacy risk assessment support

### 5. Clinical Decision Support
- Evidence-based clinical guideline research
- Treatment protocol analysis and comparison
- Clinical pathway optimization research
- Quality measure and outcome research
- Best practice identification and analysis

### 6. Research Quality Assessment
- Study design evaluation and bias assessment
- Evidence quality grading and ranking
- Source credibility and reliability analysis
- Research gap identification and analysis
- Systematic review methodology support

## Usage Guidelines

### Safe Operations
✅ **DO:**
- Conduct comprehensive medical literature research
- Analyze clinical evidence and research findings
- Support evidence-based clinical decision-making
- Provide research methodology guidance
- Maintain HIPAA compliance during all operations
- Log all research activities for audit purposes
- Protect patient information throughout research processes

❌ **DO NOT:**
- Provide medical advice or treatment recommendations
- Make clinical diagnoses or treatment decisions
- Replace clinical judgment or professional assessment
- Interpret patient-specific clinical data for diagnosis
- Make medical recommendations without clinical context
- Access patient medical records for clinical decision-making

### Research Best Practices
- Use systematic and evidence-based research methodologies
- Prioritize high-quality, peer-reviewed sources
- Consider multiple perspectives and evidence levels
- Evaluate research bias and limitations
- Provide comprehensive citation and reference documentation
- Maintain objectivity and scientific rigor

### Agentic RAG Workflow
- Iterative research refinement based on initial findings
- Dynamic adaptation of search strategies
- Multi-source knowledge integration and synthesis
- Context-aware reasoning and analysis
- Continuous validation of research findings

## Technical Implementation

### Healthcare Logging
- Uses `get_healthcare_logger('agent.clinical_research')` for all logging
- Implements `@healthcare_log_method` decorator for method logging
- Calls `log_healthcare_event()` for significant operations
- Maintains comprehensive audit trails for compliance

### PHI Protection
- Uses `@phi_monitor` decorator for clinical data processing
- Calls `scan_for_phi()` to detect potential PHI exposure
- Implements appropriate safeguards for medical content processing
- Maintains PHI safety throughout research workflows

### Integration Points
- FastAPI router at `/research/*` endpoints
- MCP (Model Context Protocol) integration for tool access
- Enhanced medical query engine integration
- Clinical reasoning system integration
- Healthcare logging infrastructure
- PHI monitoring system

## API Endpoints

### POST /research/clinical-research
Perform comprehensive clinical research with agentic RAG capabilities

### POST /research/literature-search
Conduct focused medical literature searches

### GET /research/health
Health check and capability reporting

## Data Structures

### ResearchRequest
Request model for clinical research with query, type, and clinical context

### LiteratureSearchRequest
Request model for focused literature searches

### Research Result Structures
- Comprehensive research findings with evidence ranking
- Source quality assessment and reliability scoring
- Clinical context integration and synthesis
- Recommendation confidence scoring

## Research Query Types

### 1. General Inquiry
Broad medical research questions requiring comprehensive literature review

### 2. Differential Diagnosis
Literature support for diagnostic reasoning and condition comparison

### 3. Drug Interaction
Comprehensive medication interaction and safety analysis

### 4. Literature Research
Focused searches on specific medical topics or questions

### 5. Clinical Guidelines
Evidence-based guideline research and protocol analysis

## Evidence Quality Framework

### Source Prioritization
1. **Systematic Reviews and Meta-Analyses**: Highest priority for comprehensive evidence
2. **Randomized Controlled Trials**: Primary source for treatment effectiveness
3. **Cohort Studies**: Important for prognosis and risk factors
4. **Case-Control Studies**: Useful for rare conditions and risk assessment
5. **Case Series and Reports**: Supplementary evidence for rare conditions
6. **Expert Opinion**: Contextual support when high-quality evidence is limited

### Research Confidence Scoring
- **High Confidence (>85%)**: Multiple high-quality studies with consistent findings
- **Moderate Confidence (65-85%)**: Good quality evidence with some limitations
- **Low Confidence (<65%)**: Limited or conflicting evidence requiring further research

## Performance Metrics
- Research comprehensiveness and depth
- Evidence quality and source reliability
- Clinical relevance and applicability
- Research completion time and efficiency
- User satisfaction with research findings
- Citation accuracy and completeness
