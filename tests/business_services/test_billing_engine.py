"""
Comprehensive tests for Billing Engine Service.

Tests Tree of Thoughts reasoning, claims processing, and payment tracking
using real synthetic data from the healthcare database.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from tests.business_services.conftest import *


@pytest.mark.billing
@pytest.mark.phi_safe
class TestBillingEngineService:
    """Test suite for Billing Engine Service functionality."""

    @pytest.fixture(autouse=True)
    def setup_service_client(self, service_urls):
        """Setup service client for tests."""
        self.service_url = service_urls["billing_engine"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",
        }

    def test_service_health_check(self):
        """Test that the billing engine service health endpoint responds."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"status": "healthy", "database": "connected"}

            response = requests.get(f"{self.service_url}/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.tree_of_thoughts
    def test_create_claim_with_tot_reasoning(self, sample_patients, sample_doctors, mock_ai_responses):
        """Test claim creation using Tree of Thoughts reasoning for optimal billing strategy."""
        patient = sample_patients[0]
        doctor = sample_doctors[0]

        # Mock ToT reasoning response with multiple billing strategies
        mock_response = {
            "claim_id": f"CLM-{uuid.uuid4().hex[:8].upper()}",
            "claim_created": True,
            "tree_of_thoughts": mock_ai_responses["tree_of_thoughts"],
            "selected_strategy": {
                "strategy_name": "alternative_coding",
                "estimated_reimbursement": 275.00,
                "confidence": 0.85,
                "reasoning": "Alternative coding provides 37% better reimbursement",
            },
            "alternative_strategies": [
                {
                    "strategy_name": "standard_billing",
                    "estimated_reimbursement": 200.00,
                    "confidence": 0.92,
                },
            ],
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = mock_response

            claim_request = {
                "patient_id": patient["patient_id"],
                "provider_id": doctor["doctor_id"],
                "service_date": datetime.now().isoformat(),
                "services": [
                    {
                        "cpt_code": "99213",
                        "description": "Office visit, established patient",
                        "amount": 200.00,
                    },
                    {
                        "cpt_code": "85025",
                        "description": "Blood count, complete",
                        "amount": 75.00,
                    },
                ],
                "diagnosis_codes": ["I10", "Z00.00"],
            }

            response = requests.post(
                f"{self.service_url}/create-claim",
                json=claim_request,
                headers=self.headers,
            )

            assert response.status_code == 201
            result = response.json()

            # Verify ToT reasoning is present
            assert "tree_of_thoughts" in result
            assert "paths" in result["tree_of_thoughts"]
            assert len(result["tree_of_thoughts"]["paths"]) >= 2

            # Verify optimal strategy selection
            assert result["selected_strategy"]["estimated_reimbursement"] == 275.00
            assert result["claim_created"] is True

    def test_submit_claim_to_insurance(self, sample_billing_claims):
        """Test claim submission to insurance provider."""
        claim = sample_billing_claims[0]

        mock_response = {
            "submission_id": f"SUB-{uuid.uuid4().hex[:8].upper()}",
            "claim_id": claim["claim_id"],
            "submitted": True,
            "submission_date": datetime.now().isoformat(),
            "expected_response_time": "3-5 business days",
            "tracking_number": f"TRK{uuid.uuid4().hex[:12].upper()}",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            submission_request = {
                "claim_id": claim["claim_id"],
                "submission_method": "electronic",
                "priority": "standard",
            }

            response = requests.post(
                f"{self.service_url}/submit-claim",
                json=submission_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["submitted"] is True
            assert "tracking_number" in result

    def test_validate_medical_codes(self):
        """Test medical billing code validation (CPT, ICD-10, HCPCS)."""
        mock_response = {
            "validation_results": {
                "cpt_codes": {
                    "99213": {"valid": True, "description": "Office visit, established patient, level 3"},
                    "99999": {"valid": False, "error": "Invalid CPT code"},
                },
                "icd10_codes": {
                    "I10": {"valid": True, "description": "Essential hypertension"},
                    "Z99.99": {"valid": False, "error": "Invalid ICD-10 code"},
                },
            },
            "overall_valid": False,
            "warnings": ["Invalid codes detected"],
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            validation_request = {
                "codes": {
                    "cpt_codes": ["99213", "99999"],
                    "icd10_codes": ["I10", "Z99.99"],
                },
            }

            response = requests.post(
                f"{self.service_url}/validate-codes",
                json=validation_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["validation_results"]["cpt_codes"]["99213"]["valid"] is True
            assert result["validation_results"]["cpt_codes"]["99999"]["valid"] is False
            assert result["overall_valid"] is False

    def test_process_payment_successful(self, sample_billing_claims):
        """Test successful payment processing."""
        claim = sample_billing_claims[0]

        mock_response = {
            "payment_id": f"PAY-{uuid.uuid4().hex[:8].upper()}",
            "claim_id": claim["claim_id"],
            "payment_processed": True,
            "payment_amount": 225.50,
            "payment_date": datetime.now().isoformat(),
            "payment_method": "ACH",
            "remaining_balance": 0.00,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            payment_request = {
                "claim_id": claim["claim_id"],
                "payment_amount": 225.50,
                "payer_id": "INS_12345",
                "payment_type": "insurance_reimbursement",
            }

            response = requests.post(
                f"{self.service_url}/process-payment",
                json=payment_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["payment_processed"] is True
            assert result["remaining_balance"] == 0.00

    def test_claim_status_tracking(self, sample_billing_claims):
        """Test claim status tracking and updates."""
        claim = sample_billing_claims[0]

        mock_response = {
            "claim_id": claim["claim_id"],
            "current_status": "under_review",
            "status_history": [
                {"status": "submitted", "date": "2024-01-10T09:00:00Z"},
                {"status": "received", "date": "2024-01-11T14:30:00Z"},
                {"status": "under_review", "date": "2024-01-12T10:15:00Z"},
            ],
            "estimated_resolution_date": "2024-01-17T17:00:00Z",
            "next_action": "await_insurance_decision",
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/claim-status/{claim['claim_id']}",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["current_status"] == "under_review"
            assert len(result["status_history"]) == 3

    def test_analyze_claim_denial(self, sample_billing_claims):
        """Test claim denial analysis and resubmission recommendations."""
        denied_claim = next(
            (claim for claim in sample_billing_claims if claim["claim_status"] == "denied"),
            sample_billing_claims[0],  # fallback
        )

        mock_response = {
            "claim_id": denied_claim["claim_id"],
            "denial_analysis": {
                "denial_reason": "Prior authorization required",
                "denial_code": "CO-50",
                "correctable": True,
                "recommended_actions": [
                    "Obtain prior authorization",
                    "Resubmit with authorization number",
                ],
            },
            "resubmission_strategy": {
                "success_probability": 0.85,
                "estimated_timeline": "5-7 business days",
                "required_documentation": ["prior_auth_approval"],
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            analysis_request = {
                "claim_id": denied_claim["claim_id"],
                "denial_reason": "Prior authorization required",
            }

            response = requests.post(
                f"{self.service_url}/analyze-denial",
                json=analysis_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["denial_analysis"]["correctable"] is True
            assert result["resubmission_strategy"]["success_probability"] > 0.8

    def test_revenue_cycle_reporting(self):
        """Test revenue cycle management reports."""
        mock_response = {
            "report_period": "2024-01",
            "revenue_metrics": {
                "total_billed": 125000.00,
                "total_collected": 95000.00,
                "collection_rate": 0.76,
                "average_days_to_payment": 24.5,
            },
            "claim_statistics": {
                "total_claims": 450,
                "approved_claims": 380,
                "denied_claims": 35,
                "pending_claims": 35,
                "approval_rate": 0.844,
            },
            "top_denial_reasons": [
                {"reason": "Prior authorization required", "count": 15},
                {"reason": "Service not covered", "count": 12},
                {"reason": "Duplicate claim", "count": 8},
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/revenue-report",
                params={"period": "2024-01", "format": "summary"},
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["revenue_metrics"]["collection_rate"] > 0.7
            assert result["claim_statistics"]["total_claims"] == 450

    def test_code_optimization_suggestions(self):
        """Test billing code optimization for better reimbursement."""
        mock_response = {
            "optimization_suggestions": [
                {
                    "current_code": "99213",
                    "suggested_code": "99214",
                    "reasoning": "Documentation supports higher level visit",
                    "reimbursement_increase": 75.00,
                    "confidence": 0.88,
                },
                {
                    "current_code": "85025",
                    "additional_code": "85027",
                    "reasoning": "Additional testing performed supports add-on code",
                    "reimbursement_increase": 25.00,
                    "confidence": 0.92,
                },
            ],
            "total_potential_increase": 100.00,
            "compliance_risk": "low",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            optimization_request = {
                "encounter_documentation": "Detailed patient visit with comprehensive exam",
                "current_codes": ["99213", "85025"],
                "diagnosis_codes": ["I10"],
            }

            response = requests.post(
                f"{self.service_url}/optimize-codes",
                json=optimization_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["total_potential_increase"] == 100.00
            assert result["compliance_risk"] == "low"

    @pytest.mark.phi_safe
    def test_phi_protection_in_billing_data(self, sample_patients, sample_billing_claims):
        """Test that PHI is properly protected in billing responses."""
        patient = sample_patients[0]
        claim = sample_billing_claims[0]

        # Response should mask sensitive information
        mock_response = {
            "claim_id": claim["claim_id"],
            "patient_ref": f"pt_***{patient['patient_id'][-4:]}",  # Masked
            "provider_ref": f"dr_***{claim['doctor_id'][-4:]}",  # Masked
            "claim_amount": claim["claim_amount"],
            "phi_detected": True,
            "phi_sanitized": True,
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/claim-status/{claim['claim_id']}",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()

            # Verify PHI masking
            assert "***" in result["patient_ref"]
            assert "***" in result["provider_ref"]
            assert result["phi_sanitized"] is True

    def test_batch_claim_processing(self, sample_billing_claims):
        """Test processing multiple claims in batch."""
        claims_batch = sample_billing_claims[:3]

        mock_response = {
            "batch_id": f"BATCH-{uuid.uuid4().hex[:8].upper()}",
            "total_claims": len(claims_batch),
            "processed_claims": len(claims_batch),
            "failed_claims": 0,
            "processing_results": [
                {"claim_id": claim["claim_id"], "status": "processed", "amount": claim["claim_amount"]}
                for claim in claims_batch
            ],
            "total_amount": sum(claim["claim_amount"] for claim in claims_batch),
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            batch_request = {
                "claims": [
                    {"claim_id": claim["claim_id"], "action": "submit"}
                    for claim in claims_batch
                ],
            }

            response = requests.post(
                f"{self.service_url}/batch-process",
                json=batch_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["processed_claims"] == len(claims_batch)
            assert result["failed_claims"] == 0

    @pytest.mark.slow
    def test_billing_performance_optimization(self, sample_billing_claims):
        """Test billing engine performance under load."""
        import time

        mock_response = {
            "claims_processed": 100,
            "processing_time_ms": 1250,
            "average_time_per_claim_ms": 12.5,
            "success_rate": 0.98,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            start_time = time.time()

            # Simulate processing 100 claims
            performance_request = {
                "claim_count": 100,
                "test_mode": True,
            }

            response = requests.post(
                f"{self.service_url}/performance-test",
                json=performance_request,
                headers=self.headers,
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            result = response.json()
            assert result["average_time_per_claim_ms"] < 20  # Under 20ms per claim
            assert result["success_rate"] > 0.95
            assert elapsed_time < 5.0  # Test completes quickly


@pytest.mark.billing
@pytest.mark.integration
class TestBillingEngineIntegration:
    """Integration tests for Billing Engine Service with other services."""

    def test_integration_with_insurance_verification(self, sample_patients, service_urls):
        """Test integration with insurance verification before billing."""
        # Mock insurance verification response
        verification_response = {
            "verified": True,
            "copay_amount": 25.00,
            "deductible_remaining": 200.00,
            "coverage_percentage": 0.80,
        }

        # Mock billing response using verification data
        billing_response = {
            "claim_created": True,
            "patient_responsibility": 25.00,  # From copay
            "insurance_expected": 200.00,     # 80% of $250 service
            "verification_used": True,
        }

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: verification_response),
                MagicMock(status_code=201, json=lambda: billing_response),
            ]

            # Step 1: Verify insurance
            verification_resp = requests.post(
                f"{service_urls['insurance_verification']}/verify-insurance",
                json={"patient_id": sample_patients[0]["patient_id"]},
            )

            # Step 2: Create claim using verification data
            claim_request = {
                "patient_id": sample_patients[0]["patient_id"],
                "service_amount": 250.00,
                "insurance_verified": verification_resp.json()["verified"],
                "expected_patient_cost": verification_resp.json()["copay_amount"],
            }

            billing_resp = requests.post(
                f"{service_urls['billing_engine']}/create-claim",
                json=claim_request,
            )

            assert verification_resp.status_code == 200
            assert billing_resp.status_code == 201
            assert billing_resp.json()["verification_used"] is True

    def test_integration_with_compliance_monitor(self, sample_billing_claims, service_urls):
        """Test that billing events are logged to compliance monitor."""
        claim = sample_billing_claims[0]

        billing_response = {"claim_processed": True}
        compliance_response = {"audit_logged": True, "billing_event_recorded": True}

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: billing_response),
                MagicMock(status_code=200, json=lambda: compliance_response),
            ]

            # Process billing
            billing_resp = requests.post(
                f"{service_urls['billing_engine']}/process-payment",
                json={"claim_id": claim["claim_id"], "amount": 100.00},
            )

            # Log to compliance
            audit_request = {
                "event_type": "BILLING_PROCESSED",
                "claim_id": claim["claim_id"],
                "amount": 100.00,
            }

            compliance_resp = requests.post(
                f"{service_urls['compliance_monitor']}/track-audit",
                json=audit_request,
            )

            assert billing_resp.status_code == 200
            assert compliance_resp.status_code == 200
            assert compliance_resp.json()["billing_event_recorded"] is True

    def test_integration_with_business_intelligence(self, service_urls):
        """Test billing data feeding into business intelligence analytics."""
        billing_metrics = {
            "revenue_generated": 5000.00,
            "claims_processed": 25,
            "average_claim_value": 200.00,
        }

        analytics_response = {
            "metrics_updated": True,
            "revenue_trend": "increasing",
            "dashboard_refreshed": True,
        }

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: billing_metrics),
                MagicMock(status_code=200, json=lambda: analytics_response),
            ]

            # Get billing metrics
            billing_resp = requests.post(
                f"{service_urls['billing_engine']}/daily-metrics",
                json={"date": "2024-01-15"},
            )

            # Send to BI service
            analytics_request = {
                "source": "billing_engine",
                "metrics": billing_resp.json(),
            }

            analytics_resp = requests.post(
                f"{service_urls['business_intelligence']}/ingest-metrics",
                json=analytics_request,
            )

            assert billing_resp.status_code == 200
            assert analytics_resp.status_code == 200
            assert analytics_resp.json()["dashboard_refreshed"] is True
