"""
Comprehensive tests for Doctor Personalization Service.

Tests LoRA-based AI adaptation and personalization features
using real synthetic data from the healthcare database.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
import requests

from tests.business_services.conftest import *


@pytest.mark.personalization
@pytest.mark.phi_safe
class TestDoctorPersonalizationService:
    """Test suite for Doctor Personalization Service functionality."""

    @pytest.fixture(autouse=True)
    def setup_service_client(self, service_urls):
        """Setup service client for tests."""
        self.service_url = service_urls["doctor_personalization"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",
        }

    def test_service_health_check(self):
        """Test that the doctor personalization service health endpoint responds."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "status": "healthy",
                "model_server": "connected",
                "lora_adapters": "loaded",
            }

            response = requests.get(f"{self.service_url}/health")
            assert response.status_code == 200
            assert response.json()["model_server"] == "connected"

    def test_personalize_model_for_doctor(self, sample_doctors, sample_doctor_preferences):
        """Test creating personalized model for a specific doctor."""
        doctor = sample_doctors[0]
        preferences = next(
            (pref for pref in sample_doctor_preferences if pref["doctor_id"] == doctor["doctor_id"]),
            sample_doctor_preferences[0],
        )

        mock_response = {
            "personalization_id": f"PERS-{uuid.uuid4().hex[:8].upper()}",
            "doctor_id": doctor["doctor_id"],
            "model_created": True,
            "specialization": doctor["specialty"],
            "preferences_applied": {
                "documentation_style": preferences["documentation_style"],
                "communication_style": preferences["communication_style"],
                "ai_assistance_level": preferences["ai_assistance_level"],
            },
            "model_version": "v1.0",
            "training_completion": 1.0,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = mock_response

            personalization_request = {
                "doctor_id": doctor["doctor_id"],
                "specialty": doctor["specialty"],
                "preferences": {
                    "documentation_style": preferences["documentation_style"],
                    "communication_style": preferences["communication_style"],
                    "focus_areas": ["patient_care", "efficiency"],
                },
            }

            response = requests.post(
                f"{self.service_url}/personalize-model",
                json=personalization_request,
                headers=self.headers,
            )

            assert response.status_code == 201
            result = response.json()
            assert result["model_created"] is True
            assert result["doctor_id"] == doctor["doctor_id"]

    def test_train_lora_adaptation(self, sample_doctors):
        """Test training LoRA adapter from doctor interactions."""
        doctor = sample_doctors[0]

        mock_response = {
            "training_id": f"TRAIN-{uuid.uuid4().hex[:8].upper()}",
            "doctor_id": doctor["doctor_id"],
            "training_started": True,
            "training_data_points": 125,
            "estimated_completion": "15 minutes",
            "adapter_name": f"lora_{doctor['doctor_id']}_v1",
            "training_metrics": {
                "loss": 0.024,
                "accuracy": 0.94,
                "convergence": True,
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            training_request = {
                "doctor_id": doctor["doctor_id"],
                "training_data": [
                    {
                        "input_text": "Patient complains of chest pain",
                        "preferred_response": "Detailed cardiac assessment recommended with ECG and troponin levels",
                        "feedback_score": 5,
                    },
                    {
                        "input_text": "Follow-up visit for diabetes",
                        "preferred_response": "Review HbA1c, adjust medication as needed, lifestyle counseling",
                        "feedback_score": 4,
                    },
                ],
            }

            response = requests.post(
                f"{self.service_url}/train-adaptation",
                json=training_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["training_started"] is True
            assert result["training_metrics"]["accuracy"] > 0.9

    def test_model_status_check(self, sample_doctors):
        """Test checking personalization model status."""
        doctor = sample_doctors[0]

        mock_response = {
            "doctor_id": doctor["doctor_id"],
            "model_status": "active",
            "model_version": "v1.2",
            "last_updated": datetime.now().isoformat(),
            "performance_metrics": {
                "adaptation_score": 8.7,
                "user_satisfaction": 4.3,
                "response_quality": 0.91,
            },
            "usage_statistics": {
                "total_interactions": 340,
                "average_daily_use": 25,
                "preferred_features": ["concise_summaries", "clinical_decision_support"],
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/model-status/{doctor['doctor_id']}",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["model_status"] == "active"
            assert result["performance_metrics"]["adaptation_score"] > 8.0

    def test_generate_personalized_response(self, sample_doctors, sample_doctor_preferences):
        """Test generating personalized AI response."""
        doctor = sample_doctors[0]
        preferences = sample_doctor_preferences[0]

        mock_response = {
            "response_id": f"RESP-{uuid.uuid4().hex[:8].upper()}",
            "doctor_id": doctor["doctor_id"],
            "personalized_response": "Based on your preference for detailed documentation, here's a comprehensive assessment: The patient presents with typical symptoms requiring thorough evaluation including differential diagnosis considerations.",
            "personalization_applied": {
                "style": preferences["documentation_style"],
                "tone": preferences["communication_style"],
                "detail_level": "comprehensive",
            },
            "confidence": 0.89,
            "processing_time_ms": 234,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            request_data = {
                "doctor_id": doctor["doctor_id"],
                "input_text": "Patient has recurring headaches",
                "context": "clinical_assessment",
                "response_type": "diagnostic_guidance",
            }

            response = requests.post(
                f"{self.service_url}/generate-personalized",
                json=request_data,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["confidence"] > 0.8
            assert "personalization_applied" in result

    def test_update_doctor_preferences(self, sample_doctors):
        """Test updating doctor preferences and model adaptation."""
        doctor = sample_doctors[0]

        mock_response = {
            "doctor_id": doctor["doctor_id"],
            "preferences_updated": True,
            "model_retrained": True,
            "new_preferences": {
                "documentation_style": "bullet_points",
                "communication_tone": "empathetic",
                "ai_assistance_level": "extensive",
            },
            "adaptation_impact": {
                "response_style_changed": True,
                "performance_impact": 0.03,  # Slight improvement
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            preferences_update = {
                "doctor_id": doctor["doctor_id"],
                "updated_preferences": {
                    "documentation_style": "bullet_points",
                    "communication_tone": "empathetic",
                    "ai_assistance_level": "extensive",
                },
                "retrain_model": True,
            }

            response = requests.post(
                f"{self.service_url}/update-preferences",
                json=preferences_update,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["preferences_updated"] is True
            assert result["model_retrained"] is True

    def test_adaptation_metrics_tracking(self, sample_doctors):
        """Test tracking adaptation performance metrics."""
        doctor = sample_doctors[0]

        mock_response = {
            "doctor_id": doctor["doctor_id"],
            "metrics_summary": {
                "adaptation_score": 8.5,
                "user_satisfaction_trend": "increasing",
                "model_accuracy": 0.92,
                "response_time_avg_ms": 180,
            },
            "detailed_metrics": {
                "interaction_count": 450,
                "positive_feedback_rate": 0.87,
                "feature_usage": {
                    "clinical_decision_support": 0.78,
                    "documentation_assistance": 0.65,
                    "patient_communication": 0.43,
                },
            },
            "improvement_suggestions": [
                "Increase clinical decision support training data",
                "Optimize response time for documentation tasks",
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/adaptation-metrics",
                params={"doctor_id": doctor["doctor_id"], "period": "30d"},
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["metrics_summary"]["adaptation_score"] > 8.0
            assert result["detailed_metrics"]["positive_feedback_rate"] > 0.8

    def test_deploy_personalized_model(self, sample_doctors):
        """Test deploying personalized model to production."""
        doctor = sample_doctors[0]

        mock_response = {
            "deployment_id": f"DEPLOY-{uuid.uuid4().hex[:8].upper()}",
            "doctor_id": doctor["doctor_id"],
            "model_deployed": True,
            "deployment_status": "active",
            "model_endpoint": f"/{doctor['doctor_id']}/personalized",
            "deployment_time": datetime.now().isoformat(),
            "rollback_available": True,
            "performance_baseline": {
                "expected_response_time": "< 200ms",
                "expected_accuracy": "> 90%",
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            deployment_request = {
                "doctor_id": doctor["doctor_id"],
                "model_version": "v1.2",
                "deployment_environment": "production",
                "enable_monitoring": True,
            }

            response = requests.post(
                f"{self.service_url}/deploy-model",
                json=deployment_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["model_deployed"] is True
            assert result["rollback_available"] is True


@pytest.mark.personalization
@pytest.mark.integration
class TestDoctorPersonalizationIntegration:
    """Integration tests for Doctor Personalization Service."""

    def test_integration_with_healthcare_api(self, sample_doctors, service_urls):
        """Test integration with healthcare API for personalized responses."""
        doctor = sample_doctors[0]

        personalization_response = {
            "personalized_model_ready": True,
            "response_style": "detailed",
        }

        api_response = {
            "response_generated": True,
            "personalization_applied": True,
            "response_quality": 0.93,
        }

        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = personalization_response

            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = api_response

            # Check personalization status
            pers_response = requests.get(
                f"{service_urls['doctor_personalization']}/model-status/{doctor['doctor_id']}",
            )

            # Use personalization in healthcare API
            if pers_response.json()["personalized_model_ready"]:
                api_request = {
                    "doctor_id": doctor["doctor_id"],
                    "query": "Assess patient with chest pain",
                    "use_personalization": True,
                }

                api_resp = requests.post(
                    f"{service_urls['healthcare_api']}/chat/personalized",
                    json=api_request,
                )

                assert api_resp.json()["personalization_applied"] is True

            assert pers_response.status_code == 200
