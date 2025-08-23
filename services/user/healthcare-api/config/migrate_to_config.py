#!/usr/bin/env python3
"""
Configuration Migration Utility
Refactors existing healthcare agents to use external configuration files
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from config_loader import get_healthcare_config
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("config_migration")


class AgentConfigMigrator:
    """
    Migrates healthcare agents to use external configuration
    
    Refactors embedded configuration data into external YAML files
    and updates agent code to use the configuration loader.
    """
    
    def __init__(self, healthcare_api_dir: str):
        self.healthcare_api_dir = Path(healthcare_api_dir)
        self.config = get_healthcare_config()
        
        # Files to migrate
        self.agent_files = [
            "agents/intake/intake_agent.py",
            "core/orchestration/workflow_orchestrator.py"
        ]
        
        logger.info(f"Configuration migrator initialized for: {self.healthcare_api_dir}")
    
    def migrate_all_agents(self) -> bool:
        """Migrate all healthcare agents to use external configuration"""
        
        try:
            success_count = 0
            
            for agent_file in self.agent_files:
                file_path = self.healthcare_api_dir / agent_file
                
                if file_path.exists():
                    logger.info(f"Migrating {agent_file}...")
                    
                    if self._migrate_agent_file(file_path):
                        success_count += 1
                        logger.info(f"✅ Successfully migrated {agent_file}")
                    else:
                        logger.error(f"❌ Failed to migrate {agent_file}")
                else:
                    logger.warning(f"⚠️  Agent file not found: {file_path}")
            
            logger.info(f"Migration completed: {success_count}/{len(self.agent_files)} files migrated")
            return success_count == len([f for f in self.agent_files if (self.healthcare_api_dir / f).exists()])
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            return False
    
    def _migrate_agent_file(self, file_path: Path) -> bool:
        """Migrate a single agent file to use external configuration"""
        
        try:
            # Read original file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Create backup
            backup_path = file_path.with_suffix('.py.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            logger.debug(f"Created backup: {backup_path}")
            
            # Apply migrations based on file type
            migrated_content = original_content
            
            if "intake_agent.py" in str(file_path):
                migrated_content = self._migrate_intake_agent(migrated_content)
            
            elif "workflow_orchestrator.py" in str(file_path):
                migrated_content = self._migrate_workflow_orchestrator(migrated_content)
            
            # Write migrated file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(migrated_content)
            
            logger.debug(f"Migrated file written: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate {file_path}: {str(e)}")
            return False
    
    def _migrate_intake_agent(self, content: str) -> str:
        """Migrate intake agent to use external configuration"""
        
        # Add configuration import
        import_pattern = r"from core\.orchestration import WorkflowType, workflow_orchestrator"
        import_replacement = """from core.orchestration import WorkflowType, workflow_orchestrator
from config.config_loader import get_healthcare_config"""
        
        content = re.sub(import_pattern, import_replacement, content)
        
        # Replace embedded field_mappings in VoiceIntakeProcessor
        field_mappings_pattern = r'self\.field_mappings = \{[^}]+\}(?:\s*\})*'
        field_mappings_replacement = """# Load field mappings from configuration
        config = get_healthcare_config()
        self.field_mappings = config.intake_agent.voice_processing.field_mappings"""
        
        content = re.sub(field_mappings_pattern, field_mappings_replacement, content, flags=re.DOTALL)
        
        # Replace embedded disclaimers
        disclaimers_pattern = r'self\.disclaimers = \[[^\]]+\]'
        disclaimers_replacement = """# Load disclaimers from configuration
        config = get_healthcare_config()
        self.disclaimers = config.intake_agent.disclaimers"""
        
        content = re.sub(disclaimers_pattern, disclaimers_replacement, content, flags=re.DOTALL)
        
        # Replace hardcoded required documents
        required_docs_patterns = [
            r'required_documents = \["Government-issued photo ID"[^\]]+\]',
            r'required_documents\.extend\([^\)]+\)'
        ]
        
        for pattern in required_docs_patterns:
            content = re.sub(pattern, 
                           '# Documents loaded from configuration\n        required_documents = self._get_required_documents(intake_type, patient_type)', 
                           content, flags=re.DOTALL)
        
        # Add configuration-based helper methods
        helper_methods = '''
    def _get_required_documents(self, intake_type: str, patient_type: str = "existing") -> List[str]:
        """Get required documents from configuration based on intake and patient type"""
        config = get_healthcare_config()
        doc_req = config.intake_agent.document_requirements
        
        # Start with base documents
        documents = doc_req.base_documents.copy()
        
        # Add type-specific documents
        if patient_type == "new":
            documents.extend(doc_req.new_patient_additional)
        
        if intake_type == "specialist":
            documents.extend(doc_req.specialist_additional)
        elif intake_type == "insurance_verification":
            return doc_req.insurance_verification
        elif intake_type == "appointment_scheduling":
            return doc_req.appointment_scheduling
        elif intake_type == "general_intake":
            return doc_req.general_intake
        
        return documents
    
    def _get_next_steps(self, intake_type: str) -> List[str]:
        """Get next steps from configuration based on intake type"""
        config = get_healthcare_config()
        templates = config.intake_agent.next_steps_templates
        return templates.get(intake_type, templates.get("general_intake", []))
    
    def _get_required_fields(self, intake_type: str) -> List[str]:
        """Get required fields from configuration based on intake type"""
        config = get_healthcare_config()
        return config.intake_agent.required_fields.get(intake_type, [])'''
        
        # Insert helper methods before the cleanup method
        cleanup_pattern = r'(\s+async def cleanup\(self\) -> None:)'
        content = re.sub(cleanup_pattern, helper_methods + r'\1', content)
        
        # Replace hardcoded next_steps with configuration calls
        next_steps_patterns = [
            r'next_steps = \[[^\]]+\]',
            r'next_steps\.extend\([^\)]+\)'
        ]
        
        for pattern in next_steps_patterns:
            content = re.sub(pattern, 'next_steps = self._get_next_steps(intake_type)', content)
        
        return content
    
    def _migrate_workflow_orchestrator(self, content: str) -> str:
        """Migrate workflow orchestrator to use external configuration"""
        
        # Add configuration import
        import_pattern = r"from core\.enhanced_sessions import EnhancedSessionManager"
        import_replacement = """from core.enhanced_sessions import EnhancedSessionManager
from config.config_loader import get_healthcare_config"""
        
        content = re.sub(import_pattern, import_replacement, content)
        
        # Replace embedded workflow definitions
        workflow_init_pattern = r'self\.workflow_definitions = self\._initialize_workflow_definitions\(\)'
        workflow_init_replacement = """# Load workflow definitions from configuration
        self.workflow_definitions = self._load_workflow_definitions_from_config()"""
        
        content = re.sub(workflow_init_pattern, workflow_init_replacement, content)
        
        # Replace the _initialize_workflow_definitions method
        initialize_method_pattern = r'def _initialize_workflow_definitions\(self\)[^}]+\}'
        
        new_method = '''def _load_workflow_definitions_from_config(self) -> Dict[WorkflowType, List[WorkflowStep]]:
        """Load workflow definitions from external configuration"""
        config = get_healthcare_config()
        definitions = {}
        
        # Map configuration workflow names to WorkflowType enums
        workflow_type_mapping = {
            "intake_to_billing": WorkflowType.INTAKE_TO_BILLING,
            "voice_intake_workflow": WorkflowType.VOICE_INTAKE_WORKFLOW,
            "clinical_decision": WorkflowType.CLINICAL_DECISION,
            "comprehensive_analysis": WorkflowType.COMPREHENSIVE_ANALYSIS
        }
        
        # Map configuration agent names to AgentSpecialization enums
        agent_specialization_mapping = {
            "intake": AgentSpecialization.INTAKE,
            "transcription": AgentSpecialization.TRANSCRIPTION,
            "clinical_analysis": AgentSpecialization.CLINICAL_ANALYSIS,
            "billing": AgentSpecialization.BILLING,
            "compliance": AgentSpecialization.COMPLIANCE,
            "document_processor": AgentSpecialization.DOCUMENT_PROCESSOR
        }
        
        # Build workflow definitions from configuration
        for workflow_name, workflow_steps in config.workflows.step_definitions.items():
            if workflow_name in workflow_type_mapping:
                workflow_type = workflow_type_mapping[workflow_name]
                step_list = []
                
                for step_config in workflow_steps:
                    if step_config.agent_specialization in agent_specialization_mapping:
                        agent_spec = agent_specialization_mapping[step_config.agent_specialization]
                        
                        step = WorkflowStep(
                            step_name=step_config.step_name,
                            agent_specialization=agent_spec,
                            step_config=step_config.step_config,
                            dependencies=step_config.dependencies,
                            parallel_capable=step_config.parallel_capable,
                            timeout_seconds=step_config.timeout_seconds
                        )
                        step_list.append(step)
                
                definitions[workflow_type] = step_list
        
        return definitions'''
        
        content = re.sub(initialize_method_pattern, new_method, content, flags=re.DOTALL)
        
        # Replace hardcoded result compilation with configuration-based approach
        compile_result_pattern = r'def _compile_workflow_result\(self, workflow_execution: WorkflowExecution\)[^}]+return \{[^}]+\}'
        
        new_compile_method = '''def _compile_workflow_result(self, workflow_execution: WorkflowExecution) -> Dict[str, Any]:
        """Compile final workflow result using configuration templates"""
        config = get_healthcare_config()
        step_results = workflow_execution.step_results
        workflow_type_name = workflow_execution.workflow_type.value
        
        # Get result template from configuration
        result_template = config.workflows.result_templates.get(workflow_type_name, {})
        
        if result_template:
            compiled_result = {}
            for result_key, source_path in result_template.items():
                # Handle nested result paths like "compliance_check.success"
                if '.' in source_path:
                    source_step, source_field = source_path.split('.', 1)
                    if source_step in step_results:
                        compiled_result[result_key] = step_results[source_step].get(source_field)
                else:
                    compiled_result[result_key] = step_results.get(source_path, {})
            
            return compiled_result
        
        # Fallback to default result structure
        return {
            'workflow_type': workflow_execution.workflow_type.value,
            'all_step_results': step_results,
            'success': workflow_execution.status == "completed"
        }'''
        
        content = re.sub(compile_result_pattern, new_compile_method, content, flags=re.DOTALL)
        
        return content
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        
        try:
            # Try to import and initialize components with configuration
            from config.config_loader import get_healthcare_config
            config = get_healthcare_config()
            
            # Validate configuration structure
            assert hasattr(config, 'intake_agent')
            assert hasattr(config, 'workflows')
            assert hasattr(config, 'orchestration')
            
            # Validate intake configuration
            assert len(config.intake_agent.disclaimers) > 0
            assert len(config.intake_agent.voice_processing.field_mappings) > 0
            assert len(config.intake_agent.document_requirements.base_documents) > 0
            
            # Validate workflow configuration
            assert len(config.workflows.types) > 0
            assert len(config.workflows.agent_specializations) > 0
            assert len(config.workflows.step_definitions) > 0
            
            logger.info("✅ Configuration migration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration migration validation failed: {str(e)}")
            return False


def main():
    """Run configuration migration"""
    
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate healthcare agents to use external configuration")
    parser.add_argument("--healthcare-api-dir", 
                       default="/home/intelluxe/services/user/healthcare-api",
                       help="Path to healthcare API directory")
    parser.add_argument("--validate-only", 
                       action="store_true",
                       help="Only validate existing configuration without migration")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🏥 Healthcare Agent Configuration Migration")
    print("="*50)
    
    try:
        migrator = AgentConfigMigrator(args.healthcare_api_dir)
        
        if args.validate_only:
            print("Validating existing configuration...")
            if migrator.validate_migration():
                print("✅ Configuration validation successful")
                sys.exit(0)
            else:
                print("❌ Configuration validation failed")
                sys.exit(1)
        
        else:
            print("Starting configuration migration...")
            print(f"Healthcare API directory: {args.healthcare_api_dir}")
            
            # Perform migration
            success = migrator.migrate_all_agents()
            
            if success:
                print("\n✅ Migration completed successfully!")
                
                # Validate migration
                print("Validating migration...")
                if migrator.validate_migration():
                    print("✅ Migration validation successful")
                    print("\n📋 Next Steps:")
                    print("1. Review migrated agent files")
                    print("2. Test agent functionality with new configuration")
                    print("3. Update any additional hardcoded configuration")
                    print("4. Remove backup files (.py.backup) when satisfied")
                    sys.exit(0)
                else:
                    print("❌ Migration validation failed")
                    print("Please review backup files and restore if needed")
                    sys.exit(1)
            
            else:
                print("❌ Migration failed")
                print("Check backup files (.py.backup) to restore original versions")
                sys.exit(1)
    
    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()