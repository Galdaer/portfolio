# Healthcare AI Documentation Instructions

## Purpose

Comprehensive documentation guidance for healthcare AI systems emphasizing medical compliance documentation, PHI-safe examples, and modern documentation automation tools.

## Healthcare Documentation Framework

### Medical Compliance Documentation

````python
# ✅ CORRECT: Healthcare documentation patterns
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import textwrap

@dataclass
class HealthcareDocumentationStandard:
    """Documentation standards for healthcare AI systems."""

    compliance_frameworks: List[str]
    phi_safety_level: str
    medical_disclaimer_required: bool
    audit_documentation: bool

    def generate_medical_disclaimer(self) -> str:
        """Generate medical disclaimer for healthcare AI documentation."""

        return textwrap.dedent("""
        HEALTHCARE PROVIDER SUPPORT SYSTEM:
        This system supports clinical decision-making for healthcare providers.
        It does not replace clinical judgment or professional medical expertise.
        All medical decisions remain the responsibility of qualified healthcare professionals.

        HIPAA COMPLIANCE:
        This system is designed to protect patient health information (PHI).
        All PHI handling follows HIPAA security and privacy requirements.

        REGULATORY COMPLIANCE:
        This system complies with applicable healthcare regulations including
        HIPAA, HITECH, and relevant state healthcare privacy laws.
        """).strip()

    def generate_phi_safety_documentation(self) -> str:
        """Generate PHI safety documentation patterns."""

        return textwrap.dedent("""
        PHI SAFETY GUIDELINES:

        1. SYNTHETIC DATA ONLY: All examples use synthetic, non-real patient data
        2. DATA MINIMIZATION: Process only necessary PHI for specific functions
        3. ENCRYPTION: All PHI stored with AES-256 encryption at rest
        4. ACCESS LOGGING: All PHI access logged for audit compliance
        5. ANONYMIZATION: Use patient hashes for logging and debugging

        SAFE EXAMPLE PATTERNS:
        - Patient ID: Use "PAT001", "PAT002" format
        - Provider ID: Use "PROV001", "DOC001" format
        - Encounter ID: Use "ENC001", "VISIT001" format
        - Phone Numbers: Use "(555) 123-4567" format
        - SSN: Use "XXX-XX-XXXX" or "123-45-6789" (clearly synthetic)

        UNSAFE PATTERNS TO AVOID:
        - Real-looking names: "John Smith", "Mary Johnson"
        - Real area codes: "(212) 555-1234", "(415) 555-5678"
        - Sequential SSNs: "123-45-6789", "123-45-6790"
        - Real addresses or specific locations
        """).strip()

class HealthcareDocumentationGenerator:
    """Generate comprehensive healthcare AI documentation."""

    def __init__(self) -> None:
        self.doc_standards = HealthcareDocumentationStandard(
            compliance_frameworks=["HIPAA", "HITECH", "FDA Software"],
            phi_safety_level="SYNTHETIC_ONLY",
            medical_disclaimer_required=True,
            audit_documentation=True
        )

    def document_healthcare_module(
        self,
        module_name: str,
        module_purpose: str,
        medical_functions: List[str],
        phi_handling: bool = False
    ) -> str:
        """Generate comprehensive documentation for healthcare module."""

        documentation = f"""
# {module_name}

## Purpose
{module_purpose}

{self.doc_standards.generate_medical_disclaimer()}

## Medical Safety Compliance

### Administrative Functions Only
This module provides administrative and documentation support functions:
"""

        for function in medical_functions:
            documentation += f"- {function}: Administrative processing only, no medical advice\n"

        if phi_handling:
            documentation += f"\n## PHI Handling Documentation\n\n"
            documentation += self.doc_standards.generate_phi_safety_documentation()

        documentation += self._generate_usage_examples(module_name, medical_functions)
        documentation += self._generate_testing_documentation(module_name)
        documentation += self._generate_compliance_documentation()

        return documentation

    def _generate_usage_examples(self, module_name: str, functions: List[str]) -> str:
        """Generate PHI-safe usage examples."""

        examples = f"\n## Usage Examples\n\n"
        examples += "### Safe Synthetic Data Examples\n\n"

        examples += """```python
# ✅ CORRECT: PHI-safe example with synthetic data
from healthcare.{module_name} import {module_class}

# Initialize with synthetic test data
processor = {module_class}()

# Process synthetic patient data
synthetic_patient = {{
    "patient_id": "PAT001",
    "demographics": {{
        "age": 45,
        "gender": "M",
        "insurance": "Synthetic Insurance Co"
    }},
    "encounter_id": "ENC001",
    "provider_id": "PROV001"
}}

# Process administrative data (no medical advice)
result = processor.process_administrative_data(synthetic_patient)

# Safe logging with anonymization
logger.info(f"Processed patient: {{result.anonymize_for_logging()}}")
````

### Medical Safety Example

````python
# ✅ CORRECT: Medical safety compliance example
def process_patient_inquiry(inquiry: str) -> Dict[str, Any]:
    \"\"\"
    Process patient inquiry with medical safety compliance.

    MEDICAL SAFETY: This function provides administrative guidance only.
    No medical advice, diagnosis, or treatment recommendations are provided.
    \"\"\"

    if any(word in inquiry.lower() for word in ["medication", "treatment", "diagnosis"]):
        return {{
            "response_type": "administrative_referral",
            "message": "Please consult with your healthcare provider for medical questions.",
            "referral_required": True,
            "medical_advice_provided": False
        }}

    # Process administrative inquiry
    return {{
        "response_type": "administrative_support",
        "message": "Administrative support provided",
        "medical_advice_provided": False
    }}
```""".format(
            module_name=module_name.lower(),
            module_class=module_name.replace("_", "").title()
        )

        return examples

    def _generate_testing_documentation(self, module_name: str) -> str:
        """Generate testing documentation section."""

        return f"""
## Testing Guidelines

### PHI-Safe Testing
All testing uses synthetic data that contains no real PHI:

```python
# ✅ CORRECT: PHI-safe test data
@pytest.fixture
def synthetic_healthcare_data():
    return {{
        "patients": [
            {{
                "patient_id": "PAT001",
                "demographics": {{"age": 45, "gender": "M"}},
                "synthetic_flag": True
            }}
        ],
        "encounters": [
            {{
                "encounter_id": "ENC001",
                "patient_id": "PAT001",
                "provider_id": "PROV001",
                "date": "2024-01-15"
            }}
        ]
    }}

# Test medical safety compliance
@pytest.mark.medical_safety
def test_no_medical_advice_generated(synthetic_healthcare_data):
    processor = {module_name.title()}Processor()
    result = processor.process_data(synthetic_healthcare_data["patients"][0])

    assert result["medical_advice_provided"] is False
    assert "consult your healthcare provider" in result.get("message", "").lower()
````

### Compliance Testing

```bash
# Run healthcare compliance tests
pytest tests/ -v -m "medical_safety"
pytest tests/ -v -m "phi_safe"
pytest tests/ -v -m "compliance"
```

"""

    def _generate_compliance_documentation(self) -> str:
        """Generate compliance documentation section."""

        return """

## Compliance Documentation

### HIPAA Compliance

- **PHI Protection**: All patient data encrypted at rest and in transit
- **Access Controls**: Role-based access with audit logging
- **Data Minimization**: Process only necessary PHI for specific functions
- **Audit Trail**: Comprehensive logging of all PHI access and operations

### Medical Safety Compliance

- **No Medical Advice**: System provides administrative support only
- **Provider Referrals**: All medical questions referred to healthcare providers
- **Documentation Standards**: Follows healthcare documentation best practices
- **Error Handling**: Medical safety failures result in provider referral

### Regulatory Alignment

- **FDA Software Guidelines**: Follows FDA guidance for healthcare software
- **State Healthcare Laws**: Complies with applicable state healthcare regulations
- **Professional Standards**: Aligns with healthcare professional documentation standards

## Audit and Monitoring

### Required Logging

```python
# ✅ CORRECT: Healthcare audit logging
@audit_healthcare_access
def process_patient_data(patient_id: str, purpose: str) -> Dict[str, Any]:
    \"\"\"Process patient data with comprehensive audit logging.\"\"\"

    # Log access for audit trail
    audit_logger.log_phi_access(
        user_id=get_current_user_id(),
        patient_hash=hash_patient_id(patient_id),
        access_purpose=purpose,
        timestamp=datetime.now(),
        compliance_framework="HIPAA"
    )

    # Process data with protection
    result = secure_processor.process(patient_id)

    return result
```

### Monitoring Requirements

- **Performance Monitoring**: Response times for healthcare operations
- **Security Monitoring**: PHI access patterns and anomaly detection
- **Compliance Monitoring**: Audit log completeness and integrity
- **Error Monitoring**: Medical safety compliance failures
  """

````

### Modern Documentation Tools Integration
```python
# ✅ CORRECT: Modern documentation automation for healthcare
class ModernHealthcareDocumentation:
    """Integrate modern documentation tools for healthcare AI."""

    def setup_sphinx_healthcare_docs(self) -> Dict[str, str]:
        """Configure Sphinx for healthcare documentation."""

        sphinx_config = {
            "conf_py": """
# Healthcare AI Documentation Configuration
import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

project = 'Intelluxe Healthcare AI'
copyright = '2024, Intelluxe AI'
author = 'Intelluxe AI Team'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
    'myst_parser'  # For Markdown support
]

# Healthcare-specific documentation settings
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Medical disclaimer in all pages
html_theme_options = {
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Auto-generated medical disclaimer
rst_prolog = '''
.. warning::
   MEDICAL DISCLAIMER: This system provides administrative support only.
   It does NOT provide medical advice, diagnosis, or treatment recommendations.
   All medical decisions must be made by qualified healthcare professionals.
'''
            """,

            "index_rst": """
Healthcare AI Documentation
==========================

.. warning::
   MEDICAL DISCLAIMER: This system provides administrative and documentation support only.
   It does NOT provide medical advice, diagnosis, or treatment recommendations.
   All medical decisions must be made by qualified healthcare professionals.

Welcome to the Intelluxe Healthcare AI documentation. This system provides
privacy-first healthcare AI capabilities for on-premise clinical deployment.

Core Modules
------------

.. toctree::
   :maxdepth: 2
   :caption: Core Healthcare Modules:

   core/medical
   core/agents
   core/orchestration
   agents/document_processor
   agents/intake
   mcps/healthcare

Compliance and Safety
--------------------

.. toctree::
   :maxdepth: 2
   :caption: Compliance Documentation:

   compliance/hipaa
   compliance/medical_safety
   compliance/phi_protection
   compliance/audit_logging

Development
-----------

.. toctree::
   :maxdepth: 2
   :caption: Development Guides:

   development/setup
   development/testing
   development/modern_tools
   development/deployment
            """
        }

        return sphinx_config

    def setup_mkdocs_healthcare(self) -> Dict[str, str]:
        """Configure MkDocs for healthcare documentation."""

        return {
            "mkdocs_yml": """
site_name: Intelluxe Healthcare AI
site_description: Privacy-First Healthcare AI System Documentation
site_author: Intelluxe AI Team

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.highlight
    - content.code.copy
  palette:
    - scheme: default
      primary: blue
      accent: light-blue

plugins:
  - search
  - autorefs
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
            show_source: true

nav:
  - Home: index.md
  - Medical Safety: medical_safety.md
  - Core Modules:
    - Medical: core/medical.md
    - Agents: core/agents.md
    - Orchestration: core/orchestration.md
  - Healthcare Agents:
    - Document Processor: agents/document_processor.md
    - Intake Agent: agents/intake.md
  - Compliance:
    - HIPAA Compliance: compliance/hipaa.md
    - PHI Protection: compliance/phi_protection.md
    - Audit Logging: compliance/audit_logging.md
  - Development:
    - Setup Guide: development/setup.md
    - Testing: development/testing.md
    - Modern Tools: development/modern_tools.md

markdown_extensions:
  - admonition
  - codehilite
  - pymdownx.superfences
  - pymdownx.tabbed
  - toc:
      permalink: true
            """,

            "index_md": """
# Intelluxe Healthcare AI Documentation

!!! warning "Medical Disclaimer"
    This system provides administrative and documentation support only.
    It does NOT provide medical advice, diagnosis, or treatment recommendations.
    All medical decisions must be made by qualified healthcare professionals.

Welcome to the Intelluxe Healthcare AI documentation. This system provides
privacy-first healthcare AI capabilities for on-premise clinical deployment.

## Key Features

- **Privacy-First**: All PHI/PII remains on-premise
- **Medical Safety**: Administrative support only, no medical advice
- **HIPAA Compliant**: Comprehensive PHI protection and audit logging
- **Modern Architecture**: Modular design with AI agent orchestration

## Quick Start

```bash
# Set up development environment
make install && make deps && make hooks

# Run comprehensive validation
make lint && make validate

# Generate synthetic healthcare data
python3 scripts/generate_synthetic_healthcare_data.py --doctors 75 --patients 2500
````

## Safety and Compliance

This system maintains strict medical safety and HIPAA compliance:

- ✅ Administrative functions only
- ✅ No medical advice generation
- ✅ PHI encryption and protection
- ✅ Comprehensive audit logging
- ✅ Synthetic data for testing

"""
}

    def setup_automated_documentation_pipeline(self) -> Dict[str, str]:
        """Set up automated documentation generation pipeline."""

        return {
            "github_workflow": """

name: Healthcare Documentation

on:
push:
branches: [main]
paths: - 'core/**' - 'agents/**' - 'mcps/**' - 'docs/**'
pull_request:
branches: [main]

jobs:
build-docs:
runs-on: self-hosted

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install documentation dependencies
      run: |
        pip install sphinx sphinx-rtd-theme myst-parser
        pip install mkdocs mkdocs-material mkdocstrings
        pip install -r requirements-docs.txt

    - name: Generate API documentation
      run: |
        sphinx-apidoc -o docs/api core/ agents/ mcps/

    - name: Build Sphinx documentation
      run: |
        cd docs/
        make html

    - name: Build MkDocs documentation
      run: |
        mkdocs build

    - name: Validate medical disclaimers
      run: |
        python3 scripts/validate-medical-disclaimers.py docs/

    - name: Deploy to GitHub Pages
      if: github.ref == 'refs/heads/main'
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./site
            """,

            "pre_commit_docs": """

# Pre-commit hook for documentation validation

repos:

- repo: local
  hooks:
  - id: healthcare-docs-validation
    name: Healthcare Documentation Validation
    entry: python3 scripts/validate-healthcare-docs.py
    language: python
    files: '\\.(md|rst|py)$'
  - id: medical-disclaimer-check
    name: Medical Disclaimer Check
    entry: python3 scripts/check-medical-disclaimers.py
    language: python
    files: '\\.(md|rst)$'
  - id: phi-safety-validation
    name: PHI Safety Documentation Check
    entry: python3 scripts/validate-phi-safety-docs.py
    language: python
    files: '\\.(md|rst|py)$'
    """
    }

````

### Healthcare-Specific Documentation Patterns
```python
# ✅ CORRECT: Healthcare documentation automation
class HealthcareDocumentationAutomation:
    """Automate healthcare-specific documentation generation."""

    def generate_medical_module_docs(self, module_path: str) -> str:
        """Generate documentation for medical modules with compliance."""

        doc_template = """
# {module_name}

{medical_disclaimer}

## Module Purpose
{module_purpose}

## Medical Safety Compliance
This module provides administrative and documentation support only.
It does NOT provide medical advice, diagnosis, or treatment recommendations.

## PHI Protection
All patient data handling follows HIPAA security requirements:
- Encryption at rest and in transit
- Access logging for audit compliance
- Data minimization principles
- Anonymization for logging

## API Reference

### Classes
{class_documentation}

### Functions
{function_documentation}

## Usage Examples

### PHI-Safe Examples
{phi_safe_examples}

### Medical Safety Examples
{medical_safety_examples}

## Testing
{testing_documentation}

## Compliance Validation
{compliance_documentation}
        """

        return self._populate_documentation_template(doc_template, module_path)

    def generate_agent_documentation(self, agent_path: str) -> str:
        """Generate healthcare agent documentation."""

        agent_doc_template = """
# {agent_name} Healthcare Agent

{medical_disclaimer}

## Agent Purpose
{agent_purpose}

## Medical Safety Framework
This agent operates within strict medical safety boundaries:
- Administrative and documentation support only
- No medical advice, diagnosis, or treatment recommendations
- All medical questions referred to healthcare providers
- Compliance with healthcare professional standards

## Agent Capabilities
{agent_capabilities}

## PHI Handling
{phi_handling_documentation}

## Integration Examples
{integration_examples}

## Performance Metrics
{performance_documentation}

## Compliance Testing
{compliance_testing}
        """

        return self._populate_agent_template(agent_doc_template, agent_path)

    def validate_documentation_compliance(self, doc_content: str) -> Dict[str, Any]:
        """Validate documentation meets healthcare compliance standards."""

        compliance_checks = {
            "medical_disclaimer_present": self._check_medical_disclaimer(doc_content),
            "phi_safety_documented": self._check_phi_safety_docs(doc_content),
            "no_medical_advice": self._check_no_medical_advice(doc_content),
            "synthetic_data_only": self._check_synthetic_data_usage(doc_content),
            "audit_logging_documented": self._check_audit_documentation(doc_content)
        }

        overall_compliance = all(compliance_checks.values())

        return {
            "compliant": overall_compliance,
            "checks": compliance_checks,
            "recommendations": self._generate_compliance_recommendations(compliance_checks)
        }
````

### Documentation Automation Scripts

```bash
#!/bin/bash
# scripts/generate-healthcare-docs.sh

# Generate comprehensive healthcare documentation
echo "🏥 Generating Healthcare AI Documentation..."

# Clean previous builds
rm -rf docs/_build site/

# Generate API documentation with medical disclaimers
echo "📋 Generating API documentation..."
sphinx-apidoc -o docs/api core/ agents/ mcps/ \
  --separate --module-first \
  --doc-project="Healthcare AI API" \
  --doc-author="Intelluxe AI Team"

# Add medical disclaimers to all generated files
python3 scripts/add-medical-disclaimers.py docs/api/

# Build Sphinx documentation
echo "📚 Building Sphinx documentation..."
cd docs/
make html
cd ..

# Build MkDocs documentation
echo "📖 Building MkDocs documentation..."
mkdocs build

# Validate healthcare compliance
echo "✅ Validating healthcare compliance..."
python3 scripts/validate-healthcare-docs.py docs/ site/

# Generate compliance report
echo "📊 Generating compliance report..."
python3 scripts/generate-compliance-report.py > docs/compliance_report.md

echo "✅ Healthcare documentation generated successfully!"
echo "📁 Sphinx docs: docs/_build/html/"
echo "📁 MkDocs site: site/"
echo "📋 Compliance report: docs/compliance_report.md"
```

## Healthcare Documentation Best Practices

### Medical Compliance Requirements

- **Medical Disclaimer**: Required on all healthcare-related documentation
- **PHI Safety**: All examples use synthetic data with clear labeling
- **Administrative Scope**: Clearly define administrative vs. clinical boundaries
- **Provider Referrals**: Document when to refer users to healthcare providers

### Modern Tool Integration

- **Sphinx**: For comprehensive API documentation with medical compliance
- **MkDocs**: For user-friendly documentation with healthcare themes
- **Read the Docs**: Automated documentation hosting with version control
- **GitHub Pages**: Automated deployment with compliance validation

### Automation and Validation

- **Pre-commit Hooks**: Validate medical disclaimers and PHI safety
- **CI/CD Integration**: Automated documentation builds with compliance checks
- **Compliance Scanning**: Automated detection of medical advice or PHI exposure
- **Performance Metrics**: Document healthcare-specific performance requirements

Remember: Healthcare documentation must maintain strict medical safety standards while providing comprehensive technical guidance for administrative healthcare AI systems.
