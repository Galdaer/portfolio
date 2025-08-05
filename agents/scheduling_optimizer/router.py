"""
FastAPI Router for Healthcare Scheduling Optimizer Agent
Provides REST API endpoints for appointment scheduling and optimization
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status

from core.infrastructure.healthcare_logger import get_healthcare_logger, log_healthcare_event
from core.infrastructure.phi_monitor import phi_monitor_decorator as phi_monitor
from core.infrastructure.phi_monitor import scan_for_phi

from .scheduling_agent import scheduling_optimizer_agent

logger = get_healthcare_logger("api.scheduling_optimizer")
router = APIRouter(prefix="/scheduling", tags=["scheduling_optimizer"])


@router.post("/schedule-appointment")
@phi_monitor(risk_level="medium", operation_type="api_appointment_scheduling")
async def schedule_appointment(appointment_request: dict[str, Any]) -> dict[str, Any]:
    """
    Schedule a patient appointment with optimization

    Medical Disclaimer: Administrative scheduling support only.
    Does not provide medical advice or clinical decision-making.
    """
    try:
        # Validate input for PHI exposure
        scan_for_phi(str(appointment_request))

        log_healthcare_event(
            logger,
            logging.INFO,
            "Appointment scheduling request received",
            context={
                "endpoint": "/scheduling/schedule-appointment",
                "appointment_type": appointment_request.get("appointment_type"),
                "has_patient_id": "patient_id" in appointment_request,
                "has_provider_id": "provider_id" in appointment_request,
            },
            operation_type="api_request",
        )

        result = await scheduling_optimizer_agent.schedule_appointment(appointment_request)

        return {
            "success": True,
            "data": {
                "scheduling_id": result.scheduling_id,
                "status": result.status,
                "appointment_id": result.appointment_id,
                "scheduled_time": result.scheduled_time.isoformat()
                if result.scheduled_time
                else None,
                "provider_id": result.provider_id,
                "scheduling_errors": result.scheduling_errors,
                "compliance_validated": result.compliance_validated,
                "timestamp": result.timestamp.isoformat(),
                "metadata": result.metadata,
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Appointment scheduling API error: {str(e)}",
            context={
                "endpoint": "/scheduling/schedule-appointment",
                "error": str(e),
                "error_type": type(e).__name__,
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Appointment scheduling failed: {str(e)}",
        )


@router.get("/available-slots")
async def find_available_slots(
    provider_id: str,
    appointment_type: str,
    preferred_date: str,
    duration_minutes: int | None = None,
) -> dict[str, Any]:
    """
    Find available appointment slots for specified criteria

    Medical Disclaimer: Administrative scheduling support only.
    Does not provide medical advice or treatment recommendations.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Available slots requested for {provider_id} on {preferred_date}",
            context={
                "endpoint": "/scheduling/available-slots",
                "provider_id": provider_id,
                "appointment_type": appointment_type,
                "preferred_date": preferred_date,
                "duration_minutes": duration_minutes,
            },
            operation_type="slot_search",
        )

        slots = await scheduling_optimizer_agent.find_available_slots(
            provider_id=provider_id,
            appointment_type=appointment_type,
            preferred_date=preferred_date,
            duration_minutes=duration_minutes,
        )

        # Convert slots to JSON-serializable format
        slots_data = [
            {
                "slot_id": slot.slot_id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "provider_id": slot.provider_id,
                "appointment_type": slot.appointment_type,
                "duration_minutes": slot.duration_minutes,
                "room_id": slot.room_id,
                "notes": slot.notes or [],
            }
            for slot in slots
        ]

        return {
            "success": True,
            "data": {
                "available_slots": slots_data,
                "total_slots": len(slots_data),
                "search_criteria": {
                    "provider_id": provider_id,
                    "appointment_type": appointment_type,
                    "preferred_date": preferred_date,
                    "duration_minutes": duration_minutes,
                },
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Available slots API error: {str(e)}",
            context={
                "endpoint": "/scheduling/available-slots",
                "provider_id": provider_id,
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slot search failed: {str(e)}",
        )


@router.get("/optimize-schedule/{provider_id}")
async def optimize_provider_schedule(
    provider_id: str, start_date: str, end_date: str
) -> dict[str, Any]:
    """
    Generate schedule optimization recommendations for provider

    Args:
        provider_id: Provider identifier
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Medical Disclaimer: Administrative scheduling optimization only.
    Does not provide medical advice or clinical recommendations.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Schedule optimization requested for {provider_id}",
            context={
                "endpoint": "/scheduling/optimize-schedule",
                "provider_id": provider_id,
                "start_date": start_date,
                "end_date": end_date,
            },
            operation_type="schedule_optimization",
        )

        date_range = {"start_date": start_date, "end_date": end_date}

        recommendations = await scheduling_optimizer_agent.optimize_provider_schedule(
            provider_id=provider_id, date_range=date_range
        )

        # Convert recommendations to JSON-serializable format
        recommendations_data = [
            {
                "recommendation_id": rec.recommendation_id,
                "recommendation_type": rec.recommendation_type,
                "description": rec.description,
                "potential_savings": rec.potential_savings,
                "implementation_priority": rec.implementation_priority,
                "estimated_impact": rec.estimated_impact,
            }
            for rec in recommendations
        ]

        return {
            "success": True,
            "data": {
                "provider_id": provider_id,
                "date_range": date_range,
                "recommendations": recommendations_data,
                "total_recommendations": len(recommendations_data),
                "high_priority_count": len(
                    [r for r in recommendations if r.implementation_priority == "high"]
                ),
            },
        }

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Schedule optimization API error: {str(e)}",
            context={
                "endpoint": "/scheduling/optimize-schedule",
                "provider_id": provider_id,
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule optimization failed: {str(e)}",
        )


@router.get("/wait-times/{provider_id}")
async def calculate_wait_times(provider_id: str, date: str) -> dict[str, Any]:
    """
    Calculate and analyze patient wait times for optimization

    Args:
        provider_id: Provider identifier
        date: Date in YYYY-MM-DD format

    Medical Disclaimer: Administrative wait time analysis only.
    Does not provide medical advice or clinical insights.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Wait time analysis requested for {provider_id} on {date}",
            context={
                "endpoint": "/scheduling/wait-times",
                "provider_id": provider_id,
                "date": date,
            },
            operation_type="wait_time_analysis",
        )

        analysis = await scheduling_optimizer_agent.calculate_wait_times(provider_id, date)

        return {"success": True, "data": analysis}

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Wait time analysis API error: {str(e)}",
            context={
                "endpoint": "/scheduling/wait-times",
                "provider_id": provider_id,
                "date": date,
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wait time analysis failed: {str(e)}",
        )


@router.get("/capacity-report")
async def generate_capacity_report(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Generate capacity utilization report for scheduling optimization

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Medical Disclaimer: Administrative capacity reporting only.
    Does not provide medical advice or clinical insights.
    """
    try:
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Capacity report requested: {start_date} to {end_date}",
            context={
                "endpoint": "/scheduling/capacity-report",
                "start_date": start_date,
                "end_date": end_date,
            },
            operation_type="capacity_analysis",
        )

        date_range = {"start_date": start_date, "end_date": end_date}

        report = await scheduling_optimizer_agent.generate_capacity_report(date_range)

        return {"success": True, "data": report}

    except Exception as e:
        log_healthcare_event(
            logger,
            logging.ERROR,
            f"Capacity report API error: {str(e)}",
            context={
                "endpoint": "/scheduling/capacity-report",
                "start_date": start_date,
                "end_date": end_date,
                "error": str(e),
            },
            operation_type="api_error",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Capacity report generation failed: {str(e)}",
        )


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint for scheduling optimizer service"""
    return {
        "status": "healthy",
        "service": "scheduling_optimizer",
        "timestamp": datetime.now().isoformat(),
        "capabilities": scheduling_optimizer_agent.capabilities,
    }
