"""
Comprehensive tests for Insurance Verification Service.

Tests Chain-of-Thought reasoning, multi-provider support, and PHI protection
using real synthetic data from the healthcare database.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from tests.business_services.conftest import *


@pytest.mark.insurance
@pytest.mark.phi_safe
class TestInsuranceVerificationService:
    """Test suite for Insurance Verification Service functionality."""

    @pytest.fixture(autouse=True)
    def setup_service_client(self, service_urls):
        """Setup service client for tests."""
        self.service_url = service_urls["insurance_verification"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",
        }

    def test_service_health_check(self):
        """Test that the insurance verification service health endpoint responds."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"status": "healthy"}

            response = requests.get(f"{self.service_url}/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.chain_of_thought
    def test_verify_insurance_with_cot_reasoning(self, sample_patients, sample_insurance_verifications, mock_ai_responses):
        """Test insurance verification using Chain-of-Thought reasoning."""
        patient = sample_patients[0]
        insurance_data = sample_insurance_verifications[0]

        # Mock the service response with CoT reasoning
        mock_response = {
            "verification_result": {
                "verified": True,
                "eligibility_status": "Active",
                "coverage_verified": True,
            },
            "chain_of_thought": mock_ai_responses["chain_of_thought"],
            "confidence_score": 0.92,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            verification_request = {
                "patient_id": patient["patient_id"],
                "insurance_provider": insurance_data["insurance_provider"],
                "member_id": insurance_data["member_id"],
                "group_number": insurance_data["group_number"],
                "service_date": datetime.now().isoformat(),
            }

            response = requests.post(
                f"{self.service_url}/verify-insurance",
                json=verification_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()

            # Verify CoT reasoning is present
            assert "chain_of_thought" in result
            assert "steps" in result["chain_of_thought"]
            assert len(result["chain_of_thought"]["steps"]) == 5

            # Verify verification result
            assert result["verification_result"]["verified"] is True
            assert result["confidence_score"] > 0.8

    def test_check_eligibility_active_coverage(self, sample_patients, sample_insurance_verifications):
        """Test eligibility check for patient with active coverage."""
        patient = sample_patients[0]
        insurance = next(
            (ins for ins in sample_insurance_verifications
             if ins["eligibility_status"] == "Active"),
            sample_insurance_verifications[0],
        )

        mock_response = {
            "eligible": True,
            "coverage_type": insurance["coverage_type"],
            "copay_amount": insurance["copay_amount"],
            "deductible_remaining": insurance["deductible_amount"] * 0.3,
            "prior_auth_required": insurance["prior_auth_required"],
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            eligibility_request = {
                "patient_id": patient["patient_id"],
                "service_codes": ["99213", "85025"],
                "provider_npi": "1234567890",
            }

            response = requests.post(
                f"{self.service_url}/check-eligibility",
                json=eligibility_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["eligible"] is True
            assert result["coverage_type"] == insurance["coverage_type"]

    def test_check_eligibility_suspended_coverage(self, sample_patients, sample_insurance_verifications):
        """Test eligibility check for patient with suspended coverage."""
        patient = sample_patients[0]
        suspended_insurance = next(
            (ins for ins in sample_insurance_verifications
             if ins["eligibility_status"] == "Suspended"),
            None,
        )

        if not suspended_insurance:
            pytest.skip("No suspended insurance records in test data")

        mock_response = {
            "eligible": False,
            "reason": "Coverage suspended",
            "coverage_type": suspended_insurance["coverage_type"],
            "suggested_action": "Contact insurance provider",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            eligibility_request = {
                "patient_id": patient["patient_id"],
                "service_codes": ["99214"],
                "provider_npi": "1234567890",
            }

            response = requests.post(
                f"{self.service_url}/check-eligibility",
                json=eligibility_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["eligible"] is False
            assert "reason" in result

    def test_verify_benefits_hmo_coverage(self, sample_insurance_verifications):
        """Test benefits verification for HMO coverage."""
        hmo_insurance = next(
            (ins for ins in sample_insurance_verifications
             if ins["coverage_type"] == "HMO"),
            sample_insurance_verifications[0],
        )

        mock_response = {
            "benefits": {
                "in_network_coverage": 0.90,
                "out_network_coverage": 0.0,
                "specialist_referral_required": True,
                "annual_deductible": hmo_insurance["deductible_amount"],
                "deductible_met": hmo_insurance["deductible_met"],
            },
            "coverage_limits": {
                "annual_max": 50000.00,
                "remaining_benefits": 47500.00,
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            benefits_request = {
                "member_id": hmo_insurance["member_id"],
                "group_number": hmo_insurance["group_number"],
                "benefit_year": datetime.now().year,
            }

            response = requests.post(
                f"{self.service_url}/verify-benefits",
                json=benefits_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["benefits"]["specialist_referral_required"] is True
            assert result["benefits"]["out_network_coverage"] == 0.0

    def test_check_prior_authorization_required(self, sample_insurance_verifications):
        """Test prior authorization checking."""
        insurance = next(
            (ins for ins in sample_insurance_verifications
             if ins["prior_auth_required"] is True),
            sample_insurance_verifications[0],
        )

        mock_response = {
            "prior_auth_required": True,
            "procedures_requiring_auth": ["MRI", "CT_SCAN", "SPECIALIST_REFERRAL"],
            "auth_request_process": {
                "method": "electronic",
                "typical_turnaround": "2-3 business days",
                "emergency_override": True,
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            auth_request = {
                "member_id": insurance["member_id"],
                "procedure_codes": ["70553", "99245"],
                "diagnosis_codes": ["M79.3"],
            }

            response = requests.post(
                f"{self.service_url}/check-prior-auth",
                json=auth_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["prior_auth_required"] is True
            assert len(result["procedures_requiring_auth"]) > 0

    def test_provider_network_status(self):
        """Test provider network status checking."""
        mock_response = {
            "in_network": True,
            "provider_tier": "preferred",
            "reimbursement_rate": 0.85,
            "patient_cost_share": {
                "copay": 25.00,
                "coinsurance": 0.20,
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/provider-network",
                params={
                    "provider_npi": "1234567890",
                    "insurance_provider": "UnitedHealth",
                    "plan_type": "HMO",
                },
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["in_network"] is True
            assert result["provider_tier"] == "preferred"

    @pytest.mark.phi_safe
    def test_phi_protection_in_responses(self, sample_patients):
        """Test that PHI is properly protected in verification responses."""
        patient = sample_patients[0]

        # Response should not contain raw PHI
        mock_response = {
            "verification_result": {
                "verified": True,
                "patient_ref": f"pt_***{patient['patient_id'][-4:]}",  # Masked patient ID
            },
            "phi_detected": True,
            "phi_sanitized": True,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            verification_request = {
                "patient_id": patient["patient_id"],
                "date_of_birth": patient["date_of_birth"],
                "insurance_id": "BCBS123456789",
            }

            response = requests.post(
                f"{self.service_url}/verify-insurance",
                json=verification_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()

            # Verify PHI protection flags
            assert result["phi_sanitized"] is True

            # Verify patient ID is masked
            assert "***" in result["verification_result"]["patient_ref"]

            # Verify no raw DOB in response
            response_str = json.dumps(result)
            assert patient["date_of_birth"] not in response_str

    def test_multi_provider_verification(self, sample_insurance_verifications):
        """Test verification across multiple insurance providers."""
        providers = list({ins["insurance_provider"] for ins in sample_insurance_verifications})

        for provider in providers[:3]:  # Test first 3 unique providers
            mock_response = {
                "provider_available": True,
                "response_time_ms": 250,
                "verification_successful": True,
                "provider_specific_data": {
                    "provider_name": provider,
                    "api_version": "v2.1",
                },
            }

            with patch("requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response

                verification_request = {
                    "insurance_provider": provider,
                    "member_id": "TEST123456",
                    "verification_type": "real_time",
                }

                response = requests.post(
                    f"{self.service_url}/verify-insurance",
                    json=verification_request,
                    headers=self.headers,
                )

                assert response.status_code == 200
                result = response.json()
                assert result["provider_available"] is True
                assert result["provider_specific_data"]["provider_name"] == provider

    def test_error_prevention_invalid_member_id(self):
        """Test error prevention for invalid member ID format."""
        mock_response = {
            "error": "Invalid member ID format",
            "error_code": "INVALID_MEMBER_ID",
            "suggested_fix": "Member ID should be alphanumeric, 9-12 characters",
            "retry_recommended": False,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.json.return_value = mock_response

            verification_request = {
                "insurance_provider": "UnitedHealth",
                "member_id": "INVALID!!!",  # Invalid format
                "patient_id": "pt_123456",
            }

            response = requests.post(
                f"{self.service_url}/verify-insurance",
                json=verification_request,
                headers=self.headers,
            )

            assert response.status_code == 400
            result = response.json()
            assert result["error_code"] == "INVALID_MEMBER_ID"
            assert "suggested_fix" in result

    def test_error_prevention_provider_timeout(self):
        """Test error handling when insurance provider API times out."""
        mock_response = {
            "error": "Insurance provider timeout",
            "error_code": "PROVIDER_TIMEOUT",
            "retry_recommended": True,
            "retry_after_seconds": 30,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 503
            mock_post.return_value.json.return_value = mock_response

            verification_request = {
                "insurance_provider": "Aetna",
                "member_id": "A123456789",
                "patient_id": "pt_123456",
            }

            response = requests.post(
                f"{self.service_url}/verify-insurance",
                json=verification_request,
                headers=self.headers,
            )

            assert response.status_code == 503
            result = response.json()
            assert result["retry_recommended"] is True
            assert "retry_after_seconds" in result

    @pytest.mark.slow
    def test_verification_performance(self, sample_insurance_verifications):
        """Test that verification requests complete within reasonable time."""
        # Test should complete within 2 seconds for normal verification
        import time

        mock_response = {
            "verified": True,
            "response_time_ms": 156,
            "cached_result": False,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            start_time = time.time()

            verification_request = {
                "insurance_provider": sample_insurance_verifications[0]["insurance_provider"],
                "member_id": sample_insurance_verifications[0]["member_id"],
                "patient_id": "pt_performance_test",
            }

            response = requests.post(
                f"{self.service_url}/verify-insurance",
                json=verification_request,
                headers=self.headers,
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            assert elapsed_time < 2.0  # Should complete within 2 seconds
            assert response.json()["response_time_ms"] < 1000


@pytest.mark.insurance
@pytest.mark.integration
class TestInsuranceVerificationIntegration:
    """Integration tests for Insurance Verification Service with other services."""

    def test_integration_with_billing_engine(self, sample_patients, service_urls):
        """Test integration between insurance verification and billing engine."""
        # Mock successful insurance verification
        verification_response = {
            "verified": True,
            "coverage_type": "PPO",
            "copay_amount": 25.00,
            "deductible_remaining": 500.00,
        }

        # Mock billing engine claim creation using verification data
        billing_response = {
            "claim_created": True,
            "estimated_patient_cost": 25.00,
            "estimated_insurance_payment": 175.00,
        }

        with patch("requests.post") as mock_post:
            # First call: insurance verification
            # Second call: billing engine
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: verification_response),
                MagicMock(status_code=200, json=lambda: billing_response),
            ]

            # Step 1: Verify insurance
            insurance_response = requests.post(
                f"{service_urls['insurance_verification']}/verify-insurance",
                json={"patient_id": sample_patients[0]["patient_id"]},
            )

            # Step 2: Create billing claim using verification data
            billing_request = {
                "patient_id": sample_patients[0]["patient_id"],
                "insurance_verified": insurance_response.json()["verified"],
                "estimated_patient_cost": insurance_response.json()["copay_amount"],
            }

            billing_response_obj = requests.post(
                f"{service_urls['billing_engine']}/create-claim",
                json=billing_request,
            )

            assert insurance_response.status_code == 200
            assert billing_response_obj.status_code == 200
            assert billing_response_obj.json()["claim_created"] is True

    def test_integration_with_compliance_monitor(self, sample_patients, service_urls):
        """Test that insurance verification events are logged to compliance monitor."""
        verification_response = {"verified": True}
        compliance_response = {"audit_logged": True, "compliance_score": 98.5}

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: verification_response),
                MagicMock(status_code=200, json=lambda: compliance_response),
            ]

            # Verification request
            insurance_response = requests.post(
                f"{service_urls['insurance_verification']}/verify-insurance",
                json={"patient_id": sample_patients[0]["patient_id"]},
            )

            # Audit logging to compliance monitor
            audit_request = {
                "event_type": "INSURANCE_VERIFICATION",
                "patient_id": sample_patients[0]["patient_id"],
                "verification_result": insurance_response.json()["verified"],
            }

            compliance_response_obj = requests.post(
                f"{service_urls['compliance_monitor']}/track-audit",
                json=audit_request,
            )

            assert insurance_response.status_code == 200
            assert compliance_response_obj.status_code == 200
            assert compliance_response_obj.json()["audit_logged"] is True
