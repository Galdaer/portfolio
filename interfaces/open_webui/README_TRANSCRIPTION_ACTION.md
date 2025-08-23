# Medical Transcription Action for Open WebUI

## 🎙️ Overview

This Open WebUI Action provides a simple "Start Medical Transcription" button that appears next to chat messages, enabling doctors to start live transcription sessions with automatic SOAP note generation directly within their chat interface.

## ✨ Features

### **User-Friendly Interface**
- **One-Click Start**: Simple button in chat interface
- **Real-Time Display**: Transcription appears as it happens
- **Auto SOAP Notes**: Generates structured clinical documentation
- **Chat Integration**: Everything stays within the familiar chat workflow

### **Developer Support**
- **Multi-User Testing**: Configured for `justin` and `jeff` developer accounts
- **Mock Mode**: Testing without real audio hardware
- **Debug Logging**: Comprehensive testing and troubleshooting
- **Flexible Configuration**: Easy to adjust settings

### **Healthcare Compliance**
- **Medical Disclaimers**: Clear administrative-only boundaries
- **PHI Protection**: Secure handling of medical information
- **Audit Trails**: All sessions logged for compliance
- **Professional Standards**: Follows medical documentation best practices

## 🚀 Installation

### **Step 1: Install the Action File**

Copy the action to your Open WebUI functions directory:

```bash
# Copy the action function
cp /home/intelluxe/interfaces/open_webui/medical_transcription_action.py \
   /path/to/your/openwebui/functions/

# Optional: Copy test file for validation
cp /home/intelluxe/interfaces/open_webui/test_transcription_action.py \
   /path/to/your/openwebui/functions/
```

### **Step 2: Start Healthcare API Server**

The transcription action connects to your healthcare API backend:

```bash
cd /home/intelluxe/services/user/healthcare-api
python main.py
```

This starts the WebSocket server at `ws://localhost:8000/ws/transcription/{doctor_id}`

### **Step 3: Enable in Open WebUI**

1. Open your Open WebUI interface
2. Go to **Workspace → Functions**
3. Find "🎙️ Medical Transcription" in the list
4. Click **Enable** to activate the function
5. Assign to specific models or enable globally

### **Step 4: Test the Installation**

Run the test script to validate everything works:

```bash
python3 /home/intelluxe/interfaces/open_webui/test_transcription_action.py
```

Expected output:
- ✅ Configuration tests pass
- ✅ User detection works for `justin` and `jeff`
- ✅ Mock transcription generates SOAP notes
- ⚠️ WebSocket test may fail if healthcare-api not running

## 👥 Developer Configuration

The action is preconfigured for two developer users:

### **Justin (Primary Test User)**
- **Username**: `justin`
- **Doctor ID**: `dr_justin`
- **WebSocket**: `ws://localhost:8000/ws/transcription/dr_justin`
- **Default User**: Falls back to justin if user not detected

### **Jeff (Secondary Test User)**
- **Username**: `jeff`  
- **Doctor ID**: `dr_jeff`
- **WebSocket**: `ws://localhost:8000/ws/transcription/dr_jeff`
- **Testing**: Perfect for concurrent session testing

## 🎯 Usage

### **Starting a Transcription Session**

1. **Open Chat**: Start any conversation in Open WebUI
2. **Find Button**: Look for "🎙️ Start Medical Transcription" button
3. **Click Button**: Action starts immediately
4. **Medical Disclaimer**: System shows compliance warning
5. **Recording**: Real-time transcription begins
6. **SOAP Generation**: Automatic clinical note creation
7. **Results**: Formatted SOAP note appears in chat

### **Example User Flow**

```
Doctor (justin) in chat session:
[💬 Send] [🎙️ Start Medical Transcription] [⚡ Other Actions]

↓ Click transcription button

🎙️ Starting medical transcription session for justin
⚠️ Medical disclaimer displayed
🔗 Connecting to healthcare transcription service...
✅ Connected! Session ID: dr_justin_20250123_143022

📝 Patient reports feeling better today...
📝 Blood pressure reading is normal...
📝 Examination shows improvement in symptoms...

📋 Generating SOAP note...
✅ Medical transcription completed successfully

SOAP NOTE
=========
SUBJECTIVE: Patient reports feeling better today...
OBJECTIVE: Blood pressure reading is normal...
ASSESSMENT: Patient shows improvement in symptoms...
PLAN: Continue current treatment regimen...
```

## ⚙️ Configuration Options

### **Developer Mode Settings**

```python
class Valves(BaseModel):
    # Developer Configuration  
    DEVELOPER_MODE: bool = True
    DEVELOPER_USERS: list = ["justin", "jeff"]
    DEFAULT_TEST_USER: str = "justin"
    DEBUG_LOGGING: bool = True
    MOCK_TRANSCRIPTION: bool = False
```

### **Production Settings**

For production deployment:

```python
class Valves(BaseModel):
    DEVELOPER_MODE: bool = False
    DEBUG_LOGGING: bool = False
    MOCK_TRANSCRIPTION: bool = False
```

### **Healthcare API Settings**

```python
class Valves(BaseModel):
    HEALTHCARE_API_URL: str = "ws://localhost:8000"
    HEALTHCARE_REST_URL: str = "http://localhost:8000"
    TRANSCRIPTION_TIMEOUT: int = 300  # 5 minutes
    AUTO_SOAP_GENERATION: bool = True
```

## 🧪 Testing

### **Test Scenarios**

The action includes comprehensive testing:

```bash
# Run all tests
python3 test_transcription_action.py

# Test specific functionality
pytest test_transcription_action.py::test_user_detection
pytest test_transcription_action.py::test_mock_transcription
```

### **User Detection Tests**
- ✅ Justin user identification
- ✅ Jeff user identification  
- ✅ Fallback to default user
- ✅ Developer mode handling

### **Mock Transcription Tests**
- ✅ Session creation and management
- ✅ Real-time transcription simulation
- ✅ SOAP note generation
- ✅ Event emission and status updates

### **Integration Tests**
- ✅ WebSocket connection testing
- ✅ Healthcare API integration
- ✅ Error handling and fallbacks

## 🔒 Security & Compliance

### **Medical Compliance**
- **Administrative Only**: Clear disclaimers about medical advice boundaries
- **PHI Protection**: Secure handling of patient information
- **Audit Logging**: All sessions tracked for compliance
- **Professional Review**: All generated notes require professional validation

### **User Authentication**
- **User Identification**: Secure user ID extraction from Open WebUI
- **Session Isolation**: Each user gets isolated transcription sessions
- **Access Controls**: Developer mode restricts to approved users

### **Data Security**
- **Memory Processing**: Audio processed in memory only
- **Session Cleanup**: Automatic cleanup of transcription data
- **Secure Connections**: WebSocket connections over local network
- **No Persistence**: Audio data not stored permanently

## 🐛 Troubleshooting

### **Common Issues**

#### **"Connection Failed" Error**
```
❌ Transcription failed: Connection failed: [connection error]
```
**Solution**: Ensure healthcare-api server is running:
```bash
cd /home/intelluxe/services/user/healthcare-api
python main.py
```

#### **"User Not Detected" Issue**
```
Using default test user 'justin'
```
**Solution**: This is normal in developer mode. The system falls back to justin for testing.

#### **WebSocket Timeout**
```
WebSocket connection timeout
```
**Solution**: Check healthcare-api server health:
```bash
curl http://localhost:8000/health
```

### **Debug Mode**

Enable detailed logging:

```python
self.valves.DEBUG_LOGGING = True
self.valves.MOCK_TRANSCRIPTION = True  # For testing without real connections
```

### **Health Checks**

Verify system components:

```bash
# Test healthcare API
curl http://localhost:8000/health

# Test WebSocket endpoint
wscat -c ws://localhost:8000/ws/transcription/dr_justin

# Test action function
python3 test_transcription_action.py
```

## 📚 API Reference

### **Action Method Signature**

```python
async def action(
    self, 
    body: Dict[str, Any], 
    __user__: Optional[Dict] = None, 
    __event_emitter__=None
) -> Dict[str, Any]
```

### **Return Format**

```python
{
    "success": True,
    "message": "✅ Medical transcription completed successfully",
    "data": {
        "session_id": "dr_justin_20250123_143022",
        "transcription": "Patient reports...",
        "soap_note": "SOAP NOTE\n=========\n...",
        "user_id": "justin",
        "timestamp": "2025-01-23T14:30:22"
    }
}
```

### **Event Emitter Messages**

```python
# Status updates
{"type": "status", "data": {"message": "🎙️ Starting transcription..."}}

# Real-time transcription
{"type": "status", "data": {"transcription_chunk": "Patient reports...", "chunk_index": 1}}

# SOAP generation
{"type": "status", "data": {"generating_soap": True}}
```

## 🎉 Success!

Your Open WebUI now has a user-friendly medical transcription button that makes live clinical documentation as easy as sending a chat message!

**Next Steps:**
1. Test with both `justin` and `jeff` accounts
2. Try real transcription sessions with the healthcare-api running
3. Customize the configuration for your specific needs
4. Deploy to production with appropriate security settings