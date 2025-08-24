"""
Workflow Orchestrator - Multi-Agent Healthcare Workflows
Implements the INTAKE_TO_BILLING and other multi-agent workflows from PHASE_3
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from core.enhanced_sessions import EnhancedSessionManager
from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import sanitize_healthcare_data


class WorkflowType(Enum):
    """Multi-agent workflow types from PHASE_3 design"""
    INTAKE_TO_BILLING = "intake_to_billing"
    CLINICAL_DECISION = "clinical_decision"
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"
    VOICE_INTAKE_WORKFLOW = "voice_intake_workflow"


class AgentSpecialization(Enum):
    """Agent specializations for workflow orchestration"""
    INTAKE = "intake"
    TRANSCRIPTION = "transcription"
    CLINICAL_ANALYSIS = "clinical_analysis"
    BILLING = "billing"
    COMPLIANCE = "compliance"
    DOCUMENT_PROCESSOR = "document_processor"


@dataclass
class WorkflowStep:
    """Individual step in a multi-agent workflow"""
    step_name: str
    agent_specialization: AgentSpecialization
    step_config: dict[str, Any]
    dependencies: list[str]
    parallel_capable: bool
    timeout_seconds: int = 300


@dataclass
class WorkflowExecution:
    """Runtime execution state of a workflow"""
    workflow_id: str
    workflow_type: WorkflowType
    session_id: str
    user_id: str
    doctor_id: str | None
    input_data: dict[str, Any]
    step_results: dict[str, Any]
    current_step: str | None
    status: str  # "pending", "running", "completed", "failed"
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None


class WorkflowOrchestrator:
    """
    Multi-agent workflow orchestrator implementing PHASE_3 patterns

    Coordinates complex healthcare workflows that span multiple agents,
    managing data flow, session continuity, and compliance requirements.
    """

    def __init__(self):
        self.logger = get_healthcare_logger("workflow_orchestrator")
        self.session_manager = EnhancedSessionManager()

        # Initialize workflow definitions from PHASE_3
        self.workflow_definitions = self._initialize_workflow_definitions()

        # Agent registry for workflow execution
        self.agent_registry = {}

        # Active workflow executions
        self.active_workflows: dict[str, WorkflowExecution] = {}

        log_healthcare_event(
            self.logger,
            logging.INFO,
            "Workflow Orchestrator initialized with PHASE_3 patterns",
            context={
                "workflow_types": [wt.value for wt in WorkflowType],
                "agent_specializations": [ag.value for ag in AgentSpecialization],
            },
            operation_type="orchestrator_initialization",
        )

    def _initialize_workflow_definitions(self) -> dict[WorkflowType, list[WorkflowStep]]:
        """Initialize workflow definitions based on PHASE_3 patterns"""
        return {
            WorkflowType.INTAKE_TO_BILLING: [
                WorkflowStep("patient_intake", AgentSpecialization.INTAKE, {}, [], False),
                WorkflowStep("medical_transcription", AgentSpecialization.TRANSCRIPTION, {}, ["patient_intake"], False),
                WorkflowStep("clinical_analysis", AgentSpecialization.CLINICAL_ANALYSIS, {}, ["medical_transcription"], False),
                WorkflowStep("compliance_check", AgentSpecialization.COMPLIANCE, {}, ["clinical_analysis"], True),
                WorkflowStep("billing_process", AgentSpecialization.BILLING, {}, ["clinical_analysis"], True),
            ],

            WorkflowType.VOICE_INTAKE_WORKFLOW: [
                WorkflowStep("voice_intake_session", AgentSpecialization.INTAKE,
                           {"voice_enabled": True, "real_time": True}, [], False),
                WorkflowStep("transcription_analysis", AgentSpecialization.TRANSCRIPTION,
                           {"medical_nlp": True, "terminology_extraction": True}, [], True),
                WorkflowStep("form_completion", AgentSpecialization.INTAKE,
                           {"voice_to_form": True}, ["voice_intake_session", "transcription_analysis"], False),
                WorkflowStep("clinical_validation", AgentSpecialization.CLINICAL_ANALYSIS,
                           {"voice_intake_validation": True}, ["form_completion"], False),
            ],

            WorkflowType.CLINICAL_DECISION: [
                WorkflowStep("medical_transcription", AgentSpecialization.TRANSCRIPTION, {}, [], False),
                WorkflowStep("clinical_analysis", AgentSpecialization.CLINICAL_ANALYSIS, {}, ["medical_transcription"], False),
                WorkflowStep("compliance_validation", AgentSpecialization.COMPLIANCE, {}, ["clinical_analysis"], False),
            ],

            WorkflowType.COMPREHENSIVE_ANALYSIS: [
                WorkflowStep("intake_processing", AgentSpecialization.INTAKE, {}, [], True),
                WorkflowStep("transcription_processing", AgentSpecialization.TRANSCRIPTION, {}, [], True),
                WorkflowStep("clinical_analysis", AgentSpecialization.CLINICAL_ANALYSIS,
                           {}, ["intake_processing", "transcription_processing"], False),
                WorkflowStep("document_generation", AgentSpecialization.DOCUMENT_PROCESSOR,
                           {}, ["clinical_analysis"], False),
                WorkflowStep("billing_optimization", AgentSpecialization.BILLING, {}, ["clinical_analysis"], True),
            ],
        }

    async def register_agent(self, specialization: AgentSpecialization, agent_instance):
        """Register an agent for workflow execution"""
        self.agent_registry[specialization] = agent_instance

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Agent registered: {specialization.value}",
            context={"agent_specialization": specialization.value},
            operation_type="agent_registration",
        )

    async def start_workflow(
        self,
        workflow_type: WorkflowType,
        session_id: str,
        user_id: str,
        input_data: dict[str, Any],
        doctor_id: str | None = None,
    ) -> str:
        """Start a multi-agent workflow execution"""

        # Generate workflow ID
        workflow_id = f"wf_{workflow_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Create workflow execution context
        workflow_execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            session_id=session_id,
            user_id=user_id,
            doctor_id=doctor_id,
            input_data=input_data,
            step_results={},
            current_step=None,
            status="pending",
            error_message=None,
            started_at=datetime.now(),
            completed_at=None,
        )

        # Store active workflow
        self.active_workflows[workflow_id] = workflow_execution

        # Start workflow execution
        asyncio.create_task(self._execute_workflow(workflow_id))

        log_healthcare_event(
            self.logger,
            logging.INFO,
            f"Workflow started: {workflow_type.value}",
            context={
                "workflow_id": workflow_id,
                "session_id": session_id,
                "user_id": user_id,
                "doctor_id": doctor_id,
                "workflow_type": workflow_type.value,
            },
            operation_type="workflow_started",
        )

        return workflow_id

    async def _execute_workflow(self, workflow_id: str):
        """Execute a workflow with proper error handling and session management"""

        workflow_execution = self.active_workflows.get(workflow_id)
        if not workflow_execution:
            self.logger.error(f"Workflow execution not found: {workflow_id}")
            return

        try:
            workflow_execution.status = "running"

            # Get workflow definition
            workflow_steps = self.workflow_definitions[workflow_execution.workflow_type]

            # Execute steps in order, respecting dependencies
            for step in workflow_steps:
                # Check if dependencies are satisfied
                if not self._dependencies_satisfied(step, workflow_execution.step_results):
                    continue

                workflow_execution.current_step = step.step_name

                # Execute step with agent
                step_result = await self._execute_workflow_step(step, workflow_execution)

                # Store result
                workflow_execution.step_results[step.step_name] = step_result

                # Update session with step result
                await self._update_session_with_step_result(
                    workflow_execution.session_id, step, step_result,
                )

                log_healthcare_event(
                    self.logger,
                    logging.INFO,
                    f"Workflow step completed: {step.step_name}",
                    context={
                        "workflow_id": workflow_id,
                        "step_name": step.step_name,
                        "agent_specialization": step.agent_specialization.value,
                    },
                    operation_type="workflow_step_completed",
                )

            # Mark workflow as completed
            workflow_execution.status = "completed"
            workflow_execution.completed_at = datetime.now()
            workflow_execution.current_step = None

            # Generate final workflow result
            final_result = self._compile_workflow_result(workflow_execution)

            # Update session with final result
            await self.session_manager.update_conversation_context(
                workflow_execution.session_id,
                {
                    "workflow_result": final_result,
                    "workflow_id": workflow_id,
                    "completed_at": workflow_execution.completed_at.isoformat(),
                },
            )

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Workflow completed successfully: {workflow_execution.workflow_type.value}",
                context={
                    "workflow_id": workflow_id,
                    "execution_time": (workflow_execution.completed_at - workflow_execution.started_at).total_seconds(),
                    "steps_completed": len(workflow_execution.step_results),
                },
                operation_type="workflow_completed",
            )

        except Exception as e:
            # Handle workflow failure
            workflow_execution.status = "failed"
            workflow_execution.error_message = str(e)
            workflow_execution.completed_at = datetime.now()

            log_healthcare_event(
                self.logger,
                logging.ERROR,
                f"Workflow execution failed: {str(e)}",
                context={
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_execution.workflow_type.value,
                    "current_step": workflow_execution.current_step,
                    "error": str(e),
                },
                operation_type="workflow_failed",
            )

        finally:
            # Clean up completed workflow
            if workflow_id in self.active_workflows:
                # Keep for a short time for status queries, then remove
                asyncio.create_task(self._cleanup_workflow(workflow_id, delay_seconds=300))

    async def _execute_workflow_step(
        self,
        step: WorkflowStep,
        workflow_execution: WorkflowExecution,
    ) -> dict[str, Any]:
        """Execute a single workflow step with the appropriate agent"""

        # Get the agent for this step
        agent = self.agent_registry.get(step.agent_specialization)
        if not agent:
            msg = f"Agent not registered for specialization: {step.agent_specialization.value}"
            raise RuntimeError(msg)

        # Prepare step input data
        step_input = {
            "workflow_id": workflow_execution.workflow_id,
            "session_id": workflow_execution.session_id,
            "user_id": workflow_execution.user_id,
            "doctor_id": workflow_execution.doctor_id,
            "step_config": step.step_config,
            "workflow_input": workflow_execution.input_data,
            "previous_results": workflow_execution.step_results,
        }

        # Add step-specific data based on agent type
        if step.agent_specialization == AgentSpecialization.INTAKE:
            step_input.update({
                "intake_type": workflow_execution.input_data.get("intake_type", "new_patient_registration"),
                "patient_data": workflow_execution.input_data.get("patient_data", {}),
                "voice_enabled": step.step_config.get("voice_enabled", False),
            })

        elif step.agent_specialization == AgentSpecialization.TRANSCRIPTION:
            step_input.update({
                "audio_data": workflow_execution.input_data.get("audio_data"),
                "real_time": step.step_config.get("real_time", False),
                "medical_nlp": step.step_config.get("medical_nlp", True),
            })

        # Execute with timeout
        try:
            return await asyncio.wait_for(
                agent.process_request(step_input),
                timeout=step.timeout_seconds,
            )

        except TimeoutError:
            msg = f"Step {step.step_name} timed out after {step.timeout_seconds} seconds"
            raise RuntimeError(msg)

    def _dependencies_satisfied(self, step: WorkflowStep, step_results: dict[str, Any]) -> bool:
        """Check if all dependencies for a step are satisfied"""
        return all(dep in step_results for dep in step.dependencies)

    async def _update_session_with_step_result(
        self,
        session_id: str,
        step: WorkflowStep,
        step_result: dict[str, Any],
    ):
        """Update enhanced session with step result"""

        # Sanitize result for PHI protection
        sanitized_result = sanitize_healthcare_data(step_result)

        context_update = {
            f"workflow_step_{step.step_name}": {
                "result": sanitized_result,
                "agent": step.agent_specialization.value,
                "timestamp": datetime.now().isoformat(),
                "success": step_result.get("success", True),
            },
        }

        await self.session_manager.update_conversation_context(session_id, context_update)

    def _compile_workflow_result(self, workflow_execution: WorkflowExecution) -> dict[str, Any]:
        """Compile final workflow result based on workflow type"""

        step_results = workflow_execution.step_results

        if workflow_execution.workflow_type == WorkflowType.INTAKE_TO_BILLING:
            return {
                "patient_intake": step_results.get("patient_intake", {}),
                "clinical_notes": step_results.get("medical_transcription", {}),
                "clinical_analysis": step_results.get("clinical_analysis", {}),
                "billing_codes": step_results.get("billing_process", {}),
                "compliance_verified": step_results.get("compliance_check", {}).get("success", False),
            }

        if workflow_execution.workflow_type == WorkflowType.VOICE_INTAKE_WORKFLOW:
            return {
                "voice_session": step_results.get("voice_intake_session", {}),
                "transcription_analysis": step_results.get("transcription_analysis", {}),
                "completed_form": step_results.get("form_completion", {}),
                "clinical_validation": step_results.get("clinical_validation", {}),
                "form_completion_percentage": step_results.get("form_completion", {}).get("completion_percentage", 0),
            }

        if workflow_execution.workflow_type == WorkflowType.CLINICAL_DECISION:
            return {
                "transcription_analysis": step_results.get("medical_transcription", {}),
                "clinical_recommendations": step_results.get("clinical_analysis", {}),
                "compliance_validation": step_results.get("compliance_validation", {}),
            }

        if workflow_execution.workflow_type == WorkflowType.COMPREHENSIVE_ANALYSIS:
            return {
                "intake_data": step_results.get("intake_processing", {}),
                "transcription_data": step_results.get("transcription_processing", {}),
                "clinical_analysis": step_results.get("clinical_analysis", {}),
                "generated_documents": step_results.get("document_generation", {}),
                "billing_optimization": step_results.get("billing_optimization", {}),
            }

        # Default result structure
        return {
            "workflow_type": workflow_execution.workflow_type.value,
            "all_step_results": step_results,
            "success": workflow_execution.status == "completed",
        }

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """Get current status of a workflow execution"""

        workflow_execution = self.active_workflows.get(workflow_id)
        if not workflow_execution:
            return None

        return {
            "workflow_id": workflow_id,
            "workflow_type": workflow_execution.workflow_type.value,
            "status": workflow_execution.status,
            "current_step": workflow_execution.current_step,
            "completed_steps": list(workflow_execution.step_results.keys()),
            "error_message": workflow_execution.error_message,
            "started_at": workflow_execution.started_at.isoformat(),
            "completed_at": workflow_execution.completed_at.isoformat() if workflow_execution.completed_at else None,
        }

    async def _cleanup_workflow(self, workflow_id: str, delay_seconds: int = 300):
        """Clean up workflow execution after delay"""
        await asyncio.sleep(delay_seconds)
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]

            log_healthcare_event(
                self.logger,
                logging.INFO,
                f"Workflow cleaned up: {workflow_id}",
                context={"workflow_id": workflow_id},
                operation_type="workflow_cleanup",
            )


# Singleton instance for application use
workflow_orchestrator = WorkflowOrchestrator()
