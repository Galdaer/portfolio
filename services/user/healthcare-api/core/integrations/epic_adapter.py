"""
Epic MyChart Integration Adapter
Provides integration with Epic MyChart for scheduling and patient data
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx

from core.database.secure_db_manager import DatabaseType, get_db_manager
from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.infrastructure.phi_detector import PHIDetector


class EpicEnvironment(Enum):
    """Epic environment types"""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class EpicAuthMethod(Enum):
    """Epic authentication methods"""
    OAUTH2 = "oauth2"
    BACKEND_OAUTH2 = "backend_oauth2"
    SMART_ON_FHIR = "smart_on_fhir"


class EpicMyChartAdapter:
    """
    Adapter for Epic MyChart integration
    Implements FHIR R4 standard for Epic interoperability
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize Epic MyChart adapter

        Args:
            config: Integration configuration including:
                - client_id: Epic client ID
                - client_secret: Epic client secret (encrypted)
                - base_url: Epic FHIR base URL
                - environment: sandbox or production
                - auth_method: Authentication method to use
        """
        self.logger = get_healthcare_logger("integration.epic")
        self.phi_detector = PHIDetector()

        # Configuration
        self.config = config
        self.client_id = config.get("client_id")
        self.base_url = config.get("base_url", "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4")
        self.environment = EpicEnvironment(config.get("environment", "sandbox"))
        self.auth_method = EpicAuthMethod(config.get("auth_method", "backend_oauth2"))

        # HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            },
        )

        # Authentication
        self.access_token = None
        self.token_expiry = None

        # Database manager
        self.db_manager = None

    async def initialize(self):
        """Initialize the adapter"""
        self.db_manager = await get_db_manager()
        await self.authenticate()

    async def authenticate(self):
        """Authenticate with Epic using configured method"""
        try:
            if self.auth_method == EpicAuthMethod.BACKEND_OAUTH2:
                await self._backend_oauth_auth()
            elif self.auth_method == EpicAuthMethod.OAUTH2:
                await self._standard_oauth_auth()
            elif self.auth_method == EpicAuthMethod.SMART_ON_FHIR:
                await self._smart_on_fhir_auth()
            else:
                msg = f"Unsupported auth method: {self.auth_method}"
                raise ValueError(msg)

            self.logger.info(f"Successfully authenticated with Epic ({self.environment.value})")

        except Exception as e:
            self.logger.exception(f"Epic authentication failed: {e}")
            raise

    async def _backend_oauth_auth(self):
        """Backend OAuth 2.0 authentication (for system-to-system)"""
        # Get client secret from secure storage
        client_secret = await self._get_client_secret()

        auth_url = f"{self.base_url}/../oauth2/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": client_secret,
            "scope": "system/*.read system/*.write",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(auth_url, data=data)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

    async def _standard_oauth_auth(self):
        """Standard OAuth 2.0 authentication"""
        # Implementation for standard OAuth flow
        # This would typically involve user interaction
        raise NotImplementedError("Standard OAuth requires user interaction")

    async def _smart_on_fhir_auth(self):
        """SMART on FHIR authentication"""
        # Implementation for SMART on FHIR
        # This involves additional SMART launch parameters
        raise NotImplementedError("SMART on FHIR authentication not yet implemented")

    async def _get_client_secret(self) -> str:
        """Retrieve and decrypt client secret from secure storage"""
        # In production, this would retrieve from secure key vault
        # For now, get from environment variable
        import os
        return os.getenv("EPIC_CLIENT_SECRET", "")

    async def _ensure_authenticated(self):
        """Ensure we have a valid authentication token"""
        if not self.access_token or datetime.utcnow() >= self.token_expiry:
            await self.authenticate()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] = None,
        params: dict[str, str] = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to Epic FHIR API

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters

        Returns:
            Response data
        """
        await self._ensure_authenticated()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        response = await self.client.request(
            method=method,
            url=endpoint,
            json=data,
            params=params,
            headers=headers,
        )

        response.raise_for_status()
        return response.json()

    # ============================================
    # SCHEDULING OPERATIONS
    # ============================================

    async def search_slots(
        self,
        practitioner_id: str = None,
        location_id: str = None,
        service_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        status: str = "free",
    ) -> list[dict[str, Any]]:
        """
        Search for available appointment slots

        Args:
            practitioner_id: Epic practitioner ID
            location_id: Epic location ID
            service_type: Type of service
            start_date: Start of search period
            end_date: End of search period
            status: Slot status (free, busy, busy-tentative)

        Returns:
            List of available slots
        """
        try:
            params = {
                "status": status,
                "_include": "Slot:schedule",
            }

            if practitioner_id:
                params["schedule.actor"] = f"Practitioner/{practitioner_id}"
            if location_id:
                params["schedule.actor"] = f"Location/{location_id}"
            if service_type:
                params["service-type"] = service_type
            if start_date:
                params["start"] = f"ge{start_date.isoformat()}"
            if end_date:
                params["start"] = f"le{end_date.isoformat()}"

            response = await self._make_request(
                "GET",
                "/Slot",
                params=params,
            )

            slots = []
            for entry in response.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Slot":
                    slots.append(self._parse_slot(resource))

            self.logger.info(f"Found {len(slots)} available slots")
            return slots

        except Exception as e:
            self.logger.exception(f"Failed to search slots: {e}")
            raise

    def _parse_slot(self, slot_resource: dict[str, Any]) -> dict[str, Any]:
        """Parse Epic Slot resource into internal format"""
        return {
            "slot_id": slot_resource.get("id"),
            "status": slot_resource.get("status"),
            "start": slot_resource.get("start"),
            "end": slot_resource.get("end"),
            "duration_minutes": self._calculate_duration(
                slot_resource.get("start"),
                slot_resource.get("end"),
            ),
            "service_type": slot_resource.get("serviceType", []),
            "schedule_reference": slot_resource.get("schedule", {}).get("reference"),
            "comment": slot_resource.get("comment"),
            "source": "epic",
        }

    def _calculate_duration(self, start: str, end: str) -> int:
        """Calculate duration in minutes between two timestamps"""
        if not start or not end:
            return 0
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return int((end_dt - start_dt).total_seconds() / 60)
        except:
            return 0

    async def book_appointment(
        self,
        patient_id: str,
        slot_id: str,
        appointment_type: str,
        reason: str = None,
        comment: str = None,
    ) -> dict[str, Any]:
        """
        Book an appointment in Epic

        Args:
            patient_id: Epic patient ID
            slot_id: Epic slot ID
            appointment_type: Type of appointment
            reason: Reason for appointment
            comment: Additional comments

        Returns:
            Created appointment details
        """
        try:
            # Create FHIR Appointment resource
            appointment = {
                "resourceType": "Appointment",
                "status": "booked",
                "slot": [{
                    "reference": f"Slot/{slot_id}",
                }],
                "participant": [{
                    "actor": {
                        "reference": f"Patient/{patient_id}",
                    },
                    "required": "required",
                    "status": "accepted",
                }],
                "appointmentType": {
                    "text": appointment_type,
                },
            }

            if reason:
                appointment["reasonCode"] = [{
                    "text": reason,
                }]
            if comment:
                appointment["comment"] = comment

            response = await self._make_request(
                "POST",
                "/Appointment",
                data=appointment,
            )

            # Store in local database (private - contains PHI)
            await self._store_appointment_locally(response, patient_id)

            self.logger.info(f"Successfully booked appointment: {response.get('id')}")
            return self._parse_appointment(response)

        except Exception as e:
            self.logger.exception(f"Failed to book appointment: {e}")
            raise

    async def _store_appointment_locally(
        self,
        appointment: dict[str, Any],
        patient_id: str,
    ):
        """Store appointment in local private database"""
        try:
            # Extract appointment details
            epic_id = appointment.get("id")
            start = appointment.get("start")
            end = appointment.get("end")
            status = appointment.get("status")

            # Store in private database (contains PHI)
            await self.db_manager.execute(
                """
                INSERT INTO appointments (
                    external_id, external_system, patient_id,
                    start_time, end_time, status,
                    raw_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (external_id, external_system)
                DO UPDATE SET
                    status = $6,
                    raw_data = $7,
                    updated_at = CURRENT_TIMESTAMP
                """,
                epic_id, "epic", patient_id,
                start, end, status,
                json.dumps(appointment), datetime.utcnow(),
                database=DatabaseType.PRIVATE,
                user_id="system",
            )

        except Exception as e:
            self.logger.exception(f"Failed to store appointment locally: {e}")
            # Don't raise - local storage failure shouldn't break booking

    def _parse_appointment(self, appointment_resource: dict[str, Any]) -> dict[str, Any]:
        """Parse Epic Appointment resource into internal format"""
        return {
            "appointment_id": appointment_resource.get("id"),
            "status": appointment_resource.get("status"),
            "start": appointment_resource.get("start"),
            "end": appointment_resource.get("end"),
            "duration_minutes": self._calculate_duration(
                appointment_resource.get("start"),
                appointment_resource.get("end"),
            ),
            "appointment_type": appointment_resource.get("appointmentType", {}).get("text"),
            "participants": self._parse_participants(
                appointment_resource.get("participant", []),
            ),
            "comment": appointment_resource.get("comment"),
            "source": "epic",
        }

    def _parse_participants(self, participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse appointment participants"""
        parsed = []
        for participant in participants:
            parsed.append({
                "reference": participant.get("actor", {}).get("reference"),
                "status": participant.get("status"),
                "required": participant.get("required"),
            })
        return parsed

    async def cancel_appointment(
        self,
        appointment_id: str,
        cancellation_reason: str,
    ) -> dict[str, Any]:
        """
        Cancel an appointment in Epic

        Args:
            appointment_id: Epic appointment ID
            cancellation_reason: Reason for cancellation

        Returns:
            Updated appointment details
        """
        try:
            # Update appointment status to cancelled
            update_data = {
                "resourceType": "Appointment",
                "id": appointment_id,
                "status": "cancelled",
                "cancelationReason": {
                    "text": cancellation_reason,
                },
            }

            response = await self._make_request(
                "PUT",
                f"/Appointment/{appointment_id}",
                data=update_data,
            )

            # Update local database
            await self.db_manager.execute(
                """
                UPDATE appointments
                SET status = 'cancelled',
                    cancellation_reason = $1,
                    cancelled_at = $2,
                    updated_at = CURRENT_TIMESTAMP
                WHERE external_id = $3 AND external_system = 'epic'
                """,
                cancellation_reason, datetime.utcnow(), appointment_id,
                database=DatabaseType.PRIVATE,
                user_id="system",
            )

            self.logger.info(f"Successfully cancelled appointment: {appointment_id}")
            return self._parse_appointment(response)

        except Exception as e:
            self.logger.exception(f"Failed to cancel appointment: {e}")
            raise

    async def get_practitioner_schedule(
        self,
        practitioner_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """
        Get practitioner's schedule from Epic

        Args:
            practitioner_id: Epic practitioner ID
            start_date: Start date
            end_date: End date

        Returns:
            List of schedule entries
        """
        try:
            params = {
                "actor": f"Practitioner/{practitioner_id}",
                "date": f"ge{start_date.isoformat()}",
                "date": f"le{end_date.isoformat()}",
            }

            response = await self._make_request(
                "GET",
                "/Schedule",
                params=params,
            )

            schedules = []
            for entry in response.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Schedule":
                    schedules.append(self._parse_schedule(resource))

            return schedules

        except Exception as e:
            self.logger.exception(f"Failed to get practitioner schedule: {e}")
            raise

    def _parse_schedule(self, schedule_resource: dict[str, Any]) -> dict[str, Any]:
        """Parse Epic Schedule resource"""
        return {
            "schedule_id": schedule_resource.get("id"),
            "active": schedule_resource.get("active", True),
            "service_category": schedule_resource.get("serviceCategory", []),
            "service_type": schedule_resource.get("serviceType", []),
            "actor": schedule_resource.get("actor", []),
            "planning_horizon": schedule_resource.get("planningHorizon", {}),
            "comment": schedule_resource.get("comment"),
            "source": "epic",
        }

    async def sync_appointments(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> dict[str, Any]:
        """
        Sync appointments from Epic to local database

        Args:
            start_date: Start of sync period
            end_date: End of sync period

        Returns:
            Sync statistics
        """
        try:
            if not start_date:
                start_date = datetime.utcnow()
            if not end_date:
                end_date = start_date + timedelta(days=30)

            params = {
                "date": f"ge{start_date.isoformat()}",
                "date": f"le{end_date.isoformat()}",
                "_count": "100",
            }

            response = await self._make_request(
                "GET",
                "/Appointment",
                params=params,
            )

            stats = {
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 0,
            }

            for entry in response.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Appointment":
                    stats["total"] += 1
                    try:
                        # Store appointment (contains PHI - goes to private DB)
                        await self._store_appointment_locally(
                            resource,
                            self._extract_patient_id(resource),
                        )
                        stats["created"] += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to sync appointment: {e}")
                        stats["errors"] += 1

            # Log sync results
            await self.db_manager.execute(
                """
                INSERT INTO integration_sync_logs (
                    config_id, sync_type, sync_started_at, sync_completed_at,
                    records_processed, records_created, records_updated,
                    records_failed, sync_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                self.config.get("config_id"), "incremental",
                start_date, datetime.utcnow(),
                stats["total"], stats["created"], stats["updated"],
                stats["errors"], "completed",
                database=DatabaseType.PUBLIC,
                user_id="system",
            )

            self.logger.info(f"Appointment sync complete: {stats}")
            return stats

        except Exception as e:
            self.logger.exception(f"Failed to sync appointments: {e}")
            raise

    def _extract_patient_id(self, appointment: dict[str, Any]) -> str:
        """Extract patient ID from appointment resource"""
        for participant in appointment.get("participant", []):
            actor_ref = participant.get("actor", {}).get("reference", "")
            if actor_ref.startswith("Patient/"):
                return actor_ref.replace("Patient/", "")
        return None

    async def close(self):
        """Close the adapter and clean up resources"""
        if self.client:
            await self.client.aclose()

    async def test_connection(self) -> bool:
        """Test connection to Epic"""
        try:
            await self.authenticate()
            # Try to fetch metadata
            response = await self._make_request("GET", "/metadata")
            return response.get("resourceType") == "CapabilityStatement"
        except Exception as e:
            self.logger.exception(f"Connection test failed: {e}")
            return False
