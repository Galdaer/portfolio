"""
Medical Transcription Action for Open WebUI
Provides a simple button interface for live medical transcription with automatic SOAP note generation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import websockets
from pydantic import BaseModel
import sys
import os

# Add the healthcare-api config path for config loading
sys.path.append('/home/intelluxe/services/user/healthcare-api')
from config.ui_config_loader import UI_CONFIG


class Action:
    """
    Medical Transcription Action
    
    Adds a "🎙️ Start Medical Transcription" button to Open WebUI chat interface.
    When clicked, starts live transcription session and generates SOAP notes automatically.
    """
    
    class Valves(BaseModel):
        """Configuration for Medical Transcription Action - loaded from config files"""
        
        # Healthcare API Configuration - loaded from UI_CONFIG
        HEALTHCARE_API_URL: str = UI_CONFIG.api_integration.websocket_url
        HEALTHCARE_REST_URL: str = UI_CONFIG.api_integration.rest_api_url
        
        # Developer Configuration - loaded from UI_CONFIG  
        DEVELOPER_MODE: bool = UI_CONFIG.developer.mode_enabled
        DEVELOPER_USERS: list = UI_CONFIG.developer.test_users
        DEFAULT_TEST_USER: str = UI_CONFIG.developer.default_test_user
        DEBUG_LOGGING: bool = UI_CONFIG.developer.debug_logging
        MOCK_TRANSCRIPTION: bool = UI_CONFIG.developer.mock_transcription
        
        # Transcription Settings - loaded from UI_CONFIG
        TRANSCRIPTION_TIMEOUT: int = UI_CONFIG.session.timeout_seconds
        CHUNK_INTERVAL: int = UI_CONFIG.session.chunk_interval_seconds
        AUTO_SOAP_GENERATION: bool = UI_CONFIG.session.auto_soap_generation
        
        # Medical Disclaimer - loaded from UI_CONFIG
        MEDICAL_DISCLAIMER: str = UI_CONFIG.compliance.disclaimer_text

    def __init__(self):
        self.id = UI_CONFIG.action.id
        self.name = UI_CONFIG.action.name
        self.description = UI_CONFIG.action.description
        self.valves = self.Valves()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if self.valves.DEBUG_LOGGING:
            self.logger.setLevel(logging.DEBUG)

    async def action(
        self, 
        body: Dict[str, Any], 
        __user__: Optional[Dict] = None, 
        __event_emitter__=None
    ) -> Dict[str, Any]:
        """
        Main action function - called when user clicks transcription button
        """
        try:
            # Extract user information
            user_id = self.extract_user_id(__user__, body)
            
            # Developer mode handling
            if self.valves.DEVELOPER_MODE:
                user_id = self.handle_developer_mode(user_id)
                
            doctor_id = f"dr_{user_id}"
            
            # Log session start
            await self.emit_status(
                f"🎙️ Starting medical transcription session for {user_id}",
                __event_emitter__, 
                {"user_id": user_id, "doctor_id": doctor_id}
            )
            
            # Show medical disclaimer
            await self.emit_status(
                self.valves.MEDICAL_DISCLAIMER,
                __event_emitter__,
                {"type": "disclaimer"}
            )
            
            # Start transcription session
            session_result = await self.start_transcription_session(
                doctor_id, user_id, __event_emitter__
            )
            
            if session_result["success"]:
                return {
                    "success": True,
                    "message": "✅ Medical transcription completed successfully",
                    "data": {
                        "session_id": session_result["session_id"],
                        "transcription": session_result["transcription"],
                        "soap_note": session_result.get("soap_note"),
                        "user_id": user_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Transcription failed: {session_result.get('error', 'Unknown error')}",
                    "error": session_result.get("error")
                }
                
        except Exception as e:
            self.logger.error(f"Medical transcription action failed: {e}")
            return {
                "success": False,
                "message": f"❌ System error: {str(e)}",
                "error": str(e)
            }

    def extract_user_id(self, __user__: Optional[Dict], body: Dict[str, Any]) -> Optional[str]:
        """Extract user ID from various possible sources"""
        
        user_candidates = []
        
        # Try user object attributes
        if __user__:
            if isinstance(__user__, dict):
                user_candidates.extend([
                    __user__.get('id'),
                    __user__.get('username'), 
                    __user__.get('email'),
                    __user__.get('name')
                ])
            else:
                # Try object attributes
                for attr in ['id', 'username', 'email', 'name']:
                    if hasattr(__user__, attr):
                        user_candidates.append(getattr(__user__, attr))
        
        # Try body user information
        if 'user' in body:
            user_info = body['user']
            if isinstance(user_info, dict):
                user_candidates.extend([
                    user_info.get('id'),
                    user_info.get('username'),
                    user_info.get('email'),
                    user_info.get('name')
                ])
        
        # Return first valid candidate
        for candidate in user_candidates:
            if candidate and str(candidate).strip() and candidate != 'unknown':
                return str(candidate).lower()
        
        return None

    def handle_developer_mode(self, user_id: Optional[str]) -> str:
        """Handle developer mode user identification"""
        
        if not user_id or user_id == 'unknown':
            user_id = self.valves.DEFAULT_TEST_USER
            self.logger.info(f"Developer mode: Using default test user '{user_id}'")
        
        # Validate developer users
        if user_id in self.valves.DEVELOPER_USERS:
            self.logger.info(f"Developer mode: Confirmed developer user '{user_id}'")
            return user_id
        else:
            # Check if it's a partial match
            for dev_user in self.valves.DEVELOPER_USERS:
                if dev_user in user_id or user_id in dev_user:
                    self.logger.info(f"Developer mode: Matched '{user_id}' to '{dev_user}'")
                    return dev_user
            
            # Default to primary test user
            self.logger.warning(f"Developer mode: Unknown user '{user_id}', using default '{self.valves.DEFAULT_TEST_USER}'")
            return self.valves.DEFAULT_TEST_USER

    async def start_transcription_session(
        self, 
        doctor_id: str, 
        user_id: str,
        __event_emitter__
    ) -> Dict[str, Any]:
        """Start WebSocket transcription session with healthcare API"""
        
        try:
            # Mock transcription for testing
            if self.valves.MOCK_TRANSCRIPTION:
                return await self.mock_transcription_session(doctor_id, user_id, __event_emitter__)
            
            # Real WebSocket connection
            ws_url = f"{self.valves.HEALTHCARE_API_URL}/ws/transcription/{doctor_id}"
            
            await self.emit_status(
                f"🔗 Connecting to healthcare transcription service...",
                __event_emitter__
            )
            
            session_data = {
                "session_id": None,
                "transcription_chunks": [],
                "full_transcription": "",
                "soap_note": None
            }
            
            # Connect to WebSocket
            try:
                async with websockets.connect(ws_url) as websocket:
                    
                    # Wait for session start message
                    initial_message = await websocket.recv()
                    session_start = json.loads(initial_message)
                    
                    if session_start.get("type") == "session_start":
                        session_data["session_id"] = session_start.get("session_id")
                        
                        await self.emit_status(
                            f"✅ Connected! Session ID: {session_data['session_id']}",
                            __event_emitter__,
                            {"session_id": session_data["session_id"]}
                        )
                        
                        # Simulate transcription session
                        await self.simulate_transcription_session(
                            websocket, session_data, __event_emitter__
                        )
                        
                        # End session and get SOAP note
                        await websocket.send(json.dumps({"type": "end_session"}))
                        
                        # Wait for session end response
                        end_message = await websocket.recv()
                        session_end = json.loads(end_message)
                        
                        if session_end.get("type") == "session_end":
                            session_data["soap_note"] = session_end.get("soap_note")
                            
                            await self.emit_status(
                                "📋 SOAP note generated successfully!",
                                __event_emitter__,
                                {"soap_generated": True}
                            )
            
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
            except Exception as ws_error:
                self.logger.error(f"WebSocket error: {ws_error}")
                return {
                    "success": False,
                    "error": f"Connection failed: {str(ws_error)}"
                }
            
            return {
                "success": True,
                "session_id": session_data["session_id"],
                "transcription": session_data["full_transcription"],
                "soap_note": session_data.get("soap_note")
            }
            
        except Exception as e:
            self.logger.error(f"Transcription session failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def simulate_transcription_session(
        self, 
        websocket, 
        session_data: Dict,
        __event_emitter__
    ):
        """Simulate a medical transcription session with audio chunks"""
        
        # Mock medical transcription chunks
        mock_transcription_chunks = [
            "Patient presents with chief complaint of fatigue lasting two weeks.",
            "History of present illness: 45-year-old female reports increasing fatigue.",
            "Physical examination: Blood pressure 140 over 85, heart rate 78 and regular.",
            "Patient appears tired but alert and oriented.",
            "Cardiovascular examination shows regular rate and rhythm.",
            "Assessment: Hypertension, newly diagnosed. Fatigue likely related to blood pressure elevation.",
            "Plan: Start lisinopril 10 milligrams daily. Patient education provided.",
            "Follow-up in two weeks to assess response to treatment."
        ]
        
        await self.emit_status(
            "🎙️ Recording... (Simulated medical encounter)",
            __event_emitter__,
            {"recording": True}
        )
        
        for i, chunk in enumerate(mock_transcription_chunks):
            # Send mock audio chunk
            audio_message = {
                "type": "audio_chunk",
                "audio_data": {
                    "format": "webm",
                    "data": f"mock_audio_chunk_{i}",
                    "duration": 2.0
                }
            }
            
            await websocket.send(json.dumps(audio_message))
            
            # Wait for transcription response
            response = await websocket.recv()
            transcription_result = json.loads(response)
            
            if transcription_result.get("type") == "transcription_chunk":
                result = transcription_result.get("result", {})
                if result.get("success"):
                    transcription_text = result.get("transcription", chunk)
                    session_data["transcription_chunks"].append(transcription_text)
                    session_data["full_transcription"] += transcription_text + " "
                    
                    # Show real-time transcription
                    await self.emit_status(
                        f"📝 {transcription_text}",
                        __event_emitter__,
                        {"transcription_chunk": transcription_text, "chunk_index": i}
                    )
            
            # Simulate natural speaking pace
            await asyncio.sleep(1.5)

    async def mock_transcription_session(
        self, 
        doctor_id: str, 
        user_id: str,
        __event_emitter__
    ) -> Dict[str, Any]:
        """Mock transcription session for testing without WebSocket"""
        
        await self.emit_status(
            "🧪 Mock transcription mode (for testing)",
            __event_emitter__,
            {"mock_mode": True}
        )
        
        # Simulate connection delay
        await asyncio.sleep(1)
        
        session_id = f"mock_session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Mock transcription content
        mock_transcription = (
            "Chief complaint: Patient presents with fatigue and headaches for the past two weeks. "
            "Physical examination: Blood pressure 140 over 85. Heart rate 78 and regular. "
            "Assessment: Hypertension, newly diagnosed. Fatigue likely related to blood pressure elevation. "
            "Plan: Start lisinopril 10 milligrams daily. Follow-up in two weeks."
        )
        
        # Mock SOAP note
        mock_soap_note = """
SOAP NOTE
=========

SUBJECTIVE:
Chief Complaint: Patient presents with fatigue and headaches for the past two weeks.
History of Present Illness: 45-year-old female reports increasing fatigue and intermittent headaches.

OBJECTIVE:
Physical Examination: Blood pressure 140 over 85. Heart rate 78 and regular. Patient appears tired but alert.

ASSESSMENT:
Hypertension, newly diagnosed. Fatigue likely related to blood pressure elevation.

PLAN:
Start lisinopril 10 milligrams daily. Patient education provided. Follow-up in two weeks.

---
Generated by Medical Transcription System
Quality Score: 0.92
"""
        
        await self.emit_status(
            f"📝 Transcription: {mock_transcription[:100]}...",
            __event_emitter__,
            {"transcription_preview": True}
        )
        
        await asyncio.sleep(2)
        
        await self.emit_status(
            "📋 Generating SOAP note...",
            __event_emitter__,
            {"generating_soap": True}
        )
        
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "session_id": session_id,
            "transcription": mock_transcription,
            "soap_note": mock_soap_note
        }

    async def emit_status(
        self, 
        message: str, 
        __event_emitter__, 
        data: Dict[str, Any] = None
    ):
        """Emit status message to Open WebUI interface"""
        
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    **(data or {})
                }
            })
            
        if self.valves.DEBUG_LOGGING:
            self.logger.info(f"Status: {message}")

    def get_action_metadata(self) -> Dict[str, Any]:
        """Return metadata about this action for Open WebUI"""
        
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": UI_CONFIG.action.icon,
            "category": UI_CONFIG.action.category,
            "developer_mode": self.valves.DEVELOPER_MODE,
            "supported_users": self.valves.DEVELOPER_USERS if self.valves.DEVELOPER_MODE else "all",
            "healthcare_compliance": UI_CONFIG.compliance.healthcare_compliance_mode,
            "phi_protection": UI_CONFIG.compliance.phi_protection_enabled
        }