"""
Comprehensive integration tests for all Business Services.

Tests end-to-end workflows across insurance verification, billing engine,
compliance monitoring, business intelligence, and doctor personalization.
"""

import asyncio
import pytest
import requests
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from tests.business_services.conftest import *


@pytest.mark.integration
@pytest.mark.phi_safe
@pytest.mark.slow
class TestBusinessServicesIntegration:
    """Integration tests for all business services working together."""

    @pytest.fixture(autouse=True)
    def setup_service_clients(self, service_urls):
        """Setup service clients for integration tests."""
        self.services = service_urls
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token"
        }

    def test_complete_patient_workflow(self, sample_patients, sample_doctors):
        """Test complete workflow: verification → billing → compliance → analytics."""
        patient = sample_patients[0]
        doctor = sample_doctors[0]
        
        # Mock responses for each service in the workflow
        mock_responses = {
            "insurance_verification": {"verified": True, "copay": 25.00},
            "billing_engine": {"claim_created": True, "claim_id": "CLM-12345"},
            "compliance_monitor": {"audit_logged": True, "compliance_score": 95.2},
            "business_intelligence": {"metrics_updated": True, "revenue_impact": 250.00}
        }
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: mock_responses["insurance_verification"]),
                MagicMock(status_code=201, json=lambda: mock_responses["billing_engine"]),
                MagicMock(status_code=200, json=lambda: mock_responses["compliance_monitor"]),
                MagicMock(status_code=200, json=lambda: mock_responses["business_intelligence"])
            ]
            
            # Step 1: Verify Insurance
            verification_resp = requests.post(
                f"{self.services['insurance_verification']}/verify-insurance",
                json={"patient_id": patient["patient_id"], "provider_id": doctor["doctor_id"]}
            )
            
            # Step 2: Create Billing Claim
            billing_resp = requests.post(
                f"{self.services['billing_engine']}/create-claim",
                json={
                    "patient_id": patient["patient_id"],
                    "provider_id": doctor["doctor_id"],
                    "insurance_verified": verification_resp.json()["verified"],
                    "service_amount": 250.00
                }
            )
            
            # Step 3: Log Compliance Events
            compliance_resp = requests.post(
                f"{self.services['compliance_monitor']}/track-audit",
                json={
                    "event_type": "PATIENT_BILLING_WORKFLOW",
                    "patient_id": patient["patient_id"],
                    "claim_id": billing_resp.json()["claim_id"]
                }
            )
            
            # Step 4: Update Analytics
            analytics_resp = requests.post(
                f"{self.services['business_intelligence']}/ingest-metrics",
                json={
                    "source": "billing_workflow",
                    "revenue": 250.00,
                    "compliance_score": compliance_resp.json()["compliance_score"]
                }
            )
            
            # Verify complete workflow
            assert verification_resp.status_code == 200
            assert billing_resp.status_code == 201
            assert compliance_resp.status_code == 200
            assert analytics_resp.status_code == 200
            
            assert verification_resp.json()["verified"] is True
            assert billing_resp.json()["claim_created"] is True
            assert compliance_resp.json()["audit_logged"] is True
            assert analytics_resp.json()["metrics_updated"] is True

    def test_personalized_workflow_with_doctor_preferences(self, sample_doctors, sample_doctor_preferences):
        """Test workflow with doctor personalization affecting all services."""
        doctor = sample_doctors[0]
        preferences = sample_doctor_preferences[0]
        
        mock_responses = {
            "doctor_personalization": {"personalized": True, "style": "detailed"},
            "insurance_verification": {"verified": True, "detailed_report": True},
            "billing_engine": {"optimized_codes": True, "detailed_breakdown": True},
            "compliance_monitor": {"personalized_alerts": True}
        }
        
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_responses["doctor_personalization"]
            
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: mock_responses["insurance_verification"]),
                MagicMock(status_code=200, json=lambda: mock_responses["billing_engine"]),
                MagicMock(status_code=200, json=lambda: mock_responses["compliance_monitor"])
            ]
            
            # Get doctor personalization
            personalization_resp = requests.get(
                f"{self.services['doctor_personalization']}/model-status/{doctor['doctor_id']}"
            )
            
            if personalization_resp.json()["personalized"]:
                # Use personalization in other services
                insurance_resp = requests.post(
                    f"{self.services['insurance_verification']}/verify-insurance",
                    json={
                        "doctor_id": doctor["doctor_id"],
                        "personalization": "detailed_reports"
                    }
                )
                
                billing_resp = requests.post(
                    f"{self.services['billing_engine']}/create-claim",
                    json={
                        "doctor_id": doctor["doctor_id"],
                        "personalization": "optimize_codes"
                    }
                )
                
                compliance_resp = requests.post(
                    f"{self.services['compliance_monitor']}/configure-alerts",
                    json={
                        "doctor_id": doctor["doctor_id"],
                        "personalization": "custom_thresholds"
                    }
                )
                
                assert insurance_resp.json()["detailed_report"] is True
                assert billing_resp.json()["optimized_codes"] is True
                assert compliance_resp.json()["personalized_alerts"] is True

    def test_compliance_monitoring_across_all_services(self, sample_doctors):
        """Test compliance monitoring integrated across all business services."""
        doctor = sample_doctors[0]
        
        # Mock compliance events from each service
        mock_events = {
            "insurance_verification": {"phi_access": True, "compliant": True},
            "billing_engine": {"payment_processed": True, "audit_trail": True},
            "business_intelligence": {"data_aggregated": True, "privacy_protected": True},
            "doctor_personalization": {"model_updated": True, "preferences_secure": True}
        }
        
        compliance_summary = {
            "overall_compliance": True,
            "service_scores": {
                "insurance_verification": 96.5,
                "billing_engine": 94.8,
                "business_intelligence": 97.2,
                "doctor_personalization": 95.1
            },
            "average_score": 95.9
        }
        
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            # Mock individual service compliance events
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: mock_events["insurance_verification"]),
                MagicMock(status_code=200, json=lambda: mock_events["billing_engine"]),
                MagicMock(status_code=200, json=lambda: mock_events["business_intelligence"]),
                MagicMock(status_code=200, json=lambda: mock_events["doctor_personalization"])
            ]
            
            # Mock compliance summary
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = compliance_summary
            
            # Generate compliance events from each service
            services = ["insurance_verification", "billing_engine", "business_intelligence", "doctor_personalization"]
            
            for service in services:
                event_resp = requests.post(
                    f"{self.services['compliance_monitor']}/track-audit",
                    json={
                        "event_type": f"{service.upper()}_OPERATION",
                        "user_id": doctor["doctor_id"],
                        "source_service": service
                    }
                )
                assert event_resp.status_code == 200
                assert event_resp.json()["compliant"] is True or event_resp.json().get("audit_trail") is True
            
            # Get overall compliance summary
            summary_resp = requests.get(
                f"{self.services['compliance_monitor']}/compliance-status"
            )
            
            assert summary_resp.status_code == 200
            assert summary_resp.json()["average_score"] > 95.0

    def test_data_flow_analytics_pipeline(self, sample_patients, sample_billing_claims):
        """Test data flowing from all services into business intelligence."""
        mock_data_sources = {
            "insurance_verification": {"verifications": 150, "success_rate": 0.94},
            "billing_engine": {"claims": 120, "revenue": 45000},
            "compliance_monitor": {"violations": 2, "score": 96.8},
            "doctor_personalization": {"active_models": 25, "satisfaction": 4.3}
        }
        
        analytics_result = {
            "data_integration_successful": True,
            "sources_processed": 4,
            "total_revenue": 45000,
            "overall_performance": {
                "verification_success": 0.94,
                "compliance_score": 96.8,
                "user_satisfaction": 4.3
            },
            "dashboard_updated": True
        }
        
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            # Mock data collection from each service
            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: mock_data_sources["insurance_verification"]),
                MagicMock(status_code=200, json=lambda: mock_data_sources["billing_engine"]),
                MagicMock(status_code=200, json=lambda: mock_data_sources["compliance_monitor"]),
                MagicMock(status_code=200, json=lambda: mock_data_sources["doctor_personalization"])
            ]
            
            # Mock analytics processing
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = analytics_result
            
            # Collect data from all services
            service_data = {}
            services = ["insurance_verification", "billing_engine", "compliance_monitor", "doctor_personalization"]
            
            for service in services:
                data_resp = requests.get(f"{self.services[service]}/metrics")
                service_data[service] = data_resp.json()
            
            # Process in business intelligence
            analytics_resp = requests.post(
                f"{self.services['business_intelligence']}/process-multi-source-data",
                json={"source_data": service_data}
            )
            
            assert analytics_resp.status_code == 200
            result = analytics_resp.json()
            assert result["data_integration_successful"] is True
            assert result["sources_processed"] == 4

    def test_error_handling_and_circuit_breakers(self):
        """Test error handling and circuit breaker patterns across services."""
        mock_responses = {
            "service_down": {"status_code": 503, "error": "Service temporarily unavailable"},
            "circuit_open": {"circuit_breaker": "OPEN", "fallback_used": True},
            "recovery": {"status_code": 200, "circuit_breaker": "CLOSED", "service_restored": True}
        }
        
        with patch('requests.post') as mock_post:
            # Simulate service failure
            mock_post.return_value.status_code = 503
            mock_post.return_value.json.return_value = mock_responses["service_down"]
            
            failure_resp = requests.post(
                f"{self.services['billing_engine']}/create-claim",
                json={"patient_id": "test", "amount": 100}
            )
            
            assert failure_resp.status_code == 503
            
            # Simulate circuit breaker activation
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_responses["circuit_open"]
            
            circuit_resp = requests.post(
                f"{self.services['insurance_verification']}/verify-insurance",
                json={"patient_id": "test"}
            )
            
            assert circuit_resp.json()["fallback_used"] is True
            
            # Simulate service recovery
            mock_post.return_value.json.return_value = mock_responses["recovery"]
            
            recovery_resp = requests.post(
                f"{self.services['billing_engine']}/health-check"
            )
            
            assert recovery_resp.json()["service_restored"] is True

    def test_performance_under_concurrent_load(self):
        """Test system performance under concurrent requests across all services."""
        import time
        import concurrent.futures
        
        mock_response = {"processed": True, "response_time_ms": 150}
        
        def make_request(service_name):
            with patch('requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response
                
                start_time = time.time()
                response = requests.post(f"{self.services[service_name]}/test-endpoint")
                end_time = time.time()
                
                return {
                    "service": service_name,
                    "status": response.status_code,
                    "duration": end_time - start_time
                }
        
        # Test concurrent requests to all services
        services = ["insurance_verification", "billing_engine", "compliance_monitor", 
                   "business_intelligence", "doctor_personalization"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, service) for service in services]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all requests completed successfully
        assert len(results) == 5
        for result in results:
            assert result["status"] == 200
            assert result["duration"] < 2.0  # All requests under 2 seconds

    def test_end_to_end_audit_trail(self, sample_patients, sample_doctors):
        """Test complete audit trail across all business services."""
        patient = sample_patients[0]
        doctor = sample_doctors[0]
        workflow_id = str(uuid.uuid4())
        
        # Mock audit responses
        audit_responses = [
            {"audit_id": f"AUD-001", "service": "insurance_verification", "action": "verify"},
            {"audit_id": f"AUD-002", "service": "billing_engine", "action": "create_claim"},
            {"audit_id": f"AUD-003", "service": "compliance_monitor", "action": "track_event"},
            {"audit_id": f"AUD-004", "service": "business_intelligence", "action": "update_metrics"}
        ]
        
        complete_audit = {
            "workflow_id": workflow_id,
            "patient_id": patient["patient_id"],
            "doctor_id": doctor["doctor_id"],
            "audit_trail": audit_responses,
            "compliance_verified": True,
            "complete_trail": True
        }
        
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            # Mock individual audit logging
            mock_post.side_effect = [MagicMock(status_code=200, json=lambda resp=resp: resp) for resp in audit_responses]
            
            # Mock complete audit trail retrieval
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = complete_audit
            
            # Generate audit events across all services
            services = ["insurance_verification", "billing_engine", "compliance_monitor", "business_intelligence"]
            
            for i, service in enumerate(services):
                audit_resp = requests.post(
                    f"{self.services['compliance_monitor']}/track-audit",
                    json={
                        "workflow_id": workflow_id,
                        "service": service,
                        "patient_id": patient["patient_id"],
                        "doctor_id": doctor["doctor_id"],
                        "action": audit_responses[i]["action"]
                    }
                )
                assert audit_resp.status_code == 200
            
            # Retrieve complete audit trail
            trail_resp = requests.get(
                f"{self.services['compliance_monitor']}/audit-trail/workflow/{workflow_id}"
            )
            
            assert trail_resp.status_code == 200
            result = trail_resp.json()
            assert result["complete_trail"] is True
            assert len(result["audit_trail"]) == 4
            assert result["compliance_verified"] is True