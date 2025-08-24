# Open WebUI Function Import Guide (Research-Based Solution)

Based on extensive research of official documentation, GitHub discussions, and community sources, this guide provides the **correct** way to import functions into Open WebUI.

## 🔍 Key Research Findings

### **The Real Issue**
- Open WebUI functions are **Python files**, not JSON by default
- JSON format is for **export/sharing between instances**, not primary import method
- Functions **MUST be imported through the UI**, not by placing files in directories
- External dependencies cause import failures - functions must be self-contained

### **Python vs JSON Confusion Solved**
- ✅ **Functions are written in Python** with specific class structures  
- ✅ **JSON is for export/import between Open WebUI instances**
- ❌ **Don't place .py files in Docker volumes** - this doesn't work
- ✅ **Import Python code directly through the UI**

## 📁 Corrected Function Files

Your healthcare functions have been rewritten to follow proper Open WebUI conventions:

### **Ready-to-Import Python Functions**
- `test_action_simple.py` - 🧪 Minimal test function to verify import process
- `healthcare_config_manager_corrected.py` - ⚙️ Healthcare Configuration Manager  
- `medical_transcription_action_corrected.py` - 🎙️ Medical Transcription Action

### **Key Fixes Applied**
- ✅ Removed `sys.path.append()` statements (not allowed in Open WebUI)
- ✅ Replaced external config imports with environment variables
- ✅ Added proper metadata headers (title, author, version)
- ✅ Used correct Action class structure with Pydantic Valves
- ✅ Added fallback configurations for missing dependencies
- ✅ Included mock modes for testing

## 🚀 Correct Import Process

### **Method 1: Copy-Paste Python Code (Recommended)**

1. **Open Open WebUI**
2. **Navigate to Workspace → Functions**
3. **Click "Import Functions" or "+ Add Function"**
4. **Select "Create New Function"** (not import from file)
5. **Copy the entire Python code** from one of the corrected files
6. **Paste into the code editor**
7. **Click "Save"**

### **Method 2: Upload Python File**

1. **Go to Workspace → Functions**
2. **Click "Import Functions"**
3. **Choose "Upload File"**
4. **Select a `.py` file** (e.g., `test_action_simple.py`)
5. **Click "Import"**

## ✅ Step-by-Step Testing Process

### **Start with Simple Test Function**

1. **Import `test_action_simple.py` first** to verify the process works
2. **Enable the function** after import (toggle it ON)
3. **Test it** by clicking the action button in a chat
4. **Verify you see**: "Test Action Executed Successfully!"

### **Import Healthcare Functions**

Once the test works:

1. **Import `healthcare_config_manager_corrected.py`**
2. **Import `medical_transcription_action_corrected.py`**
3. **Enable both functions**
4. **Configure through Valves** (function settings)

## ⚙️ Configuration Through Valves

### **Access Function Settings**
1. **Go to Workspace → Functions**
2. **Click the ⚙️ (Settings) icon** next to each function
3. **Modify the Valves** (configuration options)
4. **Click Save**

### **Key Settings to Configure**

#### Healthcare Config Manager:
- `healthcare_websocket_url`: Your API WebSocket URL
- `admin_users`: Add your username to the list
- `developer_mode`: Enable for additional features

#### Medical Transcription:
- `healthcare_websocket_url`: Your API WebSocket URL  
- `mock_transcription_enabled`: Enable for testing
- `developer_mode`: Enable if you're a developer user
- `show_medical_disclaimer`: Keep enabled for compliance

## 🧪 Testing Your Functions

### **Healthcare Config Manager Test**
1. **Enable the function**
2. **Click the function button** in a chat
3. **Expected result**: Configuration summary display
4. **If "Access Denied"**: Add your username to `admin_users` in Valves

### **Medical Transcription Test**
1. **Enable the function**
2. **Set `mock_transcription_enabled = true`** in Valves  
3. **Click "🎙️ Start Medical Transcription"** button
4. **Expected result**: Mock transcription with SOAP note generation

## 🔧 Troubleshooting Common Issues

### **Function Not Appearing After Import**
- **Cause**: Function not enabled after import
- **Solution**: Go to Workspace → Functions, find your function, toggle it **ON**

### **"Import Failed" or Syntax Errors**
- **Cause**: External import dependencies or syntax issues
- **Solution**: Use the corrected `*_corrected.py` files which remove external dependencies

### **Functions Show But Don't Work**
- **Cause**: Functions need to be assigned to models or enabled globally
- **Solution**: 
  - **For Action functions**: Enable globally in Workspace → Functions
  - **For Filter/Pipe functions**: Assign to specific models in Workspace → Models

### **"Access Denied" Errors**
- **Cause**: Admin-only mode enabled in function settings
- **Solution**: Edit function Valves, add your username to `admin_users` list

### **Connection Errors in Production Mode**
- **Cause**: Healthcare API not accessible
- **Solution**: Enable `mock_transcription_enabled` for testing, or verify API is running

## 📋 Function Structure Requirements

### **Required Elements** (all corrected files include these):
```python
"""
title: Function Name
author: Your Name  
version: 1.0.0
description: Function description
"""

from pydantic import BaseModel, Field
from typing import Optional

class Action:  # or Filter/Pipe
    class Valves(BaseModel):
        setting: str = Field(
            default="value",
            description="Setting description"
        )
    
    def __init__(self):
        self.valves = self.Valves()
    
    async def action(self, body: dict, __user__: Optional[dict] = None, __event_emitter__=None):
        # Function logic here
        return {"content": "Response text"}
```

## 🎯 Environment Variable Alternative

If Valves don't work, you can use environment variables:

```bash
# Set these in your Open WebUI environment
export HEALTHCARE_WEBSOCKET_URL="ws://your-api:8000"
export TRANSCRIPTION_TIMEOUT="300"  
export DEVELOPER_MODE="true"
export MOCK_TRANSCRIPTION="true"
export DEBUG_LOGGING="false"
```

## 🚨 Important Notes

### **What DOESN'T Work** (based on research):
- ❌ Placing `.py` files in Docker volumes/functions directory
- ❌ Using JSON format for initial import (unless from community)
- ❌ Functions with external dependencies (not packaged in Open WebUI)
- ❌ Functions without proper metadata headers

### **What DOES Work** (confirmed by research):
- ✅ Importing Python code through UI  
- ✅ Self-contained functions with fallback configs
- ✅ Proper Action/Filter/Pipe class structures
- ✅ Configuration through Valves system
- ✅ Environment variable fallbacks

## 🎉 Success Indicators

Your functions are working correctly when:

### **Test Function**:
- ✅ Appears as enabled in Functions list
- ✅ Shows action button in chat interface  
- ✅ Displays success message when clicked

### **Healthcare Config Manager**:
- ✅ Shows configuration summary
- ✅ Admin access working properly
- ✅ Valves modifications take effect

### **Medical Transcription**:
- ✅ Action button appears in chat
- ✅ Mock mode generates realistic transcription data
- ✅ SOAP notes are properly formatted
- ✅ Real-time status updates work

## 🔄 Next Steps

1. **Start with `test_action_simple.py`** to verify import process
2. **Import the corrected healthcare functions**  
3. **Configure through Valves** for your environment
4. **Test in mock mode** before connecting to real services
5. **Enable production mode** once everything works

This research-based approach solves the real issues with Open WebUI function importing and provides a working solution for your healthcare system integration!