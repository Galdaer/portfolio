#!/usr/bin/env python3
"""
Doctor Personalization Service

Provides personalized AI experiences for healthcare providers using LoRA adaptation
and preference learning to tailor responses to individual clinical workflows and styles.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import httpx
import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import redis.asyncio as redis
from transformers import AutoTokenizer

from models.personalization_models import (
    DoctorProfile,
    PersonalizationRequest,
    PersonalizedResponse,
    PersonalizationType,
    SpecialtyArea,
    ExperienceLevel,
    CommunicationStyle,
    LoRAAdapter,
    InteractionFeedback,
    PersonalizationAnalytics,
    PersonalizationRule,
    ModelPerformance,
    PersonalizationConfiguration,
)


class DoctorPersonalizationService:
    def __init__(self):
        self.app = FastAPI(
            title="Doctor Personalization Service",
            description="AI personalization service for healthcare providers",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Model and personalization state
        self.doctor_profiles: Dict[str, DoctorProfile] = {}
        self.lora_adapters: Dict[str, LoRAAdapter] = {}
        self.personalization_rules: Dict[str, PersonalizationRule] = {}
        self.model_cache: Dict[str, Any] = {}
        
        # Configuration
        self.config = PersonalizationConfiguration(
            config_id="default",
            config_name="Default Configuration",
            default_base_model="llama3.1:8b",
            updated_by="system"
        )
        
        self.setup_routes()
        self.setup_middleware()
        
    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                if self.db_pool:
                    async with self.db_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                
                if self.redis_client:
                    await self.redis_client.ping()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow(),
                    "service": "doctor-personalization",
                    "version": "1.0.0",
                    "active_profiles": len(self.doctor_profiles),
                    "active_adapters": len(self.lora_adapters)
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {"status": "unhealthy", "error": str(e)}

        @self.app.post("/profiles/create", response_model=DoctorProfile)
        async def create_doctor_profile(
            profile_data: Dict[str, Any],
            background_tasks: BackgroundTasks
        ):
            """Create a new doctor profile for personalization"""
            try:
                profile = DoctorProfile(
                    profile_id=str(uuid.uuid4()),
                    **profile_data
                )
                
                await self.store_doctor_profile(profile)
                self.doctor_profiles[profile.doctor_id] = profile
                
                # Initialize personalization rules for this profile
                background_tasks.add_task(self.initialize_profile_rules, profile)
                
                return profile
            except Exception as e:
                logger.error(f"Failed to create doctor profile: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/profiles/{doctor_id}", response_model=DoctorProfile)
        async def get_doctor_profile(doctor_id: str):
            """Get doctor profile by ID"""
            try:
                profile = await self.get_doctor_profile(doctor_id)
                if not profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                return profile
            except Exception as e:
                logger.error(f"Failed to get doctor profile: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.put("/profiles/{doctor_id}/update")
        async def update_doctor_profile(
            doctor_id: str,
            updates: Dict[str, Any],
            background_tasks: BackgroundTasks
        ):
            """Update doctor profile preferences"""
            try:
                profile = await self.get_doctor_profile(doctor_id)
                if not profile:
                    raise HTTPException(status_code=404, detail="Profile not found")
                
                # Update profile with new data
                for key, value in updates.items():
                    if hasattr(profile, key):
                        setattr(profile, key, value)
                
                profile.last_updated = datetime.utcnow()
                
                await self.store_doctor_profile(profile)
                self.doctor_profiles[doctor_id] = profile
                
                # Retrain personalization models if needed
                background_tasks.add_task(self.update_personalization_models, doctor_id)
                
                return {"status": "updated", "profile_id": profile.profile_id}
            except Exception as e:
                logger.error(f"Failed to update doctor profile: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/personalize", response_model=PersonalizedResponse)
        async def personalize_response(
            request: PersonalizationRequest,
            background_tasks: BackgroundTasks
        ):
            """Generate personalized AI response for a healthcare provider"""
            try:
                start_time = datetime.utcnow()
                
                # Get doctor profile
                profile = await self.get_doctor_profile(request.doctor_id)
                if not profile:
                    raise HTTPException(status_code=404, detail="Doctor profile not found")
                
                # Generate personalized response
                response = await self.generate_personalized_response(request, profile)
                
                # Record interaction for learning
                background_tasks.add_task(self.record_interaction, request, response, profile)
                
                # Update profile interaction history
                background_tasks.add_task(self.update_interaction_history, profile, request, response)
                
                return response
                
            except Exception as e:
                logger.error(f"Failed to generate personalized response: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/feedback/submit")
        async def submit_feedback(
            feedback: InteractionFeedback,
            background_tasks: BackgroundTasks
        ):
            """Submit feedback on personalized interactions"""
            try:
                await self.store_interaction_feedback(feedback)
                
                # Use feedback to improve personalization
                background_tasks.add_task(self.process_feedback_for_learning, feedback)
                
                return {
                    "feedback_id": feedback.feedback_id,
                    "status": "submitted",
                    "overall_score": feedback.overall_score
                }
            except Exception as e:
                logger.error(f"Failed to submit feedback: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/analytics/{doctor_id}", response_model=PersonalizationAnalytics)
        async def get_personalization_analytics(
            doctor_id: str,
            period_days: int = 30
        ):
            """Get personalization analytics for a doctor"""
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                analytics = await self.generate_personalization_analytics(
                    doctor_id, start_date, end_date
                )
                
                return analytics
            except Exception as e:
                logger.error(f"Failed to get personalization analytics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/adapters", response_model=List[LoRAAdapter])
        async def list_lora_adapters():
            """List available LoRA adapters"""
            try:
                return list(self.lora_adapters.values())
            except Exception as e:
                logger.error(f"Failed to list LoRA adapters: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/adapters/create")
        async def create_lora_adapter(
            adapter_data: Dict[str, Any],
            background_tasks: BackgroundTasks
        ):
            """Create a new LoRA adapter"""
            try:
                adapter = LoRAAdapter(
                    adapter_id=str(uuid.uuid4()),
                    **adapter_data
                )
                
                await self.store_lora_adapter(adapter)
                self.lora_adapters[adapter.adapter_id] = adapter
                
                # Train the adapter in background
                background_tasks.add_task(self.train_lora_adapter, adapter)
                
                return {
                    "adapter_id": adapter.adapter_id,
                    "status": "created",
                    "training_status": "queued"
                }
            except Exception as e:
                logger.error(f"Failed to create LoRA adapter: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/models/performance")
        async def get_model_performance(
            doctor_id: Optional[str] = None,
            period_days: int = 7
        ):
            """Get model performance metrics"""
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                performance = await self.calculate_model_performance(
                    doctor_id, start_date, end_date
                )
                
                return performance
            except Exception as e:
                logger.error(f"Failed to get model performance: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/rules/create")
        async def create_personalization_rule(rule: PersonalizationRule):
            """Create a new personalization rule"""
            try:
                await self.store_personalization_rule(rule)
                self.personalization_rules[rule.rule_id] = rule
                
                return {
                    "rule_id": rule.rule_id,
                    "status": "created",
                    "enabled": rule.enabled
                }
            except Exception as e:
                logger.error(f"Failed to create personalization rule: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/configuration", response_model=PersonalizationConfiguration)
        async def get_configuration():
            """Get current personalization configuration"""
            return self.config

        @self.app.put("/configuration/update")
        async def update_configuration(
            config_updates: Dict[str, Any],
            updated_by: str
        ):
            """Update personalization configuration"""
            try:
                for key, value in config_updates.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                
                self.config.last_updated = datetime.utcnow()
                self.config.updated_by = updated_by
                
                await self.store_configuration(self.config)
                
                return {
                    "status": "updated",
                    "config_id": self.config.config_id,
                    "updated_by": updated_by
                }
            except Exception as e:
                logger.error(f"Failed to update configuration: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def startup(self):
        """Initialize service connections and load models"""
        try:
            # Initialize database connection
            postgres_url = os.getenv('POSTGRES_URL')
            if not postgres_url:
                raise ValueError("POSTGRES_URL environment variable not set")
            
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=5, max_size=20)
            await self.create_tables()
            
            # Initialize Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://172.20.0.12:6379')
            self.redis_client = redis.from_url(redis_url)
            
            # Initialize HTTP client for Ollama communication
            self.http_client = httpx.AsyncClient(timeout=60.0)
            
            # Load existing profiles, adapters, and rules
            await self.load_doctor_profiles()
            await self.load_lora_adapters()
            await self.load_personalization_rules()
            await self.load_configuration()
            
            # Initialize model cache
            await self.initialize_model_cache()
            
            logger.info("Doctor Personalization service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Doctor Personalization service: {e}")
            raise

    async def shutdown(self):
        """Clean up resources"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()

    async def create_tables(self):
        """Create database tables for personalization service"""
        async with self.db_pool.acquire() as conn:
            # Doctor profiles table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS doctor_profiles (
                    profile_id VARCHAR PRIMARY KEY,
                    doctor_id VARCHAR UNIQUE NOT NULL,
                    name VARCHAR NOT NULL,
                    specialty VARCHAR NOT NULL,
                    subspecialties TEXT[],
                    experience_level VARCHAR NOT NULL,
                    years_experience INTEGER,
                    communication_style VARCHAR NOT NULL,
                    documentation_style JSONB DEFAULT '{}',
                    clinical_interests TEXT[],
                    workflow_preferences JSONB DEFAULT '{}',
                    ai_assistance_preferences JSONB DEFAULT '{}',
                    interaction_history JSONB DEFAULT '[]',
                    feedback_scores JSONB DEFAULT '{}',
                    learning_objectives TEXT[],
                    preferred_models TEXT[],
                    lora_adapters TEXT[],
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_interaction TIMESTAMP WITH TIME ZONE,
                    active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # LoRA adapters table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS lora_adapters (
                    adapter_id VARCHAR PRIMARY KEY,
                    adapter_name VARCHAR NOT NULL,
                    adapter_type VARCHAR NOT NULL,
                    target_doctors TEXT[],
                    base_model VARCHAR NOT NULL,
                    training_data_sources TEXT[],
                    training_parameters JSONB DEFAULT '{}',
                    validation_score NUMERIC,
                    improvement_metrics JSONB DEFAULT '{}',
                    adapter_path VARCHAR NOT NULL,
                    config_path VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_used TIMESTAMP WITH TIME ZONE,
                    usage_count INTEGER DEFAULT 0
                )
            ''')
            
            # Personalized responses table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS personalized_responses (
                    response_id VARCHAR PRIMARY KEY,
                    request_id VARCHAR NOT NULL,
                    doctor_id VARCHAR NOT NULL,
                    personalized_content TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    adaptations_applied TEXT[],
                    model_used VARCHAR NOT NULL,
                    lora_adapters_used TEXT[],
                    confidence_score NUMERIC NOT NULL,
                    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processing_time_ms INTEGER NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    personalization_score NUMERIC NOT NULL
                )
            ''')
            
            # Interaction feedback table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS interaction_feedback (
                    feedback_id VARCHAR PRIMARY KEY,
                    response_id VARCHAR NOT NULL,
                    doctor_id VARCHAR NOT NULL,
                    relevance_score NUMERIC NOT NULL,
                    accuracy_score NUMERIC NOT NULL,
                    helpfulness_score NUMERIC NOT NULL,
                    personalization_score NUMERIC NOT NULL,
                    overall_score NUMERIC NOT NULL,
                    comments TEXT,
                    suggested_improvements TEXT[],
                    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    interaction_context JSONB DEFAULT '{}'
                )
            ''')
            
            # Personalization rules table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS personalization_rules (
                    rule_id VARCHAR PRIMARY KEY,
                    rule_name VARCHAR NOT NULL,
                    description TEXT,
                    conditions JSONB NOT NULL,
                    target_profiles TEXT[],
                    adaptations JSONB NOT NULL,
                    response_modifications JSONB DEFAULT '{}',
                    priority INTEGER DEFAULT 1,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_triggered TIMESTAMP WITH TIME ZONE,
                    trigger_count INTEGER DEFAULT 0
                )
            ''')
            
            # Configuration table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS personalization_config (
                    config_id VARCHAR PRIMARY KEY,
                    config_name VARCHAR NOT NULL,
                    personalization_enabled BOOLEAN DEFAULT TRUE,
                    adaptation_aggressiveness NUMERIC DEFAULT 0.5,
                    learning_rate NUMERIC DEFAULT 0.01,
                    default_base_model VARCHAR NOT NULL,
                    max_lora_adapters INTEGER DEFAULT 3,
                    model_cache_size INTEGER DEFAULT 5,
                    phi_protection_level VARCHAR DEFAULT 'strict',
                    content_filtering BOOLEAN DEFAULT TRUE,
                    audit_all_interactions BOOLEAN DEFAULT TRUE,
                    max_response_time INTEGER DEFAULT 30000,
                    concurrent_requests_limit INTEGER DEFAULT 100,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_by VARCHAR NOT NULL
                )
            ''')

    async def generate_personalized_response(
        self, request: PersonalizationRequest, profile: DoctorProfile
    ) -> PersonalizedResponse:
        """Generate a personalized AI response based on doctor profile"""
        start_time = datetime.utcnow()
        
        try:
            # Apply personalization rules
            adaptations = await self.determine_adaptations(request, profile)
            
            # Select appropriate model and adapters
            model_config = await self.select_model_configuration(profile, request)
            
            # Generate base response from Ollama
            base_response = await self.get_base_response(
                request.context, model_config["model"], request.task_type
            )
            
            # Apply personalization transformations
            personalized_content = await self.apply_personalization(
                base_response, adaptations, profile, request
            )
            
            # Calculate confidence and personalization scores
            confidence_score = await self.calculate_confidence_score(
                personalized_content, profile, request
            )
            personalization_score = await self.calculate_personalization_score(
                base_response, personalized_content, adaptations
            )
            
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            response = PersonalizedResponse(
                response_id=str(uuid.uuid4()),
                request_id=request.request_id,
                doctor_id=request.doctor_id,
                personalized_content=personalized_content,
                reasoning=f"Applied {len(adaptations)} personalizations based on profile preferences",
                adaptations_applied=adaptations,
                model_used=model_config["model"],
                lora_adapters_used=model_config.get("adapters", []),
                confidence_score=confidence_score,
                processing_time_ms=processing_time,
                personalization_score=personalization_score
            )
            
            # Store response
            await self.store_personalized_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate personalized response: {e}")
            raise

    async def determine_adaptations(
        self, request: PersonalizationRequest, profile: DoctorProfile
    ) -> List[str]:
        """Determine which adaptations to apply based on profile and context"""
        adaptations = []
        
        # Communication style adaptations
        if profile.communication_style == CommunicationStyle.DIRECT:
            adaptations.append("direct_communication")
        elif profile.communication_style == CommunicationStyle.DETAILED:
            adaptations.append("detailed_explanations")
        elif profile.communication_style == CommunicationStyle.CONCISE:
            adaptations.append("concise_responses")
        
        # Experience level adaptations
        if profile.experience_level == ExperienceLevel.RESIDENT:
            adaptations.append("educational_context")
        elif profile.experience_level == ExperienceLevel.SENIOR_ATTENDING:
            adaptations.append("expert_level_detail")
        
        # Specialty-specific adaptations
        specialty_adaptations = {
            SpecialtyArea.CARDIOLOGY: "cardiology_focus",
            SpecialtyArea.PEDIATRICS: "pediatric_considerations",
            SpecialtyArea.EMERGENCY_MEDICINE: "emergency_protocols",
            SpecialtyArea.SURGERY: "surgical_perspective"
        }
        
        if profile.specialty in specialty_adaptations:
            adaptations.append(specialty_adaptations[profile.specialty])
        
        # Task-type specific adaptations
        if request.personalization_type == PersonalizationType.DOCUMENTATION_PREFERENCES:
            if profile.documentation_style.get("format") == "structured":
                adaptations.append("structured_documentation")
            elif profile.documentation_style.get("format") == "narrative":
                adaptations.append("narrative_documentation")
        
        # Apply personalization rules
        rule_adaptations = await self.apply_personalization_rules(request, profile)
        adaptations.extend(rule_adaptations)
        
        return list(set(adaptations))  # Remove duplicates

    async def apply_personalization_rules(
        self, request: PersonalizationRequest, profile: DoctorProfile
    ) -> List[str]:
        """Apply dynamic personalization rules"""
        rule_adaptations = []
        
        for rule in self.personalization_rules.values():
            if not rule.enabled:
                continue
                
            # Check if rule conditions match
            if await self.evaluate_rule_conditions(rule, request, profile):
                # Apply rule adaptations
                for adaptation in rule.adaptations.get("add", []):
                    rule_adaptations.append(adaptation)
                
                # Update rule trigger count
                await self.update_rule_trigger_count(rule.rule_id)
        
        return rule_adaptations

    async def evaluate_rule_conditions(
        self, rule: PersonalizationRule, request: PersonalizationRequest, profile: DoctorProfile
    ) -> bool:
        """Evaluate if rule conditions are met"""
        conditions = rule.conditions
        
        # Check profile conditions
        if "specialty" in conditions:
            if profile.specialty.value not in conditions["specialty"]:
                return False
        
        if "experience_level" in conditions:
            if profile.experience_level.value not in conditions["experience_level"]:
                return False
        
        if "communication_style" in conditions:
            if profile.communication_style.value not in conditions["communication_style"]:
                return False
        
        # Check request conditions
        if "personalization_type" in conditions:
            if request.personalization_type.value not in conditions["personalization_type"]:
                return False
        
        if "task_type" in conditions:
            if request.task_type not in conditions["task_type"]:
                return False
        
        return True

    async def select_model_configuration(
        self, profile: DoctorProfile, request: PersonalizationRequest
    ) -> Dict[str, Any]:
        """Select the best model and adapter configuration"""
        config = {
            "model": self.config.default_base_model,
            "adapters": []
        }
        
        # Use profile's preferred model if available
        if profile.preferred_models:
            config["model"] = profile.preferred_models[0]
        
        # Select LoRA adapters
        suitable_adapters = []
        for adapter_id in profile.lora_adapters:
            if adapter_id in self.lora_adapters:
                adapter = self.lora_adapters[adapter_id]
                if adapter.status == "active" and profile.doctor_id in adapter.target_doctors:
                    suitable_adapters.append(adapter_id)
        
        # Limit number of adapters
        config["adapters"] = suitable_adapters[:self.config.max_lora_adapters]
        
        return config

    async def get_base_response(self, context: str, model: str, task_type: str) -> str:
        """Get base response from Ollama"""
        try:
            ollama_host = os.getenv('OLLAMA_HOST', 'http://172.20.0.10:11434')
            
            # Prepare prompt with task-specific instructions
            task_prompts = {
                "clinical_reasoning": "Provide clinical reasoning for the following case:",
                "documentation": "Help create clinical documentation for:",
                "differential_diagnosis": "Generate differential diagnosis for:",
                "treatment_planning": "Suggest treatment plan for:",
                "patient_education": "Create patient education material for:"
            }
            
            prompt = task_prompts.get(task_type, "Respond to:") + "\n\n" + context
            
            async with self.http_client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return "Error generating response from base model"
                    
        except Exception as e:
            logger.error(f"Failed to get base response: {e}")
            return "Error communicating with AI model"

    async def apply_personalization(
        self, base_response: str, adaptations: List[str], 
        profile: DoctorProfile, request: PersonalizationRequest
    ) -> str:
        """Apply personalization adaptations to base response"""
        personalized = base_response
        
        # Apply communication style adaptations
        if "direct_communication" in adaptations:
            personalized = await self.adapt_for_direct_style(personalized)
        elif "detailed_explanations" in adaptations:
            personalized = await self.adapt_for_detailed_style(personalized)
        elif "concise_responses" in adaptations:
            personalized = await self.adapt_for_concise_style(personalized)
        
        # Apply experience-level adaptations
        if "educational_context" in adaptations:
            personalized = await self.add_educational_context(personalized)
        elif "expert_level_detail" in adaptations:
            personalized = await self.add_expert_details(personalized)
        
        # Apply specialty-specific adaptations
        specialty_adapters = {
            "cardiology_focus": self.adapt_for_cardiology,
            "pediatric_considerations": self.adapt_for_pediatrics,
            "emergency_protocols": self.adapt_for_emergency,
            "surgical_perspective": self.adapt_for_surgery
        }
        
        for adaptation in adaptations:
            if adaptation in specialty_adapters:
                personalized = await specialty_adapters[adaptation](personalized)
        
        # Apply documentation style adaptations
        if "structured_documentation" in adaptations:
            personalized = await self.format_as_structured_doc(personalized)
        elif "narrative_documentation" in adaptations:
            personalized = await self.format_as_narrative_doc(personalized)
        
        return personalized

    async def adapt_for_direct_style(self, content: str) -> str:
        """Adapt content for direct communication style"""
        # Simplify language, remove hedging, make statements more definitive
        adaptations = [
            ("might be", "is likely"),
            ("could be", "is probably"),
            ("perhaps", ""),
            ("it seems", ""),
            ("I think", "")
        ]
        
        adapted = content
        for old, new in adaptations:
            adapted = adapted.replace(old, new)
        
        return adapted

    async def adapt_for_detailed_style(self, content: str) -> str:
        """Adapt content for detailed communication style"""
        # Add more explanatory context and background information
        if len(content) < 500:  # If response is short, add more detail
            detail_prompt = f"Provide more detailed explanation for: {content[:200]}..."
            detailed_response = await self.get_base_response(
                detail_prompt, self.config.default_base_model, "explanation"
            )
            return content + "\n\nAdditional Details:\n" + detailed_response
        return content

    async def adapt_for_concise_style(self, content: str) -> str:
        """Adapt content for concise communication style"""
        # Summarize and remove redundant information
        if len(content) > 300:  # If response is long, summarize
            summary_prompt = f"Provide a concise summary of: {content}"
            summary = await self.get_base_response(
                summary_prompt, self.config.default_base_model, "summarization"
            )
            return summary
        return content

    async def add_educational_context(self, content: str) -> str:
        """Add educational context for trainees"""
        return f"Educational Context: {content}\n\nLearning Points:\n- This case demonstrates important clinical principles\n- Consider reviewing relevant guidelines and literature"

    async def add_expert_details(self, content: str) -> str:
        """Add expert-level clinical details"""
        return f"{content}\n\nAdvanced Considerations:\n- Review latest evidence and guidelines\n- Consider rare differentials and complex interactions"

    async def adapt_for_cardiology(self, content: str) -> str:
        """Add cardiology-specific focus"""
        return f"Cardiology Focus: {content}\n\nCardiovascular Considerations: Monitor hemodynamics, consider cardiac risk factors"

    async def adapt_for_pediatrics(self, content: str) -> str:
        """Add pediatric considerations"""
        return f"Pediatric Considerations: {content}\n\nAge-specific factors: Dosing, developmental considerations, family involvement"

    async def adapt_for_emergency(self, content: str) -> str:
        """Add emergency medicine protocols"""
        return f"Emergency Protocol: {content}\n\nUrgent Actions: Stabilize, assess, prioritize interventions"

    async def adapt_for_surgery(self, content: str) -> str:
        """Add surgical perspective"""
        return f"Surgical Perspective: {content}\n\nOperative Considerations: Anatomy, approach, risks, alternatives"

    async def format_as_structured_doc(self, content: str) -> str:
        """Format content as structured documentation"""
        return f"""
ASSESSMENT:
{content}

PLAN:
- [To be determined based on clinical judgment]

FOLLOW-UP:
- [Schedule appropriate follow-up]
"""

    async def format_as_narrative_doc(self, content: str) -> str:
        """Format content as narrative documentation"""
        return f"Clinical Assessment: {content} The patient will continue to be monitored with appropriate follow-up as clinically indicated."

    async def calculate_confidence_score(
        self, content: str, profile: DoctorProfile, request: PersonalizationRequest
    ) -> float:
        """Calculate confidence score for personalized response"""
        # Mock confidence calculation - would use actual model confidence in production
        base_confidence = 0.8
        
        # Adjust based on profile completeness
        if len(profile.interaction_history) > 10:
            base_confidence += 0.1
        
        # Adjust based on specialization match
        if request.task_type in ["clinical_reasoning", "differential_diagnosis"]:
            if profile.specialty in [SpecialtyArea.INTERNAL_MEDICINE, SpecialtyArea.FAMILY_MEDICINE]:
                base_confidence += 0.05
        
        return min(1.0, base_confidence)

    async def calculate_personalization_score(
        self, base_response: str, personalized_content: str, adaptations: List[str]
    ) -> float:
        """Calculate degree of personalization applied"""
        # Simple metric based on content difference and adaptations applied
        content_diff = abs(len(personalized_content) - len(base_response)) / max(len(base_response), 1)
        adaptation_score = len(adaptations) / 10.0  # Normalize by max expected adaptations
        
        return min(1.0, (content_diff + adaptation_score) / 2)

    async def store_doctor_profile(self, profile: DoctorProfile):
        """Store doctor profile in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO doctor_profiles (
                    profile_id, doctor_id, name, specialty, subspecialties,
                    experience_level, years_experience, communication_style,
                    documentation_style, clinical_interests, workflow_preferences,
                    ai_assistance_preferences, interaction_history, feedback_scores,
                    learning_objectives, preferred_models, lora_adapters,
                    last_updated, last_interaction, active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                ON CONFLICT (doctor_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    specialty = EXCLUDED.specialty,
                    subspecialties = EXCLUDED.subspecialties,
                    experience_level = EXCLUDED.experience_level,
                    years_experience = EXCLUDED.years_experience,
                    communication_style = EXCLUDED.communication_style,
                    documentation_style = EXCLUDED.documentation_style,
                    clinical_interests = EXCLUDED.clinical_interests,
                    workflow_preferences = EXCLUDED.workflow_preferences,
                    ai_assistance_preferences = EXCLUDED.ai_assistance_preferences,
                    interaction_history = EXCLUDED.interaction_history,
                    feedback_scores = EXCLUDED.feedback_scores,
                    learning_objectives = EXCLUDED.learning_objectives,
                    preferred_models = EXCLUDED.preferred_models,
                    lora_adapters = EXCLUDED.lora_adapters,
                    last_updated = EXCLUDED.last_updated,
                    last_interaction = EXCLUDED.last_interaction,
                    active = EXCLUDED.active
            ''',
                profile.profile_id, profile.doctor_id, profile.name,
                profile.specialty.value, [s.value for s in profile.subspecialties],
                profile.experience_level.value, profile.years_experience,
                profile.communication_style.value,
                json.dumps(profile.documentation_style),
                profile.clinical_interests,
                json.dumps(profile.workflow_preferences),
                json.dumps(profile.ai_assistance_preferences),
                json.dumps([h for h in profile.interaction_history]),
                json.dumps(profile.feedback_scores),
                profile.learning_objectives, profile.preferred_models,
                profile.lora_adapters, profile.last_updated,
                profile.last_interaction, profile.active
            )

    async def get_doctor_profile(self, doctor_id: str) -> Optional[DoctorProfile]:
        """Get doctor profile from cache or database"""
        if doctor_id in self.doctor_profiles:
            return self.doctor_profiles[doctor_id]
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM doctor_profiles WHERE doctor_id = $1 AND active = TRUE",
                doctor_id
            )
            
            if row:
                profile_data = dict(row)
                # Convert JSON fields
                profile_data['documentation_style'] = json.loads(profile_data['documentation_style'] or '{}')
                profile_data['workflow_preferences'] = json.loads(profile_data['workflow_preferences'] or '{}')
                profile_data['ai_assistance_preferences'] = json.loads(profile_data['ai_assistance_preferences'] or '{}')
                profile_data['interaction_history'] = json.loads(profile_data['interaction_history'] or '[]')
                profile_data['feedback_scores'] = json.loads(profile_data['feedback_scores'] or '{}')
                
                # Convert enum fields
                profile_data['specialty'] = SpecialtyArea(profile_data['specialty'])
                profile_data['subspecialties'] = [SpecialtyArea(s) for s in (profile_data['subspecialties'] or [])]
                profile_data['experience_level'] = ExperienceLevel(profile_data['experience_level'])
                profile_data['communication_style'] = CommunicationStyle(profile_data['communication_style'])
                
                profile = DoctorProfile(**profile_data)
                self.doctor_profiles[doctor_id] = profile
                return profile
        
        return None

    async def store_personalized_response(self, response: PersonalizedResponse):
        """Store personalized response in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO personalized_responses (
                    response_id, request_id, doctor_id, personalized_content,
                    reasoning, adaptations_applied, model_used, lora_adapters_used,
                    confidence_score, processing_time_ms, tokens_used, personalization_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ''',
                response.response_id, response.request_id, response.doctor_id,
                response.personalized_content, response.reasoning,
                response.adaptations_applied, response.model_used,
                response.lora_adapters_used, response.confidence_score,
                response.processing_time_ms, response.tokens_used,
                response.personalization_score
            )

    async def store_interaction_feedback(self, feedback: InteractionFeedback):
        """Store interaction feedback in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO interaction_feedback (
                    feedback_id, response_id, doctor_id, relevance_score,
                    accuracy_score, helpfulness_score, personalization_score,
                    overall_score, comments, suggested_improvements, interaction_context
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''',
                feedback.feedback_id, feedback.response_id, feedback.doctor_id,
                feedback.relevance_score, feedback.accuracy_score,
                feedback.helpfulness_score, feedback.personalization_score,
                feedback.overall_score, feedback.comments,
                feedback.suggested_improvements,
                json.dumps(feedback.interaction_context)
            )

    async def load_doctor_profiles(self):
        """Load doctor profiles from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM doctor_profiles WHERE active = TRUE")
                
                for row in rows:
                    profile_data = dict(row)
                    # Convert fields as in get_doctor_profile
                    profile_data['documentation_style'] = json.loads(profile_data['documentation_style'] or '{}')
                    profile_data['workflow_preferences'] = json.loads(profile_data['workflow_preferences'] or '{}')
                    profile_data['ai_assistance_preferences'] = json.loads(profile_data['ai_assistance_preferences'] or '{}')
                    profile_data['interaction_history'] = json.loads(profile_data['interaction_history'] or '[]')
                    profile_data['feedback_scores'] = json.loads(profile_data['feedback_scores'] or '{}')
                    
                    profile_data['specialty'] = SpecialtyArea(profile_data['specialty'])
                    profile_data['subspecialties'] = [SpecialtyArea(s) for s in (profile_data['subspecialties'] or [])]
                    profile_data['experience_level'] = ExperienceLevel(profile_data['experience_level'])
                    profile_data['communication_style'] = CommunicationStyle(profile_data['communication_style'])
                    
                    profile = DoctorProfile(**profile_data)
                    self.doctor_profiles[profile.doctor_id] = profile
                    
            logger.info(f"Loaded {len(self.doctor_profiles)} doctor profiles")
            
        except Exception as e:
            logger.error(f"Failed to load doctor profiles: {e}")

    async def load_lora_adapters(self):
        """Load LoRA adapters from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM lora_adapters WHERE status = 'active'")
                
                for row in rows:
                    adapter_data = dict(row)
                    adapter_data['training_parameters'] = json.loads(adapter_data['training_parameters'] or '{}')
                    adapter_data['improvement_metrics'] = json.loads(adapter_data['improvement_metrics'] or '{}')
                    
                    adapter = LoRAAdapter(**adapter_data)
                    self.lora_adapters[adapter.adapter_id] = adapter
                    
            logger.info(f"Loaded {len(self.lora_adapters)} LoRA adapters")
            
        except Exception as e:
            logger.error(f"Failed to load LoRA adapters: {e}")

    async def load_personalization_rules(self):
        """Load personalization rules from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM personalization_rules WHERE enabled = TRUE")
                
                for row in rows:
                    rule_data = dict(row)
                    rule_data['conditions'] = json.loads(rule_data['conditions'])
                    rule_data['adaptations'] = json.loads(rule_data['adaptations'])
                    rule_data['response_modifications'] = json.loads(rule_data['response_modifications'] or '{}')
                    
                    rule = PersonalizationRule(**rule_data)
                    self.personalization_rules[rule.rule_id] = rule
                    
            logger.info(f"Loaded {len(self.personalization_rules)} personalization rules")
            
        except Exception as e:
            logger.error(f"Failed to load personalization rules: {e}")

    async def load_configuration(self):
        """Load personalization configuration"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM personalization_config ORDER BY last_updated DESC LIMIT 1"
                )
                
                if row:
                    config_data = dict(row)
                    self.config = PersonalizationConfiguration(**config_data)
                else:
                    # Store default config
                    await self.store_configuration(self.config)
                    
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")

    async def store_configuration(self, config: PersonalizationConfiguration):
        """Store personalization configuration"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO personalization_config (
                    config_id, config_name, personalization_enabled,
                    adaptation_aggressiveness, learning_rate, default_base_model,
                    max_lora_adapters, model_cache_size, phi_protection_level,
                    content_filtering, audit_all_interactions, max_response_time,
                    concurrent_requests_limit, last_updated, updated_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (config_id) DO UPDATE SET
                    config_name = EXCLUDED.config_name,
                    personalization_enabled = EXCLUDED.personalization_enabled,
                    adaptation_aggressiveness = EXCLUDED.adaptation_aggressiveness,
                    learning_rate = EXCLUDED.learning_rate,
                    default_base_model = EXCLUDED.default_base_model,
                    max_lora_adapters = EXCLUDED.max_lora_adapters,
                    model_cache_size = EXCLUDED.model_cache_size,
                    phi_protection_level = EXCLUDED.phi_protection_level,
                    content_filtering = EXCLUDED.content_filtering,
                    audit_all_interactions = EXCLUDED.audit_all_interactions,
                    max_response_time = EXCLUDED.max_response_time,
                    concurrent_requests_limit = EXCLUDED.concurrent_requests_limit,
                    last_updated = EXCLUDED.last_updated,
                    updated_by = EXCLUDED.updated_by
            ''',
                config.config_id, config.config_name, config.personalization_enabled,
                config.adaptation_aggressiveness, config.learning_rate,
                config.default_base_model, config.max_lora_adapters,
                config.model_cache_size, config.phi_protection_level,
                config.content_filtering, config.audit_all_interactions,
                config.max_response_time, config.concurrent_requests_limit,
                config.last_updated, config.updated_by
            )

    async def initialize_model_cache(self):
        """Initialize model cache with commonly used models"""
        # This would preload models in production
        logger.info("Model cache initialized")

    async def initialize_profile_rules(self, profile: DoctorProfile):
        """Initialize default personalization rules for new profile"""
        # Create specialty-specific rules
        pass

    async def update_personalization_models(self, doctor_id: str):
        """Update personalization models based on new profile data"""
        # This would retrain or fine-tune models in production
        pass

    async def record_interaction(
        self, request: PersonalizationRequest, 
        response: PersonalizedResponse, 
        profile: DoctorProfile
    ):
        """Record interaction for learning purposes"""
        interaction_data = {
            "request_id": request.request_id,
            "response_id": response.response_id,
            "timestamp": datetime.utcnow().isoformat(),
            "personalization_type": request.personalization_type.value,
            "adaptations_applied": response.adaptations_applied,
            "personalization_score": response.personalization_score
        }
        
        # Store in Redis for real-time analytics
        await self.redis_client.lpush(
            f"interactions:{profile.doctor_id}",
            json.dumps(interaction_data)
        )
        await self.redis_client.ltrim(f"interactions:{profile.doctor_id}", 0, 1000)

    async def update_interaction_history(
        self, profile: DoctorProfile,
        request: PersonalizationRequest, 
        response: PersonalizedResponse
    ):
        """Update profile interaction history"""
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_type": request.personalization_type.value,
            "task_type": request.task_type,
            "adaptations": response.adaptations_applied,
            "satisfaction": None  # Will be filled when feedback is received
        }
        
        profile.interaction_history.append(history_entry)
        
        # Keep only recent interactions
        if len(profile.interaction_history) > 100:
            profile.interaction_history = profile.interaction_history[-100:]
        
        profile.last_interaction = datetime.utcnow()
        
        # Update in database
        await self.store_doctor_profile(profile)

    async def process_feedback_for_learning(self, feedback: InteractionFeedback):
        """Process feedback to improve personalization"""
        # Update profile feedback scores
        profile = await self.get_doctor_profile(feedback.doctor_id)
        if profile:
            # Update rolling average of feedback scores
            for score_type in ['relevance', 'accuracy', 'helpfulness', 'personalization', 'overall']:
                current_score = getattr(feedback, f"{score_type}_score")
                if score_type in profile.feedback_scores:
                    # Weighted average with recent feedback having more weight
                    profile.feedback_scores[score_type] = (
                        profile.feedback_scores[score_type] * 0.8 + current_score * 0.2
                    )
                else:
                    profile.feedback_scores[score_type] = current_score
            
            await self.store_doctor_profile(profile)

    async def generate_personalization_analytics(
        self, doctor_id: str, start_date: datetime, end_date: datetime
    ) -> PersonalizationAnalytics:
        """Generate personalization analytics for a doctor"""
        # Mock analytics - would calculate from real data
        return PersonalizationAnalytics(
            analytics_id=str(uuid.uuid4()),
            doctor_id=doctor_id,
            period_start=start_date,
            period_end=end_date,
            total_interactions=50,
            personalization_types_used={
                "clinical_reasoning": 20,
                "documentation": 15,
                "decision_support": 15
            },
            models_used={"llama3.1:8b": 45, "medpalm": 5},
            average_response_time=2.5,
            average_personalization_score=0.75,
            user_satisfaction_score=4.2,
            feedback_summary={
                "relevance": 4.1,
                "accuracy": 4.3,
                "helpfulness": 4.0,
                "personalization": 4.2,
                "overall": 4.15
            }
        )

    async def calculate_model_performance(
        self, doctor_id: Optional[str], start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate model performance metrics"""
        # Mock performance data
        return {
            "models": {
                "llama3.1:8b": {
                    "accuracy": 0.85,
                    "user_satisfaction": 4.1,
                    "average_response_time": 2.3,
                    "total_requests": 100
                }
            },
            "adapters": {
                "cardiology_v1": {
                    "effectiveness": 0.78,
                    "usage_count": 25,
                    "satisfaction_improvement": 0.15
                }
            }
        }

    async def store_lora_adapter(self, adapter: LoRAAdapter):
        """Store LoRA adapter configuration in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO lora_adapters (
                    adapter_id, adapter_name, adapter_type, target_doctors,
                    base_model, training_data_sources, training_parameters,
                    validation_score, improvement_metrics, adapter_path,
                    config_path, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ''',
                adapter.adapter_id, adapter.adapter_name, adapter.adapter_type,
                adapter.target_doctors, adapter.base_model,
                adapter.training_data_sources,
                json.dumps(adapter.training_parameters),
                adapter.validation_score,
                json.dumps(adapter.improvement_metrics),
                adapter.adapter_path, adapter.config_path, adapter.status
            )

    async def store_personalization_rule(self, rule: PersonalizationRule):
        """Store personalization rule in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO personalization_rules (
                    rule_id, rule_name, description, conditions, target_profiles,
                    adaptations, response_modifications, priority, enabled
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
                rule.rule_id, rule.rule_name, rule.description,
                json.dumps(rule.conditions), rule.target_profiles,
                json.dumps(rule.adaptations),
                json.dumps(rule.response_modifications),
                rule.priority, rule.enabled
            )

    async def update_rule_trigger_count(self, rule_id: str):
        """Update rule trigger count and timestamp"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE personalization_rules 
                SET trigger_count = trigger_count + 1,
                    last_triggered = NOW()
                WHERE rule_id = $1
            ''', rule_id)

    async def train_lora_adapter(self, adapter: LoRAAdapter):
        """Train LoRA adapter (background task)"""
        # Mock training process
        logger.info(f"Starting training for LoRA adapter {adapter.adapter_id}")
        await asyncio.sleep(5)  # Simulate training time
        
        # Update adapter status
        adapter.status = "active"
        adapter.validation_score = 0.85
        
        await self.store_lora_adapter(adapter)
        logger.info(f"Completed training for LoRA adapter {adapter.adapter_id}")


# Application instance
personalization_service = DoctorPersonalizationService()
app = personalization_service.app


@app.on_event("startup")
async def startup_event():
    await personalization_service.startup()


@app.on_event("shutdown")
async def shutdown_event():
    await personalization_service.shutdown()


def main():
    """Main entry point"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(
        "/app/logs/doctor-personalization.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format="{time:HH:mm:ss} | {level: <8} | {message}"
    )
    
    logger.info("Starting Doctor Personalization Service...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        log_level=log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()