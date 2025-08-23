# Healthcare Configuration Management System

## 🎯 Overview

The Healthcare Configuration Management System provides a user-friendly interface for managing all healthcare AI system configurations through Open WebUI. This system replaces the need to manually edit YAML files and restart services, offering:

- **Dynamic Valves** - Editable configuration through Open WebUI interface
- **YAML Persistence** - Changes automatically saved to configuration files
- **Live Reload** - No service restart required for most changes
- **Admin Controls** - Role-based access to configuration management
- **Validation** - Built-in validation prevents invalid configurations
- **Backup & Restore** - Automatic backups before changes

## 🚀 Quick Start

### **Installation**

1. **Copy Configuration Management Files:**
```bash
# Copy the main configuration manager
cp /home/intelluxe/interfaces/open_webui/healthcare_config_manager.py \
   /path/to/your/openwebui/functions/

# Copy the enhanced transcription action  
cp /home/intelluxe/interfaces/open_webui/medical_transcription_action.py \
   /path/to/your/openwebui/functions/
```

2. **Enable in Open WebUI:**
   - Go to **Workspace → Functions**
   - Find "⚙️ Healthcare Configuration Manager" 
   - Click **Enable** to activate
   - Find "🎙️ Medical Transcription" (updated version)
   - Click **Enable** to activate

3. **Set Admin Access:**
   - The configuration manager is admin-only by default
   - Default admin users: `["admin", "justin", "jeff"]`
   - Modify the `ADMIN_USERS` valve to add/remove administrators

## ⚙️ Configuration Management Options

### **Method 1: Healthcare Configuration Manager Function**

This is a **dedicated configuration management interface**:

#### **Features:**
- 🎛️ **Comprehensive Settings** - All system configurations in one place
- 📂 **Organized Sections** - Settings grouped by functionality
- 🔒 **Admin-Only Access** - Secure configuration management
- 📋 **Configuration Summary** - View current settings at a glance
- 💾 **Automatic Backups** - Safe configuration changes
- ✅ **Validation** - Prevent invalid configurations

#### **Usage:**
1. **Start Configuration Session:**
   - Click "⚙️ Healthcare Configuration Manager" in chat
   - System shows current configuration summary
   - Management options displayed

2. **Configure Settings via Valves:**
   - Go to function settings in Open WebUI
   - Modify configuration values in the Valves interface
   - Changes are automatically validated and applied

#### **Configuration Sections:**

##### **📡 Transcription Service**
- `TRANSCRIPTION_WEBSOCKET_URL` - WebSocket connection URL
- `TRANSCRIPTION_TIMEOUT_SECONDS` - Session timeout (60-3600 seconds)  
- `TRANSCRIPTION_CHUNK_INTERVAL` - Audio processing interval (1-10 seconds)
- `DEFAULT_CONFIDENCE_THRESHOLD` - Confidence threshold (0.1-1.0)
- `HIGH_CONFIDENCE_THRESHOLD` - High confidence threshold (0.1-1.0)

##### **🖥️ UI Integration**
- `UI_WEBSOCKET_URL` - UI WebSocket connection
- `UI_REST_API_URL` - UI REST API connection
- `DEVELOPER_MODE_ENABLED` - Enable developer features
- `DEBUG_LOGGING_ENABLED` - Enable debug logging
- `MOCK_TRANSCRIPTION_MODE` - Use mock transcription for testing

##### **🏥 Medical Compliance**
- `SHOW_MEDICAL_DISCLAIMER` - Display disclaimer to users
- `PHI_PROTECTION_ENABLED` - Enable PHI protection
- `HEALTHCARE_COMPLIANCE_MODE` - Strict compliance mode
- `AUDIT_LOGGING_ENABLED` - Enable audit logging
- `MEDICAL_DISCLAIMER_TEXT` - Custom disclaimer text

##### **⚡ Performance & Limits**
- `MAX_CONCURRENT_SESSIONS` - Max sessions per user (1-50)
- `CONNECTION_RETRY_ATTEMPTS` - Retry attempts (1-10)
- `RETRY_DELAY_SECONDS` - Retry delay (1-30 seconds)

##### **✨ Features**
- `AUTO_SOAP_GENERATION` - Auto-generate SOAP notes
- `REAL_TIME_TRANSCRIPTION_DISPLAY` - Show real-time transcription
- `STATUS_UPDATES_ENABLED` - Show status updates
- `AUDIO_VISUALIZATION_ENABLED` - Enable audio visualization
- `SESSION_HISTORY_ENABLED` - Enable session history

### **Method 2: Enhanced Medical Transcription Action**

The **Medical Transcription Action** now has **dynamic Valves** for quick configuration:

#### **Features:**
- 🎙️ **Quick Settings** - Most commonly changed transcription settings
- 📝 **Field Descriptions** - Helpful tooltips for each setting
- 🎚️ **Validation Rules** - Built-in limits and constraints
- 💾 **YAML Persistence** - Changes saved to configuration files
- ⚡ **Live Updates** - No restart required

#### **Usage:**
1. Go to "🎙️ Medical Transcription" function settings
2. Modify configuration values in the Valves interface
3. Changes automatically persist to YAML files
4. Configuration reloads without service restart

#### **Available Settings:**
- Healthcare API URLs
- Developer mode settings
- Transcription timeouts and intervals  
- Medical compliance options
- User experience preferences
- Performance limits

## 🔧 Technical Implementation

### **Dynamic Valves Architecture**

```python
class Valves(BaseModel):
    """Dynamic configuration with YAML persistence"""
    
    SETTING_NAME: type = Field(
        default=CONFIG.section.value,
        ge=min_value,  # Validation constraints
        le=max_value,
        description="User-friendly description"
    )
```

### **YAML Write-Back System**

```python
def update_configuration(self, new_values: Dict[str, Any]):
    """Update YAML files with new configuration values"""
    
    # 1. Load current YAML configuration
    # 2. Map valve fields to YAML structure  
    # 3. Create backup of current configuration
    # 4. Apply changes with validation
    # 5. Write updated YAML files
    # 6. Reload configuration objects
```

### **Configuration Validation**

```python
def validate_configuration(self, values: Dict[str, Any]):
    """Validate configuration before applying"""
    
    # URL validation
    # Range checking for numeric values
    # List validation for user arrays
    # Cross-field dependency checks
```

## 📁 Configuration Files

### **ui_config.yml**
```yaml
# Open WebUI Integration Configuration
api_integration:
  websocket_url: "ws://localhost:8000"
  rest_api_url: "http://localhost:8000"

developer:
  mode_enabled: true
  test_users: ["justin", "jeff"]
  debug_logging: true

compliance:
  phi_protection_enabled: true
  healthcare_compliance_mode: true
  show_medical_disclaimer: true
```

### **transcription_config.yml**
```yaml
# Transcription Service Configuration  
websocket:
  base_url: "ws://localhost:8000"
  connection_timeout_seconds: 30

session:
  default_timeout_seconds: 300
  audio_chunk_interval_seconds: 2
  max_concurrent_sessions: 50

quality:
  default_confidence_threshold: 0.85
  high_confidence_threshold: 0.92
```

## 🔒 Security & Access Control

### **Admin-Only Mode**
- Configuration management restricted to administrators
- User access validated before allowing changes
- All configuration changes logged for audit

### **Admin Users Configuration**
```python
ADMIN_USERS: List[str] = Field(
    default=["admin", "justin", "jeff"],
    description="Users with configuration management access"
)
```

### **Automatic Backups**
- Configuration backups created before changes
- Backup files: `config_file.yml.backup`
- Manual restore capability

## 🧪 Testing Configuration Changes

### **Validation Features**
- ✅ URL format validation
- ✅ Numeric range checking  
- ✅ List structure validation
- ✅ Cross-field dependency checks
- ⚠️ Warning messages for suboptimal settings

### **Testing Modes**
- 🎭 **Mock Transcription** - Test without real audio processing
- 🛠️ **Developer Mode** - Additional debugging features
- 📝 **Debug Logging** - Detailed operation logs

## 🔄 Hot-Reload System

### **Configuration Reload Process**
1. **YAML Update** - New values written to configuration files
2. **Module Reload** - Configuration modules reloaded
3. **Service Notification** - Active services notified of changes
4. **Validation Check** - New configuration validated
5. **Rollback Capability** - Restore from backup if needed

### **Services Supporting Hot-Reload**
- ✅ Medical Transcription Action
- ✅ Healthcare Configuration Manager  
- ✅ WebSocket Transcription Service
- ✅ UI Configuration API

## 🚨 Troubleshooting

### **Common Issues**

#### **"Access Denied" Error**
```
❌ Access denied. Administrator privileges required
```
**Solution:** Add your username to `ADMIN_USERS` list in Healthcare Configuration Manager

#### **"Configuration Update Failed"**
```
❌ Configuration update failed: Permission denied
```
**Solution:** Check file permissions on YAML configuration files

#### **"Invalid Configuration"**
```
❌ Validation failed: TRANSCRIPTION_TIMEOUT must be at least 60 seconds
```
**Solution:** Review validation constraints and correct values

### **Debug Mode**
Enable detailed logging:
1. Set `DEBUG_LOGGING_ENABLED = True`
2. Check healthcare-api logs for configuration details
3. Use mock transcription mode for testing

### **Backup Recovery**
To restore from backup:
1. Stop healthcare services
2. Copy `.yml.backup` files over current configuration
3. Restart services
4. Verify configuration in management interface

## 📊 Configuration Management Best Practices

### **Before Making Changes**
1. 📋 Review current configuration summary
2. 🧪 Test in development environment first
3. 💾 Ensure automatic backups are working
4. 📝 Document significant changes

### **Change Management Process**
1. 🎯 **Plan Changes** - Identify specific settings to modify
2. ✅ **Validate Settings** - Check constraints and dependencies  
3. 🧪 **Test Changes** - Use mock mode for testing
4. 💾 **Apply Changes** - Update through Valves interface
5. 🔍 **Verify Operation** - Confirm system works with new settings
6. 📝 **Document Changes** - Record what was changed and why

### **Production Deployment**
1. **Development Testing** - Test all changes in dev environment
2. **Staging Validation** - Validate in staging environment
3. **Production Backup** - Ensure current production config is backed up
4. **Gradual Rollout** - Apply changes during low-usage periods
5. **Monitoring** - Monitor system health after changes

## 🎉 Success!

Your healthcare AI system now has a comprehensive, user-friendly configuration management system that makes it easy to:

- ⚙️ **Manage Settings** - Intuitive interface for all configurations
- 💾 **Persist Changes** - Automatic YAML file updates  
- 🔒 **Control Access** - Admin-only configuration management
- 🧪 **Test Safely** - Validation and backup systems
- 📊 **Monitor Changes** - Audit logging and change tracking

The configuration management system transforms your healthcare AI platform from requiring manual file editing to having a professional configuration interface accessible through Open WebUI!