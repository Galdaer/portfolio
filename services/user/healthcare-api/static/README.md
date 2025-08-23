# Live Medical Transcription System

This system provides real-time medical transcription with automatic SOAP note generation for healthcare professionals.

## Features

### ✅ **Live Audio Transcription**
- Real-time transcription during doctor-patient sessions
- WebSocket-based streaming for low latency
- Medical terminology recognition and highlighting
- PHI detection and sanitization

### ✅ **Session Management** 
- Start/stop recording controls
- Session tracking with unique IDs
- Real-time statistics (duration, text length, chunks)
- Session persistence and retrieval

### ✅ **Automatic SOAP Note Generation**
- Auto-generates SOAP notes when sessions end
- Structured clinical documentation (Subjective, Objective, Assessment, Plan)
- Quality scoring and completeness assessment  
- Missing section identification and recommendations

### ✅ **PHI Compliance**
- Real-time PHI detection during transcription
- Automatic sanitization of sensitive information
- Healthcare-compliant logging and audit trails
- HIPAA-aligned data handling

## API Endpoints

### WebSocket Endpoints
- `ws://localhost:8000/ws/transcription/{doctor_id}` - Live transcription WebSocket

### REST Endpoints
- `GET /health` - Health check
- `POST /process` - General AI processing
- `POST /generate-soap-from-session` - Generate SOAP from completed session
- `GET /sessions/{session_id}` - Get session information
- `GET /static/live-transcription.html` - Demo UI

### SOAP Notes API
- `POST /soap-notes/generate-soap` - Generate SOAP note from text
- `POST /soap-notes/generate-progress` - Generate progress note
- `POST /soap-notes/session-to-soap` - Convert session to SOAP
- `GET /soap-notes/templates` - Get available note templates

## Usage

### 1. **Start the System**
```bash
cd /home/intelluxe/services/user/healthcare-api
python main.py
```

### 2. **Access Demo UI**
Open browser to: `http://localhost:8000/static/live-transcription.html`

### 3. **Start Live Transcription**
1. Enter Doctor ID
2. Click "Connect" to establish WebSocket connection
3. Click "Start Recording" to begin live transcription
4. Speak normally - transcription appears in real-time
5. Click "End Session" to stop and generate SOAP note

### 4. **WebSocket Message Format**

**Start Session:**
```javascript
// Automatic on connection - server sends:
{
  "type": "session_start",
  "session_id": "uuid",
  "doctor_id": "dr_demo",
  "message": "Live transcription session started"
}
```

**Send Audio Chunk:**
```javascript
// Client sends:
{
  "type": "audio_chunk",
  "audio_data": {
    "format": "webm",
    "data": "base64_audio_data",
    "duration": 2.0
  }
}

// Server responds:
{
  "type": "transcription_chunk", 
  "session_id": "uuid",
  "result": {
    "success": true,
    "transcription": "Patient reports feeling better today.",
    "confidence": 0.88,
    "medical_terms": ["patient"],
    "timestamp": "2025-01-23T10:30:00"
  }
}
```

**End Session:**
```javascript
// Client sends:
{
  "type": "end_session"
}

// Server responds:
{
  "type": "session_end",
  "session_id": "uuid",
  "summary": {
    "full_transcription": "...",
    "duration_minutes": 15.5,
    "chunk_count": 45
  },
  "soap_note": {
    "success": true,
    "note_id": "soap_20250123_103000",
    "soap_note": "SOAP NOTE\n========\n...",
    "completeness_score": 0.85
  }
}
```

### 5. **REST API Usage**

**Generate SOAP from Session:**
```bash
curl -X POST "http://localhost:8000/generate-soap-from-session" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "doctor_id": "dr_demo",
    "patient_id": "patient_123"
  }'
```

**Get Session Info:**
```bash
curl "http://localhost:8000/sessions/your-session-id"
```

## Architecture

### Component Integration
```
WebSocket Client (Browser)
     ↓ Audio Chunks
WebSocket Endpoint (/ws/transcription/{doctor_id})
     ↓ Process Audio
Transcription Agent (real-time processing)
     ↓ Store Chunks
Session Manager (in-memory storage)
     ↓ End Session
SOAP Notes Agent (document generation)
     ↓ Formatted Note
Client Response (SOAP note + metadata)
```

### Agent Workflow
1. **Live Transcription**: Real-time audio → text conversion
2. **Medical Processing**: Terminology recognition + PHI sanitization  
3. **Session Storage**: Chunk buffering + metadata tracking
4. **SOAP Generation**: Clinical note structuring + quality assessment
5. **Delivery**: Formatted documentation + recommendations

## Medical Disclaimer

⚠️ **IMPORTANT:** This system provides administrative transcription support only. It does not provide medical advice, diagnosis, or treatment recommendations. All clinical content must be reviewed and validated by qualified healthcare professionals.

## Security & Compliance

- **PHI Protection**: Real-time detection and sanitization
- **Audit Logging**: All interactions logged for compliance
- **Secure Sessions**: Session-based isolation and cleanup
- **HIPAA Alignment**: Healthcare-compliant data handling
- **No Persistence**: Audio data processed in memory only

## Development

The system is built with:
- **FastAPI** for REST and WebSocket APIs
- **Healthcare Agents** for specialized processing
- **PHI Monitor** for compliance validation
- **Session Management** for state tracking
- **Medical Terminology** processing and validation

For development details, see the individual agent documentation in `/agents/` directories.