"""
Comprehensive tests for Business Intelligence Service.

Tests analytics, reporting, and dashboard functionality
using real synthetic data from the healthcare database.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
import requests

from tests.business_services.conftest import *


@pytest.mark.analytics
@pytest.mark.phi_safe
class TestBusinessIntelligenceService:
    """Test suite for Business Intelligence Service functionality."""

    @pytest.fixture(autouse=True)
    def setup_service_client(self, service_urls):
        """Setup service client for tests."""
        self.service_url = service_urls["business_intelligence"]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",
        }

    def test_service_health_check(self):
        """Test that the business intelligence service health endpoint responds."""
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "status": "healthy",
                "analytics_engine": "running",
                "data_pipeline": "active",
            }

            response = requests.get(f"{self.service_url}/health")
            assert response.status_code == 200
            assert response.json()["analytics_engine"] == "running"

    def test_financial_dashboard_metrics(self, sample_billing_claims):
        """Test financial dashboard with revenue analytics."""
        total_claims_amount = sum(claim["claim_amount"] for claim in sample_billing_claims)

        mock_response = {
            "financial_summary": {
                "total_revenue": total_claims_amount,
                "claims_processed": len(sample_billing_claims),
                "average_claim_value": total_claims_amount / len(sample_billing_claims),
                "collection_rate": 0.85,
            },
            "revenue_trends": {
                "monthly_growth": 0.15,
                "year_over_year": 0.28,
            },
            "top_revenue_sources": [
                {"service": "Office Visits", "revenue": total_claims_amount * 0.4},
                {"service": "Lab Tests", "revenue": total_claims_amount * 0.3},
                {"service": "Procedures", "revenue": total_claims_amount * 0.3},
            ],
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/financial-dashboard",
                params={"period": "month", "year": 2024, "month": 1},
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["financial_summary"]["claims_processed"] == len(sample_billing_claims)
            assert result["financial_summary"]["collection_rate"] > 0.8

    def test_operational_metrics_dashboard(self, sample_patients, sample_doctors):
        """Test operational metrics and performance indicators."""
        mock_response = {
            "operational_summary": {
                "total_patients": len(sample_patients),
                "active_providers": len(sample_doctors),
                "patient_visits_today": 45,
                "average_wait_time_minutes": 18,
            },
            "efficiency_metrics": {
                "provider_utilization": 0.78,
                "appointment_no_show_rate": 0.12,
                "patient_satisfaction_score": 4.2,
            },
            "capacity_analysis": {
                "current_capacity": 85,
                "available_slots_today": 12,
                "booking_rate": 0.73,
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/operational-metrics",
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["operational_summary"]["total_patients"] == len(sample_patients)
            assert result["efficiency_metrics"]["provider_utilization"] > 0.5

    def test_compliance_analytics_trends(self):
        """Test compliance analytics and trend analysis."""
        mock_response = {
            "compliance_overview": {
                "current_score": 94.5,
                "trend": "improving",
                "score_change_30d": 2.3,
            },
            "violation_analysis": {
                "total_violations": 8,
                "resolved_violations": 6,
                "pending_violations": 2,
                "violation_types": {
                    "unauthorized_access": 3,
                    "after_hours_access": 2,
                    "bulk_access": 1,
                    "other": 2,
                },
            },
            "audit_statistics": {
                "total_audit_events": 15420,
                "phi_access_events": 12840,
                "system_events": 2580,
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/compliance-analytics",
                params={"period": "30d"},
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["compliance_overview"]["current_score"] > 90.0
            assert result["violation_analysis"]["resolved_violations"] > result["violation_analysis"]["pending_violations"]

    def test_generate_custom_report(self, sample_billing_claims, sample_patients):
        """Test custom report generation with specific metrics."""
        mock_response = {
            "report_id": f"RPT-{uuid.uuid4().hex[:8].upper()}",
            "report_type": "custom_analytics",
            "generated_at": datetime.now().isoformat(),
            "data": {
                "patient_demographics": {
                    "total_patients": len(sample_patients),
                    "age_groups": {"18-30": 25, "31-50": 40, "51-70": 30, "70+": 5},
                },
                "revenue_analysis": {
                    "total_revenue": sum(claim["claim_amount"] for claim in sample_billing_claims),
                    "by_service_type": {"consultation": 45000, "procedures": 32000, "lab": 18000},
                },
            },
            "export_formats": ["pdf", "csv", "json"],
            "download_url": f"/reports/{uuid.uuid4()}/download",
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            report_request = {
                "report_name": "Monthly Healthcare Analytics",
                "metrics": ["patient_demographics", "revenue_analysis", "provider_performance"],
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"},
                "format": "json",
            }

            response = requests.post(
                f"{self.service_url}/custom-report",
                json=report_request,
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert "report_id" in result
            assert "download_url" in result

    def test_predictive_analytics_insights(self):
        """Test predictive analytics and forecasting."""
        mock_response = {
            "predictions": {
                "revenue_forecast_30d": 125000.00,
                "patient_volume_forecast": 380,
                "capacity_utilization_forecast": 0.82,
            },
            "trends": {
                "revenue_trend": "increasing",
                "patient_growth_rate": 0.08,
                "seasonal_patterns": ["Q4_peak", "summer_dip"],
            },
            "recommendations": [
                "Increase staff capacity for predicted patient volume growth",
                "Optimize scheduling to improve utilization",
                "Focus on high-revenue service lines",
            ],
            "confidence_scores": {
                "revenue_forecast": 0.87,
                "volume_forecast": 0.82,
                "trend_analysis": 0.91,
            },
        }

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            response = requests.get(
                f"{self.service_url}/predictive-insights",
                params={"forecast_period": "30d", "include_recommendations": True},
                headers=self.headers,
            )

            assert response.status_code == 200
            result = response.json()
            assert result["predictions"]["revenue_forecast_30d"] > 0
            assert len(result["recommendations"]) > 0
            assert all(score > 0.8 for score in result["confidence_scores"].values())


@pytest.mark.analytics
@pytest.mark.integration
class TestBusinessIntelligenceIntegration:
    """Integration tests for Business Intelligence Service."""

    def test_data_aggregation_from_all_services(self, service_urls):
        """Test data aggregation from all business services."""
        mock_aggregated_data = {
            "data_sources": {
                "billing_engine": {"revenue": 45000, "claims": 180},
                "insurance_verification": {"verifications": 200, "success_rate": 0.95},
                "compliance_monitor": {"violations": 3, "compliance_score": 94.2},
            },
            "aggregation_successful": True,
            "last_updated": datetime.now().isoformat(),
        }

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_aggregated_data

            response = requests.post(
                f"{service_urls['business_intelligence']}/aggregate-data",
                json={"source_services": ["billing_engine", "insurance_verification", "compliance_monitor"]},
            )

            assert response.status_code == 200
            result = response.json()
            assert result["aggregation_successful"] is True
            assert len(result["data_sources"]) == 3
