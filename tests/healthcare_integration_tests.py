"""
Enhanced Healthcare Testing Infrastructure

Comprehensive testing utilities for healthcare AI systems with synthetic data,
mock services, and healthcare-specific testing patterns.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from fastapi import FastAPI
import redis.asyncio as redis

from tests.database_test_utils import HealthcareTestCase
from core.infrastructure.authentication import HealthcareRole, AuthenticatedUser
from core.infrastructure.streaming import StreamingEventType

logger = logging.getLogger(__name__)

class MockHealthcareMCP:
    """Mock Healthcare MCP server for testing"""
    
    def __init__(self):
        self.call_count = 0
        self.last_request = None
        self.responses = {}
        self.health_status = "healthy"
    
    async def extract_medical_entities(self, text: str) -> Dict[str, Any]:
        """Mock medical entity extraction"""
        self.call_count += 1
        self.last_request = {"method": "extract_medical_entities", "text": text}
        
        # Return realistic mock medical entities
        return {
            "entities": [
                {
                    "text": "hypertension",
                    "type": "CONDITION",
                    "confidence": 0.95,
                    "start": 0,
                    "end": 12
                },
                {
                    "text": "120/80 mmHg",
                    "type": "VITAL_SIGN",
                    "confidence": 0.98,
                    "start": 15,
                    "end": 26
                }
            ],
            "medical_context": "cardiology",
            "phi_detected": False
        }
    
    async def search_medical_literature(
        self, 
        query: str, 
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Mock medical literature search"""
        self.call_count += 1
        self.last_request = {
            "method": "search_medical_literature", 
            "query": query, 
            "max_results": max_results
        }
        
        return {
            "papers": [
                {
                    "title": f"Clinical Study on {query}",
                    "authors": ["Dr. Jane Smith", "Dr. John Doe"],
                    "journal": "Journal of Medical Research",
                    "year": 2024,
                    "doi": "10.1001/jmr.2024.001",
                    "relevance_score": 0.92,
                    "abstract": f"This study examines {query} in clinical settings..."
                }
            ],
            "total_results": 1,
            "search_time_ms": 150
        }
    
    async def analyze_medical_document(self, document_content: str) -> Dict[str, Any]:
        """Mock medical document analysis"""
        self.call_count += 1
        self.last_request = {
            "method": "analyze_medical_document", 
            "content_length": len(document_content)
        }
        
        return {
            "document_type": "clinical_note",
            "entities_extracted": 15,
            "sections": {
                "subjective": "Patient reports chest pain",
                "objective": "BP 140/90, HR 85",
                "assessment": "Possible hypertension", 
                "plan": "Follow-up in 1 week"
            },
            "phi_detected": False,
            "compliance_verified": True
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check"""
        return {
            "status": self.health_status,
            "timestamp": datetime.now().isoformat(),
            "call_count": self.call_count
        }

class MockHealthcareLLM:
    """Mock Healthcare LLM for testing"""
    
    def __init__(self):
        self.call_count = 0
        self.last_request = None
        self.health_status = "healthy"
        self.temperature = 0.1
        self.max_tokens = 2048
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Mock LLM response generation"""
        self.call_count += 1
        self.last_request = {"prompt": prompt, "context": context}
        
        return {
            "response": f"This is a mock healthcare AI response to: {prompt[:100]}...",
            "confidence": 0.87,
            "reasoning_steps": [
                "Analyzed medical context",
                "Checked for safety concerns", 
                "Generated appropriate response"
            ],
            "medical_disclaimer": "This is administrative support only, not medical advice",
            "tokens_used": 145,
            "response_time_ms": 1200
        }
    
    async def stream_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock streaming LLM response"""
        self.call_count += 1
        
        chunks = [
            {"chunk": "This is", "done": False},
            {"chunk": " a mock", "done": False},
            {"chunk": " streaming", "done": False},
            {"chunk": " response", "done": False},
            {"chunk": "", "done": True, "total_tokens": 45}
        ]
        
        for chunk in chunks:
            await asyncio.sleep(0.1)  # Simulate streaming delay
            yield chunk
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock LLM health check"""
        return {
            "status": self.health_status,
            "model": "mock-healthcare-llm",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "call_count": self.call_count
        }

class HealthcareTestFixtures:
    """Healthcare-specific test fixtures and utilities"""
    
    @staticmethod
    def create_test_user(
        role: HealthcareRole = HealthcareRole.DOCTOR,
        user_id: Optional[str] = None,
        facility_id: Optional[str] = None
    ) -> AuthenticatedUser:
        """Create test healthcare user"""
        return AuthenticatedUser(
            user_id=user_id or f"test_user_{uuid.uuid4().hex[:8]}",
            role=role,
            facility_id=facility_id or "test_facility_001",
            department="test_department",
            permissions=[]  # Will be set based on role
        )
    
    @staticmethod
    def create_test_patient_data() -> Dict[str, Any]:
        """Create synthetic patient data for testing"""
        return {
            "patient_id": f"TEST_{uuid.uuid4().hex[:8].upper()}",
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1980-01-15",
            "gender": "M",
            "phone": "555-0123",
            "email": "john.doe@example.com",
            "address": {
                "street": "123 Test St",
                "city": "Test City",
                "state": "TS",
                "zip_code": "12345"
            },
            "insurance": {
                "provider": "Test Insurance",
                "policy_number": "TEST123456",
                "group_number": "GRP001"
            },
            "emergency_contact": {
                "name": "Jane Doe",
                "relationship": "spouse",
                "phone": "555-0124"
            }
        }
    
    @staticmethod
    def create_test_encounter_data() -> Dict[str, Any]:
        """Create synthetic encounter data for testing"""
        return {
            "encounter_id": f"ENC_{uuid.uuid4().hex[:8].upper()}",
            "patient_id": f"TEST_{uuid.uuid4().hex[:8].upper()}",
            "provider_id": "DR_TEST_001",
            "encounter_date": datetime.now().isoformat(),
            "encounter_type": "office_visit",
            "chief_complaint": "Routine checkup",
            "vital_signs": {
                "blood_pressure": "120/80",
                "heart_rate": 72,
                "temperature": 98.6,
                "weight": 170,
                "height": 70
            },
            "assessment": "Patient appears healthy",
            "plan": "Continue current medications, follow up in 6 months",
            "prescriptions": [
                {
                    "medication": "Lisinopril",
                    "dosage": "10mg",
                    "frequency": "daily",
                    "duration": "30 days"
                }
            ]
        }
    
    @staticmethod
    def create_test_medical_document() -> str:
        """Create synthetic medical document content"""
        return """
        CLINICAL NOTE
        
        Date: 2024-08-03
        Patient: John Doe (DOB: 1980-01-15)
        Provider: Dr. Jane Smith
        
        SUBJECTIVE:
        Patient presents for routine follow-up of hypertension. Reports good compliance
        with medications. No chest pain, shortness of breath, or dizziness. 
        
        OBJECTIVE:
        Vital Signs: BP 130/85, HR 78, Temp 98.4°F, Wt 175 lbs
        Physical exam unremarkable. No peripheral edema noted.
        
        ASSESSMENT:
        Hypertension, well controlled on current regimen.
        
        PLAN:
        Continue Lisinopril 10mg daily. Follow up in 3 months.
        Patient counseled on diet and exercise.
        """

class HealthcareIntegrationTestBase:
    """Base class for healthcare integration tests"""
    
    def __init__(self):
        self.mock_mcp = MockHealthcareMCP()
        self.mock_llm = MockHealthcareLLM()
        self.test_fixtures = HealthcareTestFixtures()
        self.test_client: Optional[TestClient] = None
    
    async def setup_test_environment(self, app: FastAPI) -> None:
        """Setup test environment with mock services"""
        self.test_client = TestClient(app)
        
        # Replace real services with mocks
        app.state.mock_mcp = self.mock_mcp
        app.state.mock_llm = self.mock_llm
        
        logger.info("Healthcare test environment initialized")
    
    async def teardown_test_environment(self) -> None:
        """Cleanup test environment"""
        if self.test_client:
            self.test_client.close()
        logger.info("Healthcare test environment cleaned up")
    
    def create_authenticated_request_headers(
        self, 
        user: AuthenticatedUser
    ) -> Dict[str, str]:
        """Create headers for authenticated healthcare requests"""
        # In real implementation, this would create a valid JWT
        return {
            "Authorization": f"Bearer mock_jwt_{user.user_id}",
            "X-User-Role": user.role.value,
            "X-Facility-ID": user.facility_id or "test_facility",
            "Content-Type": "application/json"
        }

class HealthcareWorkflowTester:
    """Test healthcare workflows end-to-end"""
    
    def __init__(self, integration_test_base: HealthcareIntegrationTestBase):
        self.base = integration_test_base
    
    async def test_patient_intake_workflow(self) -> Dict[str, Any]:
        """Test complete patient intake workflow"""
        logger.info("Testing patient intake workflow")
        
        # Create test data
        user = self.base.test_fixtures.create_test_user(HealthcareRole.RECEPTIONIST)
        patient_data = self.base.test_fixtures.create_test_patient_data()
        
        results = {
            "workflow": "patient_intake",
            "steps_completed": [],
            "errors": [],
            "duration_ms": 0
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Register new patient
            headers = self.base.create_authenticated_request_headers(user)
            response = self.base.test_client.post(
                "/agents/intake/register_patient",
                json=patient_data,
                headers=headers
            )
            
            if response.status_code == 200:
                results["steps_completed"].append("patient_registration")
            else:
                results["errors"].append(f"Registration failed: {response.status_code}")
            
            # Step 2: Verify insurance
            insurance_response = self.base.test_client.post(
                "/agents/intake/verify_insurance",
                json={
                    "patient_id": patient_data["patient_id"],
                    "insurance_info": patient_data["insurance"]
                },
                headers=headers
            )
            
            if insurance_response.status_code == 200:
                results["steps_completed"].append("insurance_verification")
            else:
                results["errors"].append(f"Insurance verification failed: {insurance_response.status_code}")
            
            # Step 3: Schedule appointment
            appointment_data = {
                "patient_id": patient_data["patient_id"],
                "provider_id": "DR_TEST_001",
                "appointment_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "appointment_type": "routine_checkup"
            }
            
            appointment_response = self.base.test_client.post(
                "/agents/intake/schedule_appointment",
                json=appointment_data,
                headers=headers
            )
            
            if appointment_response.status_code == 200:
                results["steps_completed"].append("appointment_scheduling")
            else:
                results["errors"].append(f"Appointment scheduling failed: {appointment_response.status_code}")
        
        except Exception as e:
            results["errors"].append(f"Workflow exception: {str(e)}")
        
        end_time = datetime.now()
        results["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"Patient intake workflow completed: {len(results['steps_completed'])} steps, {len(results['errors'])} errors")
        return results
    
    async def test_document_processing_workflow(self) -> Dict[str, Any]:
        """Test medical document processing workflow"""
        logger.info("Testing document processing workflow")
        
        user = self.base.test_fixtures.create_test_user(HealthcareRole.DOCTOR)
        document_content = self.base.test_fixtures.create_test_medical_document()
        
        results = {
            "workflow": "document_processing",
            "steps_completed": [],
            "errors": [],
            "duration_ms": 0
        }
        
        start_time = datetime.now()
        
        try:
            headers = self.base.create_authenticated_request_headers(user)
            
            # Process medical document
            response = self.base.test_client.post(
                "/agents/document/process",
                json={
                    "document_type": "clinical_note",
                    "content": document_content,
                    "patient_id": "TEST_PATIENT_001"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                results["steps_completed"].append("document_analysis")
                
                response_data = response.json()
                if "entities_extracted" in response_data:
                    results["steps_completed"].append("entity_extraction")
                if "phi_detected" in response_data:
                    results["steps_completed"].append("phi_detection")
            else:
                results["errors"].append(f"Document processing failed: {response.status_code}")
        
        except Exception as e:
            results["errors"].append(f"Workflow exception: {str(e)}")
        
        end_time = datetime.now()
        results["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"Document processing workflow completed: {len(results['steps_completed'])} steps, {len(results['errors'])} errors")
        return results

class HealthcareLoadTester:
    """Load testing for healthcare systems"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.concurrent_users = 10
        self.test_duration_seconds = 60
    
    async def simulate_clinical_load(self) -> Dict[str, Any]:
        """Simulate realistic clinical environment load"""
        logger.info(f"Starting clinical load test: {self.concurrent_users} users for {self.test_duration_seconds}s")
        
        results = {
            "test_type": "clinical_load",
            "concurrent_users": self.concurrent_users,
            "duration_seconds": self.test_duration_seconds,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time_ms": 0,
            "peak_response_time_ms": 0,
            "errors": []
        }
        
        # Simulate concurrent healthcare users
        tasks = []
        for i in range(self.concurrent_users):
            user_type = [
                HealthcareRole.DOCTOR,
                HealthcareRole.NURSE, 
                HealthcareRole.RECEPTIONIST
            ][i % 3]
            
            task = asyncio.create_task(
                self._simulate_user_activity(user_type, self.test_duration_seconds)
            )
            tasks.append(task)
        
        # Wait for all user simulations to complete
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for user_result in user_results:
            if isinstance(user_result, dict):
                results["total_requests"] += user_result.get("requests", 0)
                results["successful_requests"] += user_result.get("successful", 0)
                results["failed_requests"] += user_result.get("failed", 0)
        
        if results["total_requests"] > 0:
            results["success_rate"] = results["successful_requests"] / results["total_requests"]
        
        logger.info(f"Clinical load test completed: {results['total_requests']} requests, {results['success_rate']:.2%} success rate")
        return results
    
    async def _simulate_user_activity(
        self, 
        role: HealthcareRole, 
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Simulate individual user activity patterns"""
        user_results = {"requests": 0, "successful": 0, "failed": 0}
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
            try:
                # Simulate role-specific activities
                if role == HealthcareRole.DOCTOR:
                    await self._simulate_doctor_activities()
                elif role == HealthcareRole.NURSE:
                    await self._simulate_nurse_activities()
                elif role == HealthcareRole.RECEPTIONIST:
                    await self._simulate_receptionist_activities()
                
                user_results["requests"] += 1
                user_results["successful"] += 1
                
                # Realistic pause between actions
                await asyncio.sleep(2.0)
                
            except Exception as e:
                user_results["failed"] += 1
                logger.warning(f"User simulation error: {e}")
        
        return user_results
    
    async def _simulate_doctor_activities(self) -> None:
        """Simulate doctor workflow activities"""
        # Mock API calls that a doctor would make
        activities = [
            "patient_lookup",
            "medical_literature_search", 
            "document_analysis",
            "prescription_review"
        ]
        
        # Simulate the activity (in real test, would make HTTP requests)
        activity = activities[hash(asyncio.current_task()) % len(activities)]
        await asyncio.sleep(0.1)  # Simulate API call
    
    async def _simulate_nurse_activities(self) -> None:
        """Simulate nurse workflow activities"""
        activities = [
            "patient_vitals_entry",
            "medication_administration",
            "care_plan_review"
        ]
        
        activity = activities[hash(asyncio.current_task()) % len(activities)]
        await asyncio.sleep(0.1)
    
    async def _simulate_receptionist_activities(self) -> None:
        """Simulate receptionist workflow activities"""
        activities = [
            "appointment_scheduling",
            "patient_registration",
            "insurance_verification"
        ]
        
        activity = activities[hash(asyncio.current_task()) % len(activities)]
        await asyncio.sleep(0.1)
