# Open WebUI Function Import Guide

This guide explains how to import your healthcare functions into Open WebUI and resolve common issues with external dependencies.

## 🎯 Overview

Open WebUI functions have specific requirements and limitations:
- **Python Code Only**: Functions run in a sandboxed Python environment
- **No External Files**: Cannot access files outside the Open WebUI environment  
- **Limited Imports**: Only standard Python libraries + some pre-installed packages
- **JSON Format Required**: Functions must be in JSON format for import

## 📁 Available Files

Your healthcare functions have been converted to standalone versions that work within Open WebUI:

### Ready-to-Import JSON Files
- `healthcare_config_manager.json` - ⚙️ Healthcare Configuration Manager
- `medical_transcription_action.json` - 🎙️ Medical Transcription Action

### Conversion Tools
- `function_converter.py` - Convert Python functions to JSON format
- `*_standalone.py` - Self-contained versions with environment variable fallbacks

## 🚀 Import Instructions

### Step 1: Access Open WebUI Functions
1. Open your Open WebUI instance
2. Navigate to **Workspace** → **Functions**
3. Click the **Import** button or **+ Add Function**

### Step 2: Import JSON Functions

#### Method A: Direct JSON Import
1. Click **Import Function**
2. Select **Upload File**
3. Choose either:
   - `healthcare_config_manager.json`
   - `medical_transcription_action.json`
4. Click **Import**

#### Method B: Copy-Paste Content
1. Click **Add Function** 
2. Open the JSON file in a text editor
3. Copy the entire JSON content
4. Paste into the import field
5. Click **Save**

### Step 3: Enable Functions
1. After import, find your functions in the Functions list
2. Toggle them **ON** (enable them)
3. For Action functions, they'll appear as buttons in chat interface

### Step 4: Configure Functions
1. Click the **Settings/Gear** icon next to each function
2. Modify the **Valves** (configuration options)
3. Key settings to configure:
   - `HEALTHCARE_API_URL`: Your healthcare API WebSocket URL
   - `DEVELOPER_MODE`: Enable for testing features
   - `MOCK_TRANSCRIPTION`: Enable for testing without real audio

## ⚙️ Configuration Options

### Environment Variables Method
You can configure functions using environment variables instead of Valves:

```bash
# Core Settings
export HEALTHCARE_WEBSOCKET_URL="ws://your-api:8000"
export HEALTHCARE_REST_URL="http://your-api:8000"
export TRANSCRIPTION_TIMEOUT="300"

# Developer Settings  
export DEVELOPER_MODE="true"
export DEBUG_LOGGING="false"
export MOCK_TRANSCRIPTION="true"

# Compliance Settings
export PHI_PROTECTION_ENABLED="true"
export SHOW_MEDICAL_DISCLAIMER="true"
```

### Valve Configuration
Use Open WebUI's Valve interface to modify settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `HEALTHCARE_API_URL` | WebSocket connection URL | `ws://localhost:8000` |
| `TRANSCRIPTION_TIMEOUT` | Session timeout (seconds) | `300` |
| `DEVELOPER_MODE` | Enable test features | `true` |
| `MOCK_TRANSCRIPTION` | Use fake data for testing | `false` |
| `PHI_PROTECTION_ENABLED` | Enable PHI protection | `true` |

## 🧪 Testing Your Functions

### Test the Configuration Manager
1. Enable the **Healthcare Configuration Manager** function
2. Click the function button in chat
3. You should see:
   - Current configuration summary
   - Admin access check
   - Environment variable options

### Test the Medical Transcription
1. Enable the **Medical Transcription Action** function  
2. Set `MOCK_TRANSCRIPTION=true` in Valves
3. Click the **🎙️ Start Medical Transcription** button
4. You should see:
   - Mock transcription process
   - Generated SOAP note
   - Session metadata

## 🔧 Troubleshooting

### Common Import Issues

#### "422 Error" During Import
- **Cause**: Invalid JSON format or illegal characters
- **Solution**: 
  1. Validate JSON format using a JSON validator
  2. Remove any non-standard characters
  3. Ensure proper encoding (UTF-8)

#### "Module Not Found" Errors
- **Cause**: Function trying to import external dependencies
- **Solution**: Use the standalone versions (`*_standalone.py`) which have fallback configurations

#### Functions Not Appearing
- **Cause**: Function not enabled after import
- **Solution**: 
  1. Go to Workspace → Functions
  2. Find your function in the list
  3. Toggle it **ON**

### Configuration Issues

#### "Access Denied" Error
- **Cause**: Admin-only mode enabled, user not in admin list
- **Solution**: 
  1. Edit function Valves
  2. Add your username to `ADMIN_USERS` list
  3. Or set `ADMIN_ONLY_MODE=false`

#### Connection Errors
- **Cause**: Healthcare API not accessible at configured URL
- **Solution**:
  1. Verify your healthcare API is running
  2. Update `HEALTHCARE_API_URL` in Valves
  3. Or enable `MOCK_TRANSCRIPTION` for testing

#### Configuration Not Persisting
- **Cause**: YAML config files not writable
- **Expected**: Functions use environment variables as fallback
- **Solution**: Set environment variables on your Open WebUI server

## 🔄 Function Conversion Workflow

If you need to convert other Python functions:

### Using the Converter Tool
```bash
cd /home/intelluxe/interfaces/open_webui

# Convert single function
python3 function_converter.py your_function.py -o your_function.json

# Batch convert directory
python3 function_converter.py /path/to/functions --batch -o /path/to/json_outputs
```

### Manual Conversion Process
1. **Remove External Imports**: Comment out `sys.path` modifications and external imports
2. **Add Environment Variables**: Replace config imports with `os.getenv()` calls
3. **Add Fallback Logic**: Provide defaults for missing configuration
4. **Convert to JSON**: Use the converter or manually format as JSON

## 📋 Function Requirements Checklist

Before importing, ensure your functions:

- [ ] Use only standard Python imports (no custom modules)
- [ ] Have fallback configurations (environment variables or defaults)  
- [ ] Include proper Pydantic BaseModel for Valves
- [ ] Have Action/Filter/Pipe class with correct methods
- [ ] Are properly formatted as JSON with id, name, meta, content fields

## 🔍 Debugging Tips

### Enable Debug Mode
1. Set `DEBUG_LOGGING=true` in Valves
2. Check Open WebUI logs for detailed information
3. Use `MOCK_TRANSCRIPTION=true` to test without external services

### Check Function Status
1. Go to Workspace → Functions
2. Look for error indicators next to functions
3. Check the function's status and any error messages

### Validate JSON Format
```bash
# Validate JSON syntax
python3 -m json.tool your_function.json

# Or use online JSON validators
```

### Test External Connections
```bash
# Test WebSocket connection
curl -H "Upgrade: websocket" http://your-api:8000

# Test REST API
curl http://your-api:8000/health
```

## 🎉 Success Indicators

Your functions are working correctly when:

✅ **Configuration Manager**:
- Shows current configuration summary
- Admin access working
- Valve modifications take effect
- YAML persistence attempts logged

✅ **Medical Transcription**:
- Button appears in chat interface
- Mock transcription generates fake data
- SOAP notes are properly formatted
- Status updates appear during processing

## 📞 Getting Help

If you encounter issues:

1. **Check the logs**: Enable debug logging in Valves
2. **Verify JSON format**: Use JSON validator tools
3. **Test in mock mode**: Enable mock transcription for testing
4. **Check environment variables**: Ensure proper configuration
5. **Review Open WebUI docs**: Check latest Open WebUI function documentation

## 🔄 Updates and Maintenance

### Updating Functions
1. Modify the `*_standalone.py` files as needed
2. Re-run the converter: `python3 function_converter.py file.py -o file.json`
3. Re-import the updated JSON into Open WebUI
4. Test the updated functionality

### Version Control
- Keep both Python and JSON versions in version control
- Document any changes to environment variables
- Test thoroughly after updates

---

**Note**: These standalone functions are designed to work within Open WebUI's limitations while maintaining the core functionality of your healthcare system. They use environment variables and fallback configurations to handle the absence of external dependencies.