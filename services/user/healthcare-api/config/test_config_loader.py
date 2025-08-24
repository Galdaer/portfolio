#!/usr/bin/env python3
"""
Configuration Loader Test
Validates that configuration files are properly loaded and structured
"""

import logging
import sys
from pathlib import Path

from config_loader import ConfigLoader, get_healthcare_config


def test_config_loader_initialization():
    """Test configuration loader initialization"""

    config_dir = Path(__file__).parent
    loader = ConfigLoader(str(config_dir))

    assert loader.config_dir == config_dir
    assert isinstance(loader.config_cache, dict)


def test_load_intake_config():
    """Test loading intake configuration"""

    config = get_healthcare_config()

    # Validate intake agent configuration
    assert hasattr(config, "intake_agent")
    intake_config = config.intake_agent

    # Test disclaimers
    assert isinstance(intake_config.disclaimers, list)
    assert len(intake_config.disclaimers) > 0
    assert "administrative support only" in intake_config.disclaimers[0].lower()

    # Test voice processing configuration
    assert hasattr(intake_config, "voice_processing")
    voice_config = intake_config.voice_processing

    assert isinstance(voice_config.enabled, bool)
    assert isinstance(voice_config.confidence_threshold, float)
    assert 0.0 <= voice_config.confidence_threshold <= 1.0
    assert isinstance(voice_config.field_mappings, dict)

    # Test field mappings
    expected_fields = [
        "first_name", "last_name", "date_of_birth",
        "contact_phone", "contact_email", "insurance_primary",
    ]

    for field in expected_fields:
        assert field in voice_config.field_mappings
        assert isinstance(voice_config.field_mappings[field], list)
        assert len(voice_config.field_mappings[field]) > 0

    # Test medical keywords
    assert isinstance(voice_config.medical_keywords, dict)
    assert "symptoms" in voice_config.medical_keywords
    assert "medications" in voice_config.medical_keywords


def test_load_workflow_config():
    """Test loading workflow configuration"""

    config = get_healthcare_config()

    # Validate workflow configuration
    assert hasattr(config, "workflows")
    workflow_config = config.workflows

    # Test workflow types
    assert isinstance(workflow_config.types, dict)
    expected_workflow_types = [
        "intake_to_billing", "voice_intake_workflow",
        "clinical_decision", "comprehensive_analysis",
    ]

    for workflow_type in expected_workflow_types:
        assert workflow_type in workflow_config.types
        type_config = workflow_config.types[workflow_type]
        assert hasattr(type_config, "name")
        assert hasattr(type_config, "description")
        assert hasattr(type_config, "timeout_seconds")
        assert isinstance(type_config.timeout_seconds, int)
        assert type_config.timeout_seconds > 0

    # Test agent specializations
    assert isinstance(workflow_config.agent_specializations, dict)
    expected_agents = ["intake", "transcription", "clinical_analysis", "billing"]

    for agent in expected_agents:
        assert agent in workflow_config.agent_specializations
        agent_config = workflow_config.agent_specializations[agent]
        assert hasattr(agent_config, "name")
        assert hasattr(agent_config, "capabilities")
        assert isinstance(agent_config.capabilities, list)

    # Test step definitions
    assert isinstance(workflow_config.step_definitions, dict)
    assert "intake_to_billing" in workflow_config.step_definitions

    intake_to_billing_steps = workflow_config.step_definitions["intake_to_billing"]
    assert len(intake_to_billing_steps) > 0

    for step in intake_to_billing_steps:
        assert hasattr(step, "step_name")
        assert hasattr(step, "agent_specialization")
        assert hasattr(step, "dependencies")
        assert isinstance(step.dependencies, list)


def test_document_requirements_config():
    """Test document requirements configuration"""

    config = get_healthcare_config()
    doc_req = config.intake_agent.document_requirements

    # Test base documents
    assert isinstance(doc_req.base_documents, list)
    assert len(doc_req.base_documents) > 0
    assert any("id" in doc.lower() for doc in doc_req.base_documents)
    assert any("insurance" in doc.lower() for doc in doc_req.base_documents)

    # Test type-specific documents
    assert isinstance(doc_req.new_patient_additional, list)
    assert len(doc_req.new_patient_additional) > 0
    assert any("medical history" in doc.lower() for doc in doc_req.new_patient_additional)

    assert isinstance(doc_req.specialist_additional, list)
    assert len(doc_req.specialist_additional) > 0
    assert any("referral" in doc.lower() for doc in doc_req.specialist_additional)


def test_validation_config():
    """Test validation configuration"""

    config = get_healthcare_config()

    # Test validation configuration exists
    assert hasattr(config, "validation")
    validation_config = config.validation

    # Test field validation rules
    assert hasattr(validation_config, "field_validation")
    assert isinstance(validation_config.field_validation, dict)

    # Test specific field validations
    if "first_name" in validation_config.field_validation:
        first_name_validation = validation_config.field_validation["first_name"]
        assert "required" in first_name_validation
        assert "pattern" in first_name_validation

    if "contact_email" in validation_config.field_validation:
        email_validation = validation_config.field_validation["contact_email"]
        assert "format" in email_validation
        assert email_validation["format"] == "email"


def test_orchestration_config():
    """Test orchestration configuration"""

    config = get_healthcare_config()

    # Test orchestration configuration
    assert hasattr(config, "orchestration")
    orch_config = config.orchestration

    # Test basic settings
    assert hasattr(orch_config, "max_concurrent_workflows")
    assert isinstance(orch_config.max_concurrent_workflows, int)
    assert orch_config.max_concurrent_workflows > 0

    assert hasattr(orch_config, "workflow_cleanup_delay_seconds")
    assert isinstance(orch_config.workflow_cleanup_delay_seconds, int)

    # Test error handling configuration
    assert hasattr(orch_config, "error_handling")
    assert isinstance(orch_config.error_handling, dict)

    # Test monitoring configuration
    assert hasattr(orch_config, "monitoring")
    assert isinstance(orch_config.monitoring, dict)


def test_configuration_completeness():
    """Test that all required configuration sections are present"""

    config = get_healthcare_config()

    # Test main sections
    required_sections = ["intake_agent", "workflows", "orchestration", "validation"]
    for section in required_sections:
        assert hasattr(config, section), f"Missing required configuration section: {section}"

    # Test intake agent subsections
    intake_required = ["disclaimers", "voice_processing", "document_requirements"]
    for subsection in intake_required:
        assert hasattr(config.intake_agent, subsection), f"Missing intake agent subsection: {subsection}"

    # Test workflow subsections
    workflow_required = ["types", "agent_specializations", "step_definitions"]
    for subsection in workflow_required:
        assert hasattr(config.workflows, subsection), f"Missing workflow subsection: {subsection}"


def test_voice_processing_field_mappings():
    """Test voice processing field mappings are comprehensive"""

    config = get_healthcare_config()
    field_mappings = config.intake_agent.voice_processing.field_mappings

    # Test critical intake fields are present
    critical_fields = [
        "first_name", "last_name", "date_of_birth", "contact_phone",
        "insurance_primary", "chief_complaint",
    ]

    for field in critical_fields:
        assert field in field_mappings, f"Missing critical field mapping: {field}"

        patterns = field_mappings[field]
        assert len(patterns) >= 2, f"Field {field} should have multiple pattern variations"

        # Test that patterns are meaningful
        if field == "first_name":
            assert any("first name" in pattern for pattern in patterns)
            assert any("given name" in pattern for pattern in patterns)

        elif field == "contact_phone":
            assert any("phone" in pattern for pattern in patterns)
            assert any("number" in pattern for pattern in patterns)


def test_workflow_step_definitions_integrity():
    """Test workflow step definitions have proper dependencies"""

    config = get_healthcare_config()
    step_definitions = config.workflows.step_definitions

    # Test intake_to_billing workflow
    if "intake_to_billing" in step_definitions:
        steps = step_definitions["intake_to_billing"]
        step_names = [step.step_name for step in steps]

        # Validate dependencies exist
        for step in steps:
            for dependency in step.dependencies:
                assert dependency in step_names, f"Step {step.step_name} has invalid dependency: {dependency}"

        # Test expected steps are present
        expected_steps = ["patient_intake", "medical_transcription"]
        for expected_step in expected_steps:
            assert expected_step in step_names, f"Missing expected step: {expected_step}"


def test_configuration_caching():
    """Test configuration caching works properly"""

    # Get configuration twice
    config1 = get_healthcare_config()
    config2 = get_healthcare_config()

    # Should be the same object due to caching
    assert config1 is config2

    # Test reload functionality
    config3 = get_healthcare_config(reload=True)
    assert config3 is not config1  # Should be different after reload


def test_environment_overrides():
    """Test environment variable overrides work"""

    import os

    # Set environment variable
    original_value = os.environ.get("VOICE_CONFIDENCE_THRESHOLD")
    os.environ["VOICE_CONFIDENCE_THRESHOLD"] = "0.9"

    try:
        # Reload configuration to apply override
        config = get_healthcare_config(reload=True)

        # Check that override was applied
        assert config.intake_agent.voice_processing.confidence_threshold == 0.9

    finally:
        # Restore original environment
        if original_value is not None:
            os.environ["VOICE_CONFIDENCE_THRESHOLD"] = original_value
        else:
            os.environ.pop("VOICE_CONFIDENCE_THRESHOLD", None)


def main():
    """Run configuration tests"""

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    print("🏥 Healthcare Configuration Loader Test")
    print("="*50)

    try:
        # Run tests
        test_config_loader_initialization()
        print("✅ Configuration loader initialization")

        test_load_intake_config()
        print("✅ Intake configuration loading")

        test_load_workflow_config()
        print("✅ Workflow configuration loading")

        test_document_requirements_config()
        print("✅ Document requirements configuration")

        test_validation_config()
        print("✅ Validation configuration")

        test_orchestration_config()
        print("✅ Orchestration configuration")

        test_configuration_completeness()
        print("✅ Configuration completeness")

        test_voice_processing_field_mappings()
        print("✅ Voice processing field mappings")

        test_workflow_step_definitions_integrity()
        print("✅ Workflow step definitions integrity")

        test_configuration_caching()
        print("✅ Configuration caching")

        test_environment_overrides()
        print("✅ Environment variable overrides")

        print("\n🎉 All configuration tests passed!")
        print("\n📋 Configuration Summary:")

        config = get_healthcare_config()
        print(f"   Disclaimers: {len(config.intake_agent.disclaimers)}")
        print(f"   Voice field mappings: {len(config.intake_agent.voice_processing.field_mappings)}")
        print(f"   Workflow types: {len(config.workflows.types)}")
        print(f"   Agent specializations: {len(config.workflows.agent_specializations)}")
        print(f"   Step definitions: {len(config.workflows.step_definitions)}")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
