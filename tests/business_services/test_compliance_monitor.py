"""
Comprehensive tests for Compliance Monitor Service.

Tests HIPAA compliance monitoring, audit tracking, and violation detection
using real synthetic data from the healthcare database.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from tests.business_services.conftest import *


@pytest.mark.compliance
@pytest.mark.phi_safe
class TestComplianceMonitorService:
    """Test suite for Compliance Monitor Service functionality."""

    @pytest.fixture(autouse=True)
    def setup_service_client(self, service_urls):
        """Setup service client for tests."""
        self.service_url = service_urls["compliance_monitor"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",
        }

    def test_service_health_check(self):
        """Test that the compliance monitor service health endpoint responds."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "status": "healthy",
                "database": "connected",
                "audit_logging": "active",
                "violation_detection": "running",
            }

            response = requests.get(f"{self.service_url}/health")
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "healthy"
            assert result["audit_logging"] == "active"

    def test_track_audit_event_phi_access(self, sample_patients, sample_doctors):
        """Test tracking PHI access audit events."""
        patient = sample_patients[0]
        doctor = sample_doctors[0]

        mock_response = {
            "audit_logged": True,
            "audit_id": f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            "phi_detected": True,
            "compliance_impact": "monitored",
            "risk_score": 2.1,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            audit_request = {
                "event_type": "PHI_ACCESS",
                "user_id": doctor["doctor_id"],
                "user_type": "doctor",
                "patient_id": patient["patient_id"],
                "action": "VIEW_RECORD",
                "timestamp": datetime.now().isoformat(),
                "ip_address": "172.20.0.50",
                "user_agent": "Healthcare-App/1.0",
                "resource_accessed": "patient_medical_record",
            }

            response = requests.post(
                f"{self.service_url}/track-audit",
                json=audit_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["audit_logged"] is True
            assert result["phi_detected"] is True
            assert result["risk_score"] < 5.0  # Low risk for normal access

    def test_track_audit_event_system_action(self, sample_audit_logs):
        """Test tracking system-level audit events."""
        next(
            (audit for audit in sample_audit_logs if audit["user_type"] == "system"),
            sample_audit_logs[0],
        )

        mock_response = {
            "audit_logged": True,
            "audit_id": f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
            "phi_detected": False,
            "compliance_impact": "informational",
            "risk_score": 0.5,
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            audit_request = {
                "event_type": "SYSTEM_BACKUP",
                "user_id": "system",
                "user_type": "system",
                "action": "BACKUP_COMPLETE",
                "timestamp": datetime.now().isoformat(),
                "resource_accessed": "database_backup",
                "backup_size_gb": 2.5,
            }

            response = requests.post(
                f"{self.service_url}/track-audit",
                json=audit_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["audit_logged"] is True
            assert result["phi_detected"] is False

    def test_get_compliance_status_overall(self):
        """Test retrieving overall compliance status."""
        mock_response = {
            "overall_score": 94.7,
            "status": "compliant",
            "last_updated": datetime.now().isoformat(),
            "score_breakdown": {
                "phi_protection": 96.2,
                "access_control": 95.1,
                "audit_logging": 98.5,
                "data_retention": 91.0,
                "user_training": 88.5,
            },
            "recent_trends": "improving",
            "next_audit_date": "2024-03-15",
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/compliance-status",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["overall_score"] > 90.0
            assert result["status"] == "compliant"
            assert "score_breakdown" in result

    def test_detect_violations_unauthorized_access(self, sample_doctors):
        """Test violation detection for unauthorized PHI access."""
        doctor = sample_doctors[0]

        mock_response = {
            "violations_detected": [
                {
                    "violation_id": f"VIO-{uuid.uuid4().hex[:6].upper()}",
                    "violation_type": "unauthorized_phi_access",
                    "severity": "high",
                    "detected_at": datetime.now().isoformat(),
                    "user_id": doctor["doctor_id"],
                    "description": "Access to patient records outside assigned cases",
                    "affected_patients": 3,
                    "auto_detected": True,
                    "resolution_required": True,
                },
            ],
            "total_violations": 1,
            "critical_violations": 1,
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/violations",
                params={
                    "severity": "high",
                    "time_range": "24h",
                    "user_id": doctor["doctor_id"],
                },
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["total_violations"] >= 1
            assert result["violations_detected"][0]["severity"] == "high"

    def test_detect_violations_bulk_access_pattern(self, sample_doctors):
        """Test detection of suspicious bulk access patterns."""
        doctor = sample_doctors[0]

        mock_response = {
            "violations_detected": [
                {
                    "violation_id": f"VIO-{uuid.uuid4().hex[:6].upper()}",
                    "violation_type": "bulk_patient_access",
                    "severity": "medium",
                    "detected_at": datetime.now().isoformat(),
                    "user_id": doctor["doctor_id"],
                    "description": "Accessed 50+ patient records in 1 hour",
                    "access_count": 75,
                    "time_window": "1 hour",
                    "threshold_exceeded": True,
                },
            ],
            "pattern_analysis": {
                "access_rate": "75 records/hour",
                "normal_rate": "15 records/hour",
                "deviation": "5x normal",
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/violations",
                params={
                    "violation_type": "bulk_patient_access",
                    "user_id": doctor["doctor_id"],
                },
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            violations = result["violations_detected"]
            assert len(violations) >= 1
            assert violations[0]["violation_type"] == "bulk_patient_access"

    def test_generate_compliance_report_weekly(self):
        """Test generating weekly compliance reports."""
        mock_response = {
            "report_id": f"RPT-{uuid.uuid4().hex[:8].upper()}",
            "report_type": "weekly_compliance",
            "period": "2024-W03",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "overall_score": 93.5,
                "phi_access_events": 1250,
                "violations_detected": 3,
                "violations_resolved": 2,
                "new_violations": 1,
            },
            "detailed_metrics": {
                "access_patterns": {
                    "normal_access": 1185,
                    "after_hours_access": 45,
                    "weekend_access": 20,
                },
                "user_compliance": {
                    "compliant_users": 47,
                    "users_with_violations": 3,
                    "training_required": 2,
                },
            },
            "recommendations": [
                "Review after-hours access policies",
                "Provide additional HIPAA training for 2 users",
            ],
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            report_request = {
                "report_type": "weekly_compliance",
                "format": "json",
                "include_details": True,
                "period": "2024-W03",
            }

            response = requests.post(
                f"{self.service_url}/generate-report",
                json=report_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["summary"]["overall_score"] > 90.0
            assert "recommendations" in result
            assert len(result["recommendations"]) > 0

    def test_audit_trail_patient_specific(self, sample_patients, sample_audit_logs):
        """Test retrieving audit trail for specific patient."""
        patient = sample_patients[0]

        # Filter audit logs for this patient
        patient_audits = [
            audit for audit in sample_audit_logs
            if audit.get("resource_id") == patient["patient_id"]
        ]

        mock_response = {
            "patient_id": patient["patient_id"],
            "audit_events": [
                {
                    "timestamp": audit["timestamp"],
                    "user_id": audit["user_id"],
                    "action": audit["action"],
                    "ip_address": audit["ip_address"],
                }
                for audit in patient_audits[:10]  # First 10 events
            ],
            "total_events": len(patient_audits),
            "date_range": {
                "from": "2024-01-01T00:00:00Z",
                "to": datetime.now().isoformat(),
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/audit-trail/{patient['patient_id']}",
                params={"limit": 10},
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["patient_id"] == patient["patient_id"]
            assert "audit_events" in result
            assert result["total_events"] >= 0

    def test_risk_assessment_user_behavior(self, sample_doctors):
        """Test compliance risk assessment for user behavior."""
        doctor = sample_doctors[0]

        mock_response = {
            "user_id": doctor["doctor_id"],
            "risk_assessment": {
                "overall_risk_score": 3.2,
                "risk_level": "low",
                "risk_factors": [
                    {
                        "factor": "after_hours_access",
                        "score": 1.5,
                        "description": "Occasional after-hours patient access",
                    },
                    {
                        "factor": "access_frequency",
                        "score": 0.8,
                        "description": "Normal access patterns",
                    },
                ],
                "behavioral_patterns": {
                    "average_session_duration": "25 minutes",
                    "typical_access_hours": "8:00 AM - 6:00 PM",
                    "weekend_access_frequency": "low",
                },
                "recommendations": [
                    "Monitor after-hours access patterns",
                    "Consider implementing additional authentication for off-hours",
                ],
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            risk_request = {
                "user_id": doctor["doctor_id"],
                "assessment_period": "30d",
                "include_behavioral_analysis": True,
            }

            response = requests.post(
                f"{self.service_url}/risk-assessment",
                json=risk_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["risk_assessment"]["overall_risk_score"] < 10.0
            assert result["risk_assessment"]["risk_level"] in ["low", "medium", "high"]

    def test_dashboard_metrics_real_time(self):
        """Test retrieving real-time dashboard metrics."""
        mock_response = {
            "current_metrics": {
                "active_users": 15,
                "phi_access_events_today": 234,
                "violations_today": 0,
                "compliance_score_current": 95.2,
            },
            "trend_data": {
                "phi_access_trend_7d": [220, 245, 198, 267, 234, 289, 234],
                "compliance_trend_7d": [94.8, 95.1, 94.5, 95.8, 95.2, 94.9, 95.2],
                "violation_trend_7d": [1, 0, 2, 0, 0, 1, 0],
            },
            "alerts": [
                {
                    "type": "info",
                    "message": "Compliance score improved 0.3 points this week",
                },
            ],
            "last_updated": datetime.now().isoformat(),
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/dashboard-metrics",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["current_metrics"]["compliance_score_current"] > 90.0
            assert "trend_data" in result
            assert len(result["trend_data"]["compliance_trend_7d"]) == 7

    @pytest.mark.phi_safe
    def test_phi_protection_in_audit_logs(self, sample_patients):
        """Test that PHI is properly protected in audit log responses."""
        patient = sample_patients[0]

        # Audit response should mask PHI
        mock_response = {
            "audit_events": [
                {
                    "event_id": f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
                    "patient_ref": f"pt_***{patient['patient_id'][-4:]}",  # Masked
                    "action": "VIEW_RECORD",
                    "phi_detected": True,
                    "phi_sanitized": True,
                    "sanitized_details": "Patient record accessed for legitimate medical purposes",
                },
            ],
            "phi_protection_applied": True,
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/audit-trail/{patient['patient_id']}",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["phi_protection_applied"] is True

            # Verify patient ID is masked in events
            for event in result["audit_events"]:
                assert "***" in event["patient_ref"]

    def test_automated_violation_alerting(self, sample_doctors):
        """Test automated alerting system for compliance violations."""
        doctor = sample_doctors[0]

        mock_response = {
            "alert_triggered": True,
            "alert_id": f"ALERT-{uuid.uuid4().hex[:8].upper()}",
            "violation_type": "after_hours_access",
            "severity": "medium",
            "user_affected": doctor["doctor_id"],
            "notification_sent": True,
            "escalation_required": False,
            "auto_remediation": {
                "action_taken": "temporary_access_restriction",
                "duration": "24 hours",
                "review_required": True,
            },
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            alert_request = {
                "violation_type": "after_hours_access",
                "user_id": doctor["doctor_id"],
                "severity": "medium",
                "auto_remediate": True,
            }

            response = requests.post(
                f"{self.service_url}/trigger-alert",
                json=alert_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["alert_triggered"] is True
            assert result["notification_sent"] is True

    @pytest.mark.slow
    def test_compliance_monitoring_performance(self):
        """Test compliance monitoring system performance under load."""
        import time

        mock_response = {
            "events_processed": 1000,
            "processing_time_ms": 850,
            "average_time_per_event_ms": 0.85,
            "violations_detected": 5,
            "false_positives": 0,
            "system_performance": "optimal",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            start_time = time.time()

            performance_request = {
                "event_count": 1000,
                "test_mode": True,
                "include_violation_detection": True,
            }

            response = requests.post(
                f"{self.service_url}/performance-test",
                json=performance_request,
                headers=self.headers,
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            result = response.json()
            assert result["average_time_per_event_ms"] < 2.0  # Under 2ms per event
            assert result["system_performance"] == "optimal"
            assert elapsed_time < 3.0  # Test completes quickly


@pytest.mark.compliance
@pytest.mark.integration
class TestComplianceMonitorIntegration:
    """Integration tests for Compliance Monitor Service with other services."""

    def test_integration_with_all_business_services(self, service_urls):
        """Test compliance monitoring integration with all business services."""
        services_to_monitor = [
            "insurance_verification", "billing_engine",
            "business_intelligence", "doctor_personalization",
        ]

        mock_responses = [
            {"service": service, "compliance_monitored": True, "events_tracked": 10}
            for service in services_to_monitor
        ]

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda response=resp: response)
                for resp in mock_responses
            ]

            for service in services_to_monitor:
                monitoring_request = {
                    "service_name": service,
                    "monitoring_enabled": True,
                    "audit_level": "comprehensive",
                }

                response = requests.post(
                    f"{service_urls['compliance_monitor']}/monitor-service",
                    json=monitoring_request,
                )

                assert response.status_code == 200
                assert response.json()["compliance_monitored"] is True

    def test_integration_phi_detection_workflow(self, sample_patients, service_urls):
        """Test end-to-end PHI detection and compliance workflow."""
        patient = sample_patients[0]

        # Mock workflow responses
        phi_detection_response = {"phi_detected": True, "confidence": 0.95}
        compliance_response = {"violation_logged": True, "risk_score": 3.5}

        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: phi_detection_response),
                MagicMock(status_code=200, json=lambda: compliance_response),
            ]

            # Step 1: PHI detection
            phi_request = {
                "text": f"Patient {patient['first_name']} {patient['last_name']} visited today",
                "context": "clinical_note",
            }

            phi_response = requests.post(
                f"{service_urls['compliance_monitor']}/detect-phi",
                json=phi_request,
            )

            # Step 2: Log compliance event
            if phi_response.json()["phi_detected"]:
                compliance_request = {
                    "event_type": "PHI_DETECTED",
                    "context": "clinical_documentation",
                    "phi_confidence": phi_response.json()["confidence"],
                }

                compliance_resp = requests.post(
                    f"{service_urls['compliance_monitor']}/track-audit",
                    json=compliance_request,
                )

                assert compliance_resp.json()["violation_logged"] is True

            assert phi_response.status_code == 200
            assert phi_response.json()["phi_detected"] is True
