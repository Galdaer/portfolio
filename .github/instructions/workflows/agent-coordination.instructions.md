---
title: Healthcare AI Agent Coordination
description: Patterns for coordinating multiple healthcare AI agents in complex clinical workflows
tags: [healthcare, multi-agent, clinical-workflows, coordination]
---

# Healthcare AI Agent Coordination Instructions

## Purpose

Comprehensive patterns for coordinating Clinical Research Agent, Search Assistant, and specialized medical agents in complex healthcare AI workflows while maintaining medical safety, PHI protection, and clinical effectiveness.

## ✅ AGENT ROUTING SUCCESS (2025-08-11)

**BREAKTHROUGH ACHIEVEMENT**: Open WebUI successfully routing to healthcare agents via `/process` endpoint.

**Current Status**: Agent router working, agents receiving method calls, but need to implement missing methods like `process_research_query` in ClinicalResearchAgent.

**Implementation Pattern**: 
```
User Request → Pipeline → Healthcare API `/process` → Agent Router → Specific Agent Method
```

**Next Phase**: Convert agent mock methods to real implementations while maintaining healthcare compliance patterns.

## Core Agent Coordination Principles

### Healthcare Agent Ecosystem

```python
# ✅ ADVANCED: Healthcare agent coordination architecture
class HealthcareAgentCoordinator:
    """Coordinate multiple healthcare AI agents for complex clinical workflows."""
    
    def __init__(self):
        self.agents = {
            "clinical_research": ClinicalResearchAgent(),
            "search_assistant": MedicalSearchAssistant(), 
            "medication_interaction": MedicationInteractionAgent(),
            "emergency_response": EmergencyResponseAgent(),
            "documentation": ClinicalDocumentationAgent(),
            "compliance_validator": HealthcareComplianceAgent()
        }
        
        # Agent capability matrix for intelligent routing
        self.agent_capabilities = {
            "clinical_research": {
                "differential_diagnosis": 0.95,
                "literature_review": 0.90,
                "case_analysis": 0.88,
                "evidence_synthesis": 0.92
            },
            "search_assistant": {
                "quick_facts": 0.95,
                "drug_information": 0.90,
                "guideline_lookup": 0.88,
                "symptom_search": 0.85
            },
            "medication_interaction": {
                "drug_interactions": 0.98,
                "dosage_validation": 0.92,
                "allergy_checking": 0.95,
                "contraindication_analysis": 0.90
            }
        }
    
    def route_clinical_query(self, query: str, clinical_context: Dict[str, Any]) -> List[str]:
        """Route queries to appropriate agents based on clinical context and urgency."""
        
        # Emergency scenarios always get immediate routing
        if self.detect_emergency_keywords(query):
            logger.critical(f"Emergency scenario detected: {query[:100]}...")
            return ["emergency_response", "clinical_research"]
        
        # Multi-dimensional routing based on query analysis
        query_analysis = self.analyze_clinical_query(query, clinical_context)
        
        selected_agents = []
        
        # Complex diagnostic scenarios requiring deep analysis
        if query_analysis.complexity_score > 0.7:
            selected_agents.append("clinical_research")
        
        # Medication-related queries
        if query_analysis.contains_medications:
            selected_agents.append("medication_interaction")
        
        # Quick fact verification during clinical workflows  
        if query_analysis.is_fact_verification and not selected_agents:
            selected_agents.append("search_assistant")
        
        # Documentation needs
        if query_analysis.requires_documentation:
            selected_agents.append("documentation")
        
        # Always include compliance validation for PHI-containing queries
        if query_analysis.contains_phi:
            selected_agents.append("compliance_validator")
        
        # Default to clinical research for medical uncertainty
        if not selected_agents:
            selected_agents.append("clinical_research")
        
        return selected_agents
    
    async def coordinate_multi_agent_workflow(self, case: ClinicalCase) -> ClinicalResult:
        """Coordinate multiple agents for complex clinical cases with intelligent orchestration."""
        
        # Phase 1: Agent selection and task distribution
        selected_agents = self.route_clinical_query(case.query, case.context)
        
        # Create agent-specific tasks with clinical context
        agent_tasks = {}
        for agent_name in selected_agents:
            task = self.create_agent_task(agent_name, case)
            agent_tasks[agent_name] = task
        
        # Phase 2: Parallel execution with healthcare-specific timeout handling
        results = {}
        async with clinical_timeout_context(30):  # 30-second clinical workflow timeout
            
            for agent_name, task in agent_tasks.items():
                try:
                    # Execute with agent-specific timeout
                    agent_timeout = self.get_agent_timeout(agent_name)
                    result = await asyncio.wait_for(task, timeout=agent_timeout)
                    results[agent_name] = result
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Agent {agent_name} timed out for case {case.id}")
                    results[agent_name] = AgentTimeoutResult(agent_name)
                
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed for case {case.id}: {e}")
                    results[agent_name] = AgentErrorResult(agent_name, str(e))
        
        # Phase 3: Intelligent result synthesis with conflict resolution
        synthesis = await self.synthesize_agent_results(results, case)
        
        # Phase 4: Clinical validation and safety checks
        validated_result = await self.validate_clinical_result(synthesis, case)
        
        # Phase 5: Add appropriate medical disclaimers
        final_result = self.add_comprehensive_medical_disclaimers(validated_result)
        
        return final_result
    
    def detect_emergency_keywords(self, query: str) -> bool:
        """Detect emergency scenarios requiring immediate clinical attention."""
        
        emergency_patterns = [
            # Cardiovascular emergencies
            "chest pain", "heart attack", "cardiac arrest", "myocardial infarction",
            # Respiratory emergencies  
            "difficulty breathing", "shortness of breath", "respiratory distress", "can't breathe",
            # Neurological emergencies
            "stroke", "seizure", "unconscious", "loss of consciousness", "paralysis",
            # Severe trauma
            "severe bleeding", "hemorrhage", "traumatic injury", "head trauma",
            # Allergic reactions
            "severe allergic reaction", "anaphylaxis", "throat swelling",
            # Poisoning/overdose
            "poisoning", "overdose", "toxic ingestion",
            # Severe pain
            "severe abdominal pain", "excruciating pain"
        ]
        
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in emergency_patterns)
    
    async def synthesize_agent_results(self, results: Dict[str, Any], case: ClinicalCase) -> ClinicalSynthesis:
        """Intelligently synthesize results from multiple healthcare agents."""
        
        synthesis = ClinicalSynthesis(case_id=case.id)
        
        # Weight agent results based on reliability and relevance
        weighted_results = {}
        for agent_name, result in results.items():
            if isinstance(result, (AgentTimeoutResult, AgentErrorResult)):
                continue
                
            weight = self.calculate_result_weight(agent_name, result, case)
            weighted_results[agent_name] = {
                "result": result,
                "weight": weight,
                "confidence": result.get("confidence", 0.5)
            }
        
        # Synthesize clinical findings with conflict resolution
        clinical_findings = await self.resolve_clinical_conflicts(weighted_results)
        
        # Generate evidence-based recommendations
        recommendations = await self.generate_clinical_recommendations(
            findings=clinical_findings,
            case_context=case.context,
            agent_results=weighted_results
        )
        
        # Quantify diagnostic uncertainty
        uncertainty_metrics = self.quantify_clinical_uncertainty(
            findings=clinical_findings,
            agent_consensus=self.measure_agent_consensus(weighted_results)
        )
        
        synthesis.findings = clinical_findings
        synthesis.recommendations = recommendations
        synthesis.uncertainty = uncertainty_metrics
        synthesis.evidence_quality = self.assess_evidence_quality(weighted_results)
        
        return synthesis
```

## Advanced Agent Coordination Patterns

### Dynamic Agent Selection

```python
# ✅ ADVANCED: Dynamic agent selection based on clinical context
class DynamicAgentSelector:
    """Select optimal agents dynamically based on clinical case characteristics."""
    
    def __init__(self):
        self.agent_performance_history = {}
        self.clinical_specialties = {
            "cardiology": ["clinical_research", "medication_interaction"],
            "neurology": ["clinical_research", "search_assistant"],
            "emergency": ["emergency_response", "clinical_research", "medication_interaction"],
            "pediatrics": ["clinical_research", "medication_interaction", "documentation"],
            "geriatrics": ["medication_interaction", "clinical_research", "search_assistant"]
        }
    
    async def select_optimal_agents(self, case: ClinicalCase) -> List[str]:
        """Select optimal agents based on case complexity and clinical specialty."""
        
        # Base agent selection on clinical specialty
        specialty_agents = self.clinical_specialties.get(case.specialty, ["clinical_research"])
        
        # Enhance selection based on case complexity
        complexity_score = await self.assess_case_complexity(case)
        
        if complexity_score > 0.8:
            # High complexity cases need multiple agents
            enhanced_agents = specialty_agents + ["documentation", "compliance_validator"]
        elif complexity_score > 0.5:
            # Medium complexity cases need targeted agents
            enhanced_agents = specialty_agents + ["compliance_validator"]
        else:
            # Low complexity cases can use minimal agents
            enhanced_agents = specialty_agents[:2]
        
        # Remove duplicates and validate agent availability
        selected_agents = list(set(enhanced_agents))
        available_agents = await self.check_agent_availability(selected_agents)
        
        return available_agents
    
    async def assess_case_complexity(self, case: ClinicalCase) -> float:
        """Assess clinical case complexity for agent selection."""
        
        complexity_factors = {
            "symptom_count": min(len(case.symptoms) / 10, 1.0) * 0.2,
            "medication_count": min(len(case.medications) / 15, 1.0) * 0.15,
            "comorbidity_count": min(len(case.comorbidities) / 5, 1.0) * 0.25,
            "diagnostic_uncertainty": case.get_diagnostic_uncertainty() * 0.3,
            "emergency_indicators": self.assess_emergency_indicators(case) * 0.1
        }
        
        return sum(complexity_factors.values())
```

### Agent Communication Protocols

```python
# ✅ ADVANCED: Healthcare agent communication with medical context preservation
class HealthcareAgentCommunicationManager:
    """Manage communication between healthcare agents with clinical context preservation."""
    
    async def facilitate_agent_collaboration(self, agents: List[str], case: ClinicalCase):
        """Facilitate collaboration between healthcare agents for complex cases."""
        
        # Establish secure communication channels with PHI protection
        communication_channels = {}
        for agent_name in agents:
            channel = await self.create_secure_channel(agent_name, case.id)
            communication_channels[agent_name] = channel
        
        # Share relevant clinical context between agents
        shared_context = await self.prepare_shared_clinical_context(case)
        
        for agent_name, channel in communication_channels.items():
            # Send agent-specific context to preserve clinical relevance
            agent_context = self.filter_context_for_agent(shared_context, agent_name)
            await channel.send_clinical_context(agent_context)
        
        # Monitor inter-agent communication for clinical consistency
        consistency_monitor = ClinicalConsistencyMonitor()
        
        async def monitor_agent_communication():
            while self.collaboration_active:
                # Check for conflicting clinical interpretations
                conflicts = await consistency_monitor.detect_clinical_conflicts(
                    communication_channels
                )
                
                if conflicts:
                    await self.resolve_clinical_conflicts(conflicts, communication_channels)
                
                await asyncio.sleep(1)  # Check every second during active collaboration
        
        # Start communication monitoring
        monitor_task = asyncio.create_task(monitor_agent_communication())
        
        return communication_channels, monitor_task
    
    async def resolve_clinical_conflicts(self, conflicts: List[ClinicalConflict], channels: Dict):
        """Resolve conflicts between agent clinical interpretations."""
        
        for conflict in conflicts:
            # Use evidence-based conflict resolution
            resolution = await self.evidence_based_conflict_resolution(conflict)
            
            # Communicate resolution to affected agents
            for agent_name in conflict.involved_agents:
                await channels[agent_name].send_conflict_resolution(resolution)
            
            # Log conflict resolution for clinical review
            logger.info(f"Resolved clinical conflict: {conflict.description}")
```

## Clinical Workflow Integration Patterns

### Real-Time Agent Coordination

```python
# ✅ ADVANCED: Real-time agent coordination for clinical workflows
class RealTimeClinicalCoordinator:
    """Coordinate agents in real-time during active clinical workflows."""
    
    async def coordinate_real_time_clinical_assistance(self, websocket: WebSocket, case: ClinicalCase):
        """Provide real-time coordinated agent assistance during clinical encounters."""
        
        # Initialize agent coordination for real-time workflow
        coordinator = await self.initialize_real_time_coordination(case)
        
        try:
            async for message in websocket.iter_text():
                # Parse clinical message with PHI protection
                clinical_message = await self.parse_clinical_message(message)
                
                # Determine which agents should respond to this message
                responsive_agents = await coordinator.select_responsive_agents(clinical_message)
                
                # Coordinate agent responses in parallel
                agent_responses = await asyncio.gather(*[
                    self.get_agent_real_time_response(agent, clinical_message)
                    for agent in responsive_agents
                ])
                
                # Synthesize and stream responses back to clinical workflow
                synthesized_response = await coordinator.synthesize_real_time_responses(
                    agent_responses, clinical_message
                )
                
                await websocket.send_json({
                    "type": "coordinated_response",
                    "content": synthesized_response,
                    "agents_consulted": responsive_agents,
                    "timestamp": datetime.now().isoformat(),
                    "medical_disclaimer": "Real-time AI assistance for educational purposes only."
                })
                
        except WebSocketDisconnect:
            await coordinator.cleanup_real_time_session()
```

## Healthcare Agent Performance Optimization

### Agent Load Balancing

```python
# ✅ ADVANCED: Healthcare agent load balancing with clinical priority
class HealthcareAgentLoadBalancer:
    """Balance load across healthcare agents with clinical priority consideration."""
    
    def __init__(self):
        self.agent_queues = {}
        self.clinical_priorities = {
            "emergency": 1,
            "urgent": 2, 
            "routine": 3,
            "research": 4
        }
    
    async def balance_clinical_workload(self, tasks: List[ClinicalTask]) -> Dict[str, List[ClinicalTask]]:
        """Balance clinical tasks across agents based on priority and capacity."""
        
        # Sort tasks by clinical priority
        prioritized_tasks = sorted(
            tasks,
            key=lambda t: (
                self.clinical_priorities.get(t.priority, 5),
                t.complexity_score,
                t.estimated_duration
            )
        )
        
        # Distribute tasks to agents based on capacity and specialization
        agent_assignments = {}
        
        for task in prioritized_tasks:
            # Select best available agent for this clinical task
            optimal_agent = await self.select_optimal_agent(task)
            
            if optimal_agent not in agent_assignments:
                agent_assignments[optimal_agent] = []
            
            agent_assignments[optimal_agent].append(task)
            
            # Update agent capacity tracking
            await self.update_agent_capacity(optimal_agent, task)
        
        return agent_assignments
```

## Integration Guidelines

### Agent Coordination Best Practices

**Multi-Agent Clinical Workflows**:
- Always route emergency scenarios to emergency response agent first
- Use parallel agent execution for complex diagnostic cases
- Implement intelligent conflict resolution between agent findings
- Maintain clinical context throughout agent coordination

**Performance Optimization**:
- Set healthcare-appropriate timeouts for agent responses
- Use dynamic agent selection based on case complexity
- Implement clinical priority-based load balancing
- Monitor agent performance against clinical workflow requirements

**Safety and Compliance**:
- All agent coordination must include PHI protection
- Implement comprehensive audit logging for multi-agent workflows
- Add medical disclaimers to all coordinated agent responses
- Validate clinical consistency across agent findings

**Real-Time Coordination**:
- Support WebSocket-based real-time agent coordination
- Enable streaming responses during clinical encounters  
- Implement emergency priority routing for urgent clinical scenarios
- Maintain clinical context throughout real-time coordination

Remember: Healthcare agent coordination must prioritize patient safety, maintain clinical accuracy, protect PHI throughout all agent interactions, and provide appropriate medical disclaimers for all coordinated clinical assistance.
