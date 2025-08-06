---
title: Real-Time Clinical Assistance
description: WebSocket patterns and streaming protocols for real-time clinical AI assistance
tags: [healthcare, real-time, websockets, clinical-assistance, streaming]
---

# Real-Time Clinical Assistance Instructions

## Purpose

Comprehensive patterns for implementing real-time healthcare AI assistance using WebSocket connections, progressive analysis streaming, and clinical workflow integration while maintaining PHI protection and medical safety.

## Core Real-Time Clinical Patterns

### WebSocket Healthcare Infrastructure

```python
# ✅ ADVANCED: Real-time clinical assistance with comprehensive safety protocols
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List

class RealTimeClinicalAssistant:
    """Real-time clinical AI assistance during patient encounters."""
    
    def __init__(self):
        self.active_sessions = {}
        self.clinical_emergency_patterns = self._load_emergency_patterns()
        self.phi_detector = PHIDetector()
        self.clinical_validator = ClinicalSafetyValidator()
    
    async def setup_clinical_websocket_handler(self):
        """WebSocket patterns optimized for clinical workflows with comprehensive safety."""
        
        @websocket_route("/clinical-assistance")
        async def handle_clinical_stream(websocket: WebSocket):
            await websocket.accept()
            
            # Establish clinical session with strict compliance logging
            session = await self.create_clinical_session(
                websocket=websocket,
                compliance_mode="strict",
                audit_level="comprehensive",
                phi_protection=True
            )
            
            self.active_sessions[session.id] = session
            
            try:
                # Send initial clinical safety message
                await websocket.send_json({
                    "type": "session_initialized",
                    "message": "Clinical AI assistance session started.",
                    "medical_disclaimer": "This AI provides educational information only. Always consult qualified healthcare professionals for medical decisions.",
                    "session_id": session.id,
                    "compliance_level": "strict"
                })
                
                async for message in websocket.iter_text():
                    # Immediate PHI scanning with real-time protection
                    phi_scan_result = await self.phi_detector.scan_real_time(message)
                    
                    if phi_scan_result.contains_phi:
                        await websocket.send_json({
                            "type": "phi_warning",
                            "message": "Protected health information detected. Implementing secure processing protocols.",
                            "phi_types": phi_scan_result.detected_types,
                            "compliance_status": "phi_protected",
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Sanitize message while preserving clinical context
                        message = await self.sanitize_phi_preserve_context(message)
                    
                    # Progressive clinical analysis with streaming updates
                    async for clinical_update in self.progressive_clinical_analysis(message, session):
                        await websocket.send_json(clinical_update)
                    
                    # Log all clinical interactions for compliance
                    await session.log_clinical_interaction(message, phi_detected=phi_scan_result.contains_phi)
                
            except WebSocketDisconnect:
                await self.cleanup_clinical_session(session, reason="client_disconnect")
            except Exception as e:
                await self.handle_clinical_session_error(session, e)
                await websocket.close(code=1011, reason="Clinical session error")
            finally:
                # Ensure session cleanup and audit logging
                if session.id in self.active_sessions:
                    del self.active_sessions[session.id]
                await session.finalize_audit_log()
    
    async def progressive_clinical_analysis(self, clinical_input: str, session: ClinicalSession) -> AsyncGenerator[Dict[str, Any], None]:
        """Provide progressive clinical analysis with streaming updates and safety validation."""
        
        # Step 1: Immediate emergency detection and safety check
        emergency_result = await self.detect_emergency_patterns(clinical_input)
        if emergency_result.is_emergency:
            yield {
                "type": "emergency_alert",
                "priority": "critical",
                "content": "EMERGENCY SCENARIO DETECTED: This appears to require immediate medical attention. Contact emergency services (911) immediately.",
                "emergency_type": emergency_result.emergency_type,
                "action_required": "immediate_medical_attention",
                "clinical_urgency": "life_threatening",
                "timestamp": datetime.now().isoformat(),
                "medical_disclaimer": "This is an automated emergency detection. Seek immediate professional medical care."
            }
            # Stop processing for emergency scenarios
            return
        
        # Step 2: Clinical entity extraction with medical context preservation
        yield {
            "type": "processing_update",
            "content": "Analyzing clinical information...",
            "stage": "entity_extraction_started",
            "timestamp": datetime.now().isoformat()
        }
        
        entities = await self.extract_medical_entities(clinical_input)
        yield {
            "type": "clinical_update",
            "priority": "normal",
            "content": f"Identified medical concepts: {self.format_entities_for_display(entities)}",
            "stage": "entity_extraction",
            "entities": entities,
            "confidence": entities.get('extraction_confidence', 0.0),
            "timestamp": datetime.now().isoformat()
        }
        
        # Step 3: Clinical literature search with evidence grading
        if entities.get('conditions') or entities.get('symptoms'):
            yield {
                "type": "processing_update", 
                "content": "Searching clinical literature...",
                "stage": "literature_search_started",
                "timestamp": datetime.now().isoformat()
            }
            
            literature_findings = await self.search_clinical_literature(entities)
            yield {
                "type": "clinical_update",
                "priority": "normal",
                "content": f"Found {len(literature_findings)} relevant clinical references",
                "stage": "literature_search",
                "findings_count": len(literature_findings),
                "evidence_quality": self.grade_evidence_quality(literature_findings),
                "top_findings": self.summarize_top_findings(literature_findings[:3]),
                "timestamp": datetime.now().isoformat()
            }
        else:
            literature_findings = []
        
        # Step 4: Clinical reasoning and differential analysis
        if entities.get('symptoms') and len(entities['symptoms']) > 1:
            yield {
                "type": "processing_update",
                "content": "Performing clinical analysis...",
                "stage": "clinical_reasoning_started", 
                "timestamp": datetime.now().isoformat()
            }
            
            clinical_reasoning = await self.perform_clinical_reasoning(entities, literature_findings)
            yield {
                "type": "clinical_update",
                "priority": "normal",
                "content": "Clinical analysis completed",
                "stage": "clinical_reasoning",
                "reasoning_steps": clinical_reasoning.reasoning_chain,
                "differential_considerations": clinical_reasoning.differential_list,
                "uncertainty_level": clinical_reasoning.uncertainty_score,
                "timestamp": datetime.now().isoformat()
            }
        else:
            clinical_reasoning = None
        
        # Step 5: Final clinical synthesis with comprehensive disclaimers
        clinical_synthesis = await self.synthesize_clinical_information(
            entities=entities,
            literature_findings=literature_findings,
            clinical_reasoning=clinical_reasoning,
            session_context=session.context
        )
        
        yield {
            "type": "clinical_synthesis",
            "priority": "normal",
            "content": clinical_synthesis.summary,
            "stage": "clinical_synthesis_complete",
            "synthesis": {
                "key_findings": clinical_synthesis.key_findings,
                "clinical_considerations": clinical_synthesis.considerations,
                "evidence_summary": clinical_synthesis.evidence_summary,
                "uncertainty_quantification": clinical_synthesis.uncertainty_metrics
            },
            "medical_disclaimer": "This analysis supports clinical decision-making but does not replace professional medical judgment. Always consult qualified healthcare professionals for medical decisions.",
            "evidence_disclaimer": "Clinical evidence presented is for educational purposes and should be verified through official medical sources.",
            "timestamp": datetime.now().isoformat()
        }
        
        # Step 6: Store analysis in session memory for context continuity
        await session.store_clinical_analysis(clinical_synthesis)
```

### Progressive Clinical Analysis Architecture

```python
# ✅ ADVANCED: Progressive clinical analysis with medical safety validation
class ProgressiveClinicalAnalyzer:
    """Progressive analysis engine for real-time clinical assistance."""
    
    def __init__(self):
        self.analysis_pipelines = {
            "emergency_detection": EmergencyDetectionPipeline(),
            "entity_extraction": MedicalEntityExtractionPipeline(),
            "literature_search": ClinicalLiteratureSearchPipeline(),
            "clinical_reasoning": ClinicalReasoningPipeline(),
            "synthesis": ClinicalSynthesisPipeline()
        }
        
        self.safety_validators = {
            "medical_safety": MedicalSafetyValidator(),
            "phi_protection": PHIProtectionValidator(),
            "compliance": HealthcareComplianceValidator()
        }
    
    async def analyze_clinical_input_progressive(
        self,
        clinical_input: str,
        session: ClinicalSession
    ) -> AsyncGenerator[ClinicalAnalysisStep, None]:
        """Progressive clinical analysis with comprehensive safety validation."""
        
        analysis_context = ClinicalAnalysisContext(
            input=clinical_input,
            session=session,
            safety_level="maximum"
        )
        
        # Pipeline execution with safety validation at each step
        for pipeline_name, pipeline in self.analysis_pipelines.items():
            try:
                # Pre-execution safety validation
                safety_check = await self.validate_pipeline_safety(pipeline_name, analysis_context)
                
                if not safety_check.is_safe:
                    yield ClinicalAnalysisStep(
                        type="safety_warning",
                        content=f"Safety validation failed for {pipeline_name}: {safety_check.reason}",
                        pipeline=pipeline_name,
                        safety_status="blocked"
                    )
                    continue
                
                # Execute pipeline with streaming results
                async for step_result in pipeline.execute_streaming(analysis_context):
                    # Validate each step result for clinical safety
                    validated_result = await self.validate_step_result(step_result)
                    
                    # Add medical disclaimers to clinical content
                    if validated_result.contains_clinical_content:
                        validated_result = self.add_step_medical_disclaimers(validated_result)
                    
                    yield validated_result
                    
                    # Update analysis context for subsequent pipelines
                    analysis_context.incorporate_step_result(validated_result)
                
            except Exception as e:
                # Handle pipeline errors with clinical context
                error_step = ClinicalAnalysisStep(
                    type="pipeline_error",
                    content=f"Analysis pipeline {pipeline_name} encountered an error",
                    error_details=str(e),
                    medical_disclaimer="Analysis could not be completed safely. Consult healthcare professionals."
                )
                yield error_step
    
    async def detect_emergency_patterns(self, clinical_input: str) -> EmergencyDetectionResult:
        """Comprehensive emergency pattern detection for clinical scenarios."""
        
        emergency_indicators = {
            # Cardiovascular emergencies
            "cardiac": {
                "patterns": [
                    "chest pain", "heart attack", "cardiac arrest", "myocardial infarction",
                    "severe chest pressure", "crushing chest pain", "heart stopped beating"
                ],
                "severity": "critical",
                "response_time": "immediate"
            },
            
            # Respiratory emergencies
            "respiratory": {
                "patterns": [
                    "can't breathe", "difficulty breathing", "shortness of breath", 
                    "respiratory distress", "choking", "airway obstruction"
                ],
                "severity": "critical", 
                "response_time": "immediate"
            },
            
            # Neurological emergencies
            "neurological": {
                "patterns": [
                    "stroke", "seizure", "unconscious", "loss of consciousness",
                    "paralysis", "severe headache", "confusion", "disorientation"
                ],
                "severity": "critical",
                "response_time": "immediate"
            },
            
            # Trauma emergencies
            "trauma": {
                "patterns": [
                    "severe bleeding", "hemorrhage", "traumatic injury", "head trauma",
                    "broken bones", "severe burns", "deep cuts"
                ],
                "severity": "urgent_to_critical",
                "response_time": "immediate_to_urgent"
            },
            
            # Allergic reactions
            "allergic": {
                "patterns": [
                    "severe allergic reaction", "anaphylaxis", "throat swelling",
                    "facial swelling", "hives all over", "difficulty swallowing"
                ],
                "severity": "critical",
                "response_time": "immediate"
            },
            
            # Poisoning/overdose
            "toxicological": {
                "patterns": [
                    "poisoning", "overdose", "toxic ingestion", "medication overdose",
                    "chemical exposure", "drug overdose"
                ],
                "severity": "critical",
                "response_time": "immediate"
            }
        }
        
        clinical_input_lower = clinical_input.lower()
        detected_emergencies = []
        
        for emergency_type, config in emergency_indicators.items():
            for pattern in config["patterns"]:
                if pattern in clinical_input_lower:
                    detected_emergencies.append({
                        "type": emergency_type,
                        "pattern": pattern,
                        "severity": config["severity"],
                        "response_time": config["response_time"]
                    })
        
        is_emergency = len(detected_emergencies) > 0
        
        return EmergencyDetectionResult(
            is_emergency=is_emergency,
            emergency_type=detected_emergencies[0]["type"] if is_emergency else None,
            detected_patterns=detected_emergencies,
            severity_level="critical" if is_emergency else "normal",
            recommended_action="immediate_911_call" if is_emergency else "continue_analysis"
        )
```

### Clinical WebSocket Session Management

```python
# ✅ ADVANCED: Clinical WebSocket session management with comprehensive audit logging
class ClinicalWebSocketSessionManager:
    """Manage WebSocket sessions for clinical AI assistance with compliance logging."""
    
    def __init__(self):
        self.active_sessions = {}
        self.session_audit_logger = ClinicalAuditLogger()
        self.phi_protection_manager = PHIProtectionManager()
    
    async def create_clinical_session(
        self,
        websocket: WebSocket,
        compliance_mode: str = "strict",
        audit_level: str = "comprehensive",
        phi_protection: bool = True
    ) -> ClinicalSession:
        """Create new clinical WebSocket session with comprehensive compliance setup."""
        
        session_id = self.generate_secure_session_id()
        
        session = ClinicalSession(
            id=session_id,
            websocket=websocket,
            compliance_mode=compliance_mode,
            audit_level=audit_level,
            phi_protection_enabled=phi_protection,
            created_at=datetime.now(),
            medical_disclaimers_acknowledged=False
        )
        
        # Initialize session audit logging
        await self.session_audit_logger.initialize_session_log(session)
        
        # Set up PHI protection for session
        if phi_protection:
            session.phi_protector = await self.phi_protection_manager.create_session_protector(session_id)
        
        # Initialize clinical context manager
        session.clinical_context = ClinicalContextManager(session_id)
        
        # Log session creation for compliance
        await self.session_audit_logger.log_session_event(
            session_id=session_id,
            event_type="session_created",
            details={
                "compliance_mode": compliance_mode,
                "audit_level": audit_level,
                "phi_protection": phi_protection,
                "client_info": self.extract_safe_client_info(websocket)
            }
        )
        
        return session
    
    async def handle_clinical_message(self, session: ClinicalSession, message: str) -> Dict[str, Any]:
        """Handle clinical messages with comprehensive safety and compliance processing."""
        
        message_id = self.generate_message_id()
        processing_start = datetime.now()
        
        try:
            # Pre-processing safety validation
            safety_validation = await self.validate_message_safety(message, session)
            
            if not safety_validation.is_safe:
                return {
                    "type": "safety_error",
                    "message": "Message could not be processed safely",
                    "safety_concerns": safety_validation.concerns,
                    "medical_disclaimer": "For patient safety, this message could not be processed."
                }
            
            # PHI detection and protection
            phi_scan = await session.phi_protector.scan_message(message)
            
            if phi_scan.contains_phi:
                # Log PHI detection for compliance
                await self.session_audit_logger.log_phi_detection(
                    session_id=session.id,
                    message_id=message_id,
                    phi_types=phi_scan.detected_types,
                    protection_applied=True
                )
                
                # Apply PHI protection while preserving clinical context
                message = await session.phi_protector.protect_message(message)
            
            # Process clinical message
            processing_result = await self.process_clinical_message(message, session)
            
            # Add comprehensive medical disclaimers
            processing_result = self.add_comprehensive_disclaimers(processing_result)
            
            # Log successful message processing
            await self.session_audit_logger.log_message_processed(
                session_id=session.id,
                message_id=message_id,
                processing_time=(datetime.now() - processing_start).total_seconds(),
                phi_detected=phi_scan.contains_phi
            )
            
            return processing_result
            
        except Exception as e:
            # Log processing error for compliance
            await self.session_audit_logger.log_processing_error(
                session_id=session.id,
                message_id=message_id,
                error=str(e),
                processing_time=(datetime.now() - processing_start).total_seconds()
            )
            
            return {
                "type": "processing_error",
                "message": "Clinical message could not be processed",
                "medical_disclaimer": "Processing error occurred. Consult healthcare professionals for clinical assistance."
            }
    
    async def cleanup_clinical_session(self, session: ClinicalSession, reason: str):
        """Clean up clinical session with comprehensive audit logging."""
        
        try:
            # Finalize clinical context and analysis
            await session.clinical_context.finalize_session()
            
            # Generate session summary for audit
            session_summary = await self.generate_session_summary(session)
            
            # Log session termination
            await self.session_audit_logger.log_session_termination(
                session_id=session.id,
                reason=reason,
                session_duration=(datetime.now() - session.created_at).total_seconds(),
                session_summary=session_summary
            )
            
            # Clean up PHI protection resources
            if session.phi_protection_enabled:
                await session.phi_protector.cleanup_session_resources()
            
            # Remove from active sessions
            if session.id in self.active_sessions:
                del self.active_sessions[session.id]
                
        except Exception as e:
            logger.error(f"Error during clinical session cleanup: {e}")
            # Ensure session is removed even if cleanup fails
            if session.id in self.active_sessions:
                del self.active_sessions[session.id]
```

## Real-Time Clinical Workflow Integration

### Clinical Dashboard Integration

```python
# ✅ ADVANCED: Real-time clinical dashboard integration patterns
class ClinicalDashboardIntegrator:
    """Integrate real-time clinical assistance with clinical dashboards and EHR systems."""
    
    async def integrate_with_clinical_dashboard(self, session: ClinicalSession):
        """Integrate real-time clinical assistance with clinical dashboard workflows."""
        
        # Establish secure connection to clinical dashboard
        dashboard_connection = await self.establish_dashboard_connection(session)
        
        # Set up clinical event streaming
        clinical_event_stream = ClinicalEventStream(session.id)
        
        # Stream clinical analysis results to dashboard
        async for analysis_result in session.get_analysis_stream():
            # Format for clinical dashboard display
            dashboard_update = await self.format_for_dashboard(analysis_result)
            
            # Send to clinical dashboard with PHI protection
            await dashboard_connection.send_clinical_update(dashboard_update)
            
            # Log dashboard integration for compliance
            await self.log_dashboard_integration(session.id, dashboard_update)
```

## Integration Guidelines

### Real-Time Clinical Best Practices

**WebSocket Clinical Safety**:
- Always implement immediate emergency detection and response
- Use comprehensive PHI protection for all real-time communications
- Provide progressive clinical analysis with streaming updates
- Include medical disclaimers with every clinical response

**Performance Requirements**:
- Emergency detection must complete within 500ms
- Progressive analysis steps should stream within 2-3 seconds
- Support concurrent clinical sessions (100+ simultaneous users)
- Implement clinical workflow-appropriate timeouts

**Compliance and Audit**:
- Log all clinical interactions with comprehensive audit trails
- Implement session-based PHI protection and monitoring
- Track clinical analysis steps for regulatory compliance
- Generate clinical session summaries for review

**Clinical Integration**:
- Support clinical dashboard and EHR integration
- Enable clinical context continuity across sessions
- Implement clinical workflow interruption handling
- Provide clinical decision support integration

Remember: Real-time clinical assistance must prioritize patient safety, provide immediate emergency detection, maintain comprehensive PHI protection, and include appropriate medical disclaimers throughout all real-time interactions.
