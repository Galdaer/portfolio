"""
Healthcare Scheduling Optimizer Agent - Administrative Scheduling Support Only
Handles appointment scheduling, resource optimization, and calendar management for healthcare workflows
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional
import asyncio
import json

from agents import BaseHealthcareAgent
from core.infrastructure.healthcare_logger import (
    get_healthcare_logger,
    healthcare_log_method,
    healthcare_agent_log,
    log_healthcare_event
)
from core.infrastructure.phi_monitor import phi_monitor, scan_for_phi, sanitize_healthcare_data

logger = get_healthcare_logger('agent.scheduling_optimizer')


@dataclass
class AppointmentSlot:
    """Available appointment slot with scheduling details"""
    
    slot_id: str
    start_time: datetime
    end_time: datetime
    provider_id: str
    appointment_type: str
    is_available: bool
    duration_minutes: int
    room_id: Optional[str] = None
    notes: List[str] = None


@dataclass
class SchedulingResult:
    """Result from scheduling operation with compliance validation"""
    
    scheduling_id: str
    status: str
    appointment_id: Optional[str]
    scheduled_time: Optional[datetime]
    provider_id: Optional[str]
    scheduling_errors: List[str]
    compliance_validated: bool
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class OptimizationRecommendation:
    """Schedule optimization recommendation"""
    
    recommendation_id: str
    recommendation_type: str
    description: str
    potential_savings: Dict[str, Any]
    implementation_priority: str
    estimated_impact: int


class SchedulingOptimizerAgent(BaseHealthcareAgent):
    """
    Healthcare Scheduling Optimizer Agent
    
    MEDICAL DISCLAIMER: This agent provides administrative scheduling support and resource
    optimization assistance only. It helps healthcare professionals optimize appointment
    scheduling, manage provider calendars, and improve operational efficiency. It does not
    provide medical advice, diagnosis, or treatment recommendations. All medical decisions
    must be made by qualified healthcare professionals.
    
    Capabilities:
    - Appointment scheduling and management
    - Provider calendar optimization
    - Resource allocation and room scheduling
    - Wait time reduction analysis
    - Capacity planning and utilization
    - Appointment reminder coordination
    """
    
    def __init__(self):
        super().__init__()
        self.agent_type = "scheduling_optimizer"
        self.capabilities = [
            "appointment_scheduling",
            "calendar_optimization",
            "resource_allocation",
            "wait_time_analysis",
            "capacity_planning",
            "reminder_coordination"
        ]
        
        # Initialize scheduling parameters
        self.standard_appointment_durations = {
            "routine_checkup": 30,
            "physical_exam": 60,
            "consultation": 45,
            "follow_up": 20,
            "procedure": 90,
            "lab_work": 15
        }
        
        # Log agent initialization with healthcare context
        log_healthcare_event(
            logger,
            logging.INFO,
            "Healthcare Scheduling Optimizer Agent initialized",
            context={
                'agent': 'scheduling_optimizer',
                'initialization': True,
                'phi_monitoring': True,
                'medical_advice_disabled': True,
                'capabilities': self.capabilities
            },
            operation_type='agent_initialization'
        )
    
    @healthcare_log_method(logger)
    @phi_monitor(risk_level="medium", operation_type="appointment_scheduling")
    async def schedule_appointment(self, appointment_request: Dict[str, Any]) -> SchedulingResult:
        """
        Schedule a patient appointment with optimization and compliance validation
        
        Args:
            appointment_request: Dictionary containing appointment details
            
        Returns:
            SchedulingResult with scheduling status and validation
            
        Medical Disclaimer: Administrative scheduling support only.
        Does not provide medical advice or clinical decision-making.
        """
        # Validate and sanitize input data for PHI protection
        scan_for_phi(str(appointment_request))
        
        scheduling_errors = []
        appointment_id = None
        scheduled_time = None
        
        try:
            # Validate required fields
            required_fields = ['patient_id', 'provider_id', 'appointment_type', 'preferred_date']
            for field in required_fields:
                if field not in appointment_request:
                    scheduling_errors.append(f"Missing required field: {field}")
            
            if scheduling_errors:
                return SchedulingResult(
                    scheduling_id=f"sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status="validation_failed",
                    appointment_id=None,
                    scheduled_time=None,
                    provider_id=appointment_request.get('provider_id'),
                    scheduling_errors=scheduling_errors,
                    compliance_validated=False,
                    timestamp=datetime.now(),
                    metadata={"validation_stage": "required_fields"}
                )
            
            # Find available slots
            available_slots = await self.find_available_slots(
                provider_id=appointment_request['provider_id'],
                appointment_type=appointment_request['appointment_type'],
                preferred_date=appointment_request['preferred_date'],
                duration_minutes=appointment_request.get('duration_minutes')
            )
            
            if not available_slots:
                scheduling_errors.append("No available slots found for requested date and provider")
                return SchedulingResult(
                    scheduling_id=f"sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    status="no_availability",
                    appointment_id=None,
                    scheduled_time=None,
                    provider_id=appointment_request['provider_id'],
                    scheduling_errors=scheduling_errors,
                    compliance_validated=True,
                    timestamp=datetime.now(),
                    metadata={"available_slots_count": 0}
                )
            
            # Select optimal slot
            optimal_slot = self._select_optimal_slot(available_slots, appointment_request)
            
            # Create appointment
            appointment_id = f"APPT{datetime.now().strftime('%Y%m%d%H%M%S')}"
            scheduled_time = optimal_slot.start_time
            
            log_healthcare_event(
                logger,
                logging.INFO,
                f"Appointment scheduled successfully: {appointment_id}",
                context={
                    'appointment_id': appointment_id,
                    'provider_id': appointment_request['provider_id'],
                    'appointment_type': appointment_request['appointment_type'],
                    'scheduled_time': scheduled_time.isoformat(),
                    'slot_id': optimal_slot.slot_id
                },
                operation_type='appointment_scheduling'
            )
            
            return SchedulingResult(
                scheduling_id=f"sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="scheduled",
                appointment_id=appointment_id,
                scheduled_time=scheduled_time,
                provider_id=appointment_request['provider_id'],
                scheduling_errors=[],
                compliance_validated=True,
                timestamp=datetime.now(),
                metadata={
                    "slot_id": optimal_slot.slot_id,
                    "duration_minutes": optimal_slot.duration_minutes,
                    "room_id": optimal_slot.room_id
                }
            )
            
        except Exception as e:
            log_healthcare_event(
                logger,
                logging.ERROR,
                f"Appointment scheduling failed: {str(e)}",
                context={
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'provider_id': appointment_request.get('provider_id')
                },
                operation_type='scheduling_error'
            )
            
            return SchedulingResult(
                scheduling_id=f"sched_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status="scheduling_failed",
                appointment_id=None,
                scheduled_time=None,
                provider_id=appointment_request.get('provider_id'),
                scheduling_errors=[f"Scheduling error: {str(e)}"],
                compliance_validated=False,
                timestamp=datetime.now(),
                metadata={"error_stage": "processing_exception"}
            )
    
    @healthcare_log_method(logger)
    async def find_available_slots(
        self,
        provider_id: str,
        appointment_type: str,
        preferred_date: str,
        duration_minutes: Optional[int] = None
    ) -> List[AppointmentSlot]:
        """
        Find available appointment slots for specified criteria
        
        Args:
            provider_id: Provider identifier
            appointment_type: Type of appointment
            preferred_date: Preferred date in YYYY-MM-DD format
            duration_minutes: Optional specific duration
            
        Returns:
            List of available AppointmentSlot objects
        """
        # Get duration from type if not specified
        if duration_minutes is None:
            duration_minutes = self.standard_appointment_durations.get(appointment_type, 30)
        
        # Parse preferred date
        try:
            preferred_datetime = datetime.strptime(preferred_date, '%Y-%m-%d')
        except ValueError:
            return []
        
        # Mock availability check (in production, query actual calendar system)
        available_slots = []
        
        # Generate sample slots for the day (9 AM to 5 PM, 30-minute intervals)
        start_hour = 9
        end_hour = 17
        
        current_time = preferred_datetime.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = preferred_datetime.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        slot_counter = 1
        while current_time < end_time:
            # Skip lunch hour (12-1 PM)
            if current_time.hour != 12:
                slot_end_time = current_time + timedelta(minutes=duration_minutes)
                
                # Mock availability (80% of slots available)
                is_available = slot_counter % 5 != 0
                
                if is_available:
                    available_slots.append(AppointmentSlot(
                        slot_id=f"slot_{provider_id}_{current_time.strftime('%Y%m%d_%H%M')}",
                        start_time=current_time,
                        end_time=slot_end_time,
                        provider_id=provider_id,
                        appointment_type=appointment_type,
                        is_available=True,
                        duration_minutes=duration_minutes,
                        room_id=f"room_{(slot_counter % 5) + 1}",
                        notes=["Standard appointment slot"]
                    ))
            
            current_time += timedelta(minutes=30)
            slot_counter += 1
        
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Found {len(available_slots)} available slots",
            context={
                'provider_id': provider_id,
                'appointment_type': appointment_type,
                'preferred_date': preferred_date,
                'duration_minutes': duration_minutes,
                'slots_found': len(available_slots)
            },
            operation_type='slot_search'
        )
        
        return available_slots
    
    def _select_optimal_slot(self, available_slots: List[AppointmentSlot], appointment_request: Dict[str, Any]) -> AppointmentSlot:
        """
        Select the optimal appointment slot based on scheduling criteria
        
        Args:
            available_slots: List of available slots
            appointment_request: Original appointment request
            
        Returns:
            Optimal AppointmentSlot
        """
        if not available_slots:
            raise ValueError("No available slots to select from")
        
        # Simple optimization: prefer morning slots for routine appointments
        appointment_type = appointment_request.get('appointment_type', '')
        
        if appointment_type in ['routine_checkup', 'physical_exam']:
            # Prefer morning slots (before noon)
            morning_slots = [slot for slot in available_slots if slot.start_time.hour < 12]
            if morning_slots:
                return min(morning_slots, key=lambda x: x.start_time)
        
        # Default: return earliest available slot
        return min(available_slots, key=lambda x: x.start_time)
    
    @healthcare_log_method(logger)
    async def optimize_provider_schedule(self, provider_id: str, date_range: Dict[str, str]) -> List[OptimizationRecommendation]:
        """
        Analyze and optimize provider schedule for efficiency
        
        Args:
            provider_id: Provider identifier
            date_range: Dictionary with 'start_date' and 'end_date'
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Mock schedule analysis (in production, analyze actual appointment data)
        recommendations.extend([
            OptimizationRecommendation(
                recommendation_id=f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_1",
                recommendation_type="slot_consolidation",
                description="Consolidate 15-minute gaps to create 30-minute slots",
                potential_savings={
                    "time_saved_minutes": 45,
                    "additional_appointments": 3,
                    "efficiency_gain_percent": 15
                },
                implementation_priority="high",
                estimated_impact=85
            ),
            OptimizationRecommendation(
                recommendation_id=f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_2",
                recommendation_type="appointment_grouping",
                description="Group similar appointment types to reduce setup time",
                potential_savings={
                    "time_saved_minutes": 30,
                    "setup_reduction_percent": 25,
                    "workflow_efficiency": 20
                },
                implementation_priority="medium",
                estimated_impact=70
            ),
            OptimizationRecommendation(
                recommendation_id=f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_3",
                recommendation_type="buffer_time_optimization",
                description="Adjust buffer times based on appointment complexity",
                potential_savings={
                    "time_saved_minutes": 20,
                    "reduced_overtime_hours": 1.5,
                    "stress_reduction_score": 30
                },
                implementation_priority="low",
                estimated_impact=60
            )
        ])
        
        log_healthcare_event(
            logger,
            logging.INFO,
            f"Generated {len(recommendations)} optimization recommendations",
            context={
                'provider_id': provider_id,
                'date_range': date_range,
                'recommendations_count': len(recommendations),
                'high_priority_count': len([r for r in recommendations if r.implementation_priority == 'high'])
            },
            operation_type='schedule_optimization'
        )
        
        return recommendations
    
    @healthcare_log_method(logger)
    async def calculate_wait_times(self, provider_id: str, date: str) -> Dict[str, Any]:
        """
        Calculate and analyze patient wait times for optimization
        
        Args:
            provider_id: Provider identifier
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with wait time analysis
        """
        # Mock wait time analysis (in production, use actual appointment data)
        wait_time_analysis = {
            "analysis_id": f"wait_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "provider_id": provider_id,
            "date": date,
            "statistics": {
                "average_wait_minutes": 12.5,
                "median_wait_minutes": 8.0,
                "max_wait_minutes": 35.0,
                "min_wait_minutes": 2.0,
                "total_appointments": 18,
                "on_time_percentage": 78.5
            },
            "time_periods": {
                "morning": {"avg_wait": 8.2, "appointment_count": 6},
                "afternoon": {"avg_wait": 15.8, "appointment_count": 8},
                "evening": {"avg_wait": 14.1, "appointment_count": 4}
            },
            "recommendations": [
                "Consider reducing afternoon appointment duration",
                "Add 5-minute buffer between complex procedures",
                "Morning slots show optimal efficiency"
            ],
            "generated_timestamp": datetime.now().isoformat()
        }
        
        log_healthcare_event(
            logger,
            logging.INFO,
            "Wait time analysis completed",
            context={
                'provider_id': provider_id,
                'date': date,
                'average_wait_minutes': wait_time_analysis["statistics"]["average_wait_minutes"],
                'on_time_percentage': wait_time_analysis["statistics"]["on_time_percentage"]
            },
            operation_type='wait_time_analysis'
        )
        
        return wait_time_analysis
    
    @healthcare_log_method(logger)
    async def generate_capacity_report(self, date_range: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate capacity utilization report for scheduling optimization
        
        Args:
            date_range: Dictionary with 'start_date' and 'end_date'
            
        Returns:
            Dictionary with capacity analysis
        """
        # Mock capacity analysis (in production, use actual scheduling data)
        capacity_report = {
            "report_id": f"capacity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "date_range": date_range,
            "overall_utilization": {
                "total_slots": 450,
                "booked_slots": 378,
                "utilization_percentage": 84.0,
                "cancelled_slots": 23,
                "no_show_slots": 15
            },
            "provider_breakdown": [
                {"provider_id": "prov_001", "utilization": 89.5, "total_slots": 150},
                {"provider_id": "prov_002", "utilization": 82.1, "total_slots": 150},
                {"provider_id": "prov_003", "utilization": 80.8, "total_slots": 150}
            ],
            "appointment_type_analysis": {
                "routine_checkup": {"slots": 180, "utilization": 87.2},
                "consultation": {"slots": 120, "utilization": 79.5},
                "follow_up": {"slots": 90, "utilization": 88.9},
                "procedure": {"slots": 60, "utilization": 75.0}
            },
            "optimization_opportunities": [
                "Provider 3 has capacity for 20% more appointments",
                "Consultation slots underutilized - consider reducing allocation",
                "Routine checkups consistently overbooked - increase allocation"
            ],
            "generated_timestamp": datetime.now().isoformat()
        }
        
        log_healthcare_event(
            logger,
            logging.INFO,
            "Capacity report generated",
            context={
                'date_range': date_range,
                'overall_utilization': capacity_report["overall_utilization"]["utilization_percentage"],
                'total_slots': capacity_report["overall_utilization"]["total_slots"],
                'booked_slots': capacity_report["overall_utilization"]["booked_slots"]
            },
            operation_type='capacity_analysis'
        )
        
        return capacity_report


# Initialize the scheduling optimizer agent
scheduling_optimizer_agent = SchedulingOptimizerAgent()
