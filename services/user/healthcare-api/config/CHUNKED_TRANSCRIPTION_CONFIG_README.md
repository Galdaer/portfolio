# Chunked Transcription Configuration System

## Overview

This configuration system extracts all hardcoded settings from the chunked transcription system into a comprehensive, centralized YAML configuration with environment-specific overrides.

## Files Created

### Core Configuration Files
- `/config/chunked_transcription_config.yml` - Main YAML configuration file with all settings
- `/config/chunked_transcription_config_loader.py` - Python configuration loader with dataclasses
- `/api/chunked_transcription_config_endpoint.py` - FastAPI endpoint to serve config to frontend

### Integration Updates
- Updated `/interfaces/open_webui/medical_transcription_tool.py` to use YAML config
- Updated `/core/transcription/secure_websocket_handler.py` to use YAML config  
- Updated `/static/secure_live_transcription.html` to load config from server endpoint

### Testing & Examples
- `/tests/test_chunked_transcription_config.py` - Comprehensive test suite
- `/examples/chunked_transcription_config_usage.py` - Usage examples and demonstrations

## Configuration Structure

### Major Configuration Sections

```yaml
# Environment Detection
environment:
  detect_from: ["ENVIRONMENT", "NODE_ENV", "FLASK_ENV"]
  default: "development"

# Chunk Processing (Audio handling)
chunk_processing:
  duration_seconds: 5
  overlap_seconds: 1.0
  sample_rate: 16000
  audio_format: "webm"
  codec: "opus"

# Security & Encryption
encryption:
  enabled: true
  algorithm: "AES-256-GCM"
  key_size_bits: 256
  session_key_rotation_interval_seconds: 3600

# WebSocket Configuration
websocket:
  base_path: "/ws/transcription"
  timeout_seconds: 30
  default_port: 8000
  compression_enabled: true

# Progressive Medical Insights
progressive_insights:
  enabled: true
  medical_entity_extraction:
    enabled: true
    confidence_threshold: 0.85
    entity_types: ["medications", "vital_signs", "symptoms", "diagnoses", "procedures"]

# SOAP Note Generation
soap_generation:
  auto_generation: true
  chunk_interval: 10
  time_interval_seconds: 60

# PHI Protection
phi_protection:
  enabled: true
  detection_level: "standard"  # minimal, standard, maximum
  real_time_scanning: true

# Session Management
session:
  timeout_minutes: 30
  max_recording_minutes: 60
  max_concurrent_sessions: 100

# User Interface Settings
ui_settings:
  show_confidence_scores: true
  enable_audio_feedback: true
  bar_count: 30
  auto_scroll_insights: true

# Performance Settings
performance:
  max_concurrent_chunks: 10
  enable_parallel_processing: true
  use_gpu_acceleration: true
```

### Environment-Specific Overrides

```yaml
environments:
  development:
    encryption:
      enabled: false  # Easier debugging
    logging:
      levels:
        root: "DEBUG"
  
  testing:
    session:
      timeout_minutes: 5  # Shorter for tests
    phi_protection:
      enabled: false  # Use synthetic data
  
  production:
    encryption:
      session_key_rotation_interval_seconds: 1800  # More frequent
    logging:
      levels:
        root: "WARN"
```

## Usage Examples

### Backend Usage (Python)

```python
from config.chunked_transcription_config_loader import get_chunked_transcription_config

# Load global configuration
config = get_chunked_transcription_config()

# Use in WebSocket handler
handler = SecureTranscriptionHandler()
handler.chunk_duration = config.chunk_processing.duration_seconds
handler.sample_rate = config.chunk_processing.sample_rate

# Use in encryption
if config.encryption.enabled:
    session_key = AESGCM.generate_key(bit_length=config.encryption.key_size_bits)
```

### Frontend Usage (JavaScript)

```javascript
// Load configuration from server
const response = await fetch('/api/transcription/chunked/config');
const serverConfig = await response.json();

// Use in audio recording
const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
        sampleRate: serverConfig.chunk_processing.sample_rate,
        echoCancellation: serverConfig.audio_processing.echo_cancellation
    }
});

// Use in UI
if (serverConfig.ui_settings.show_confidence_scores) {
    displayConfidenceScores();
}
```

### Open WebUI Tool Usage

```python
# Configuration automatically loaded in __init__
tools = Tools()
# Valves are populated from YAML configuration
print(f"Chunk duration: {tools.valves.CHUNK_DURATION_SECONDS}")
print(f"Encryption: {tools.valves.ENCRYPTION_ENABLED}")
```

## Configuration Loading Flow

1. **Environment Detection**: Detects current environment (development/testing/production)
2. **Base Config Loading**: Loads `chunked_transcription_config.yml`
3. **Environment Variable Expansion**: Processes `${VAR:-default}` syntax
4. **Environment Overrides**: Applies environment-specific settings
5. **Dataclass Population**: Creates typed configuration objects
6. **Global Singleton**: Provides cached configuration instance

## Environment Variable Support

The system supports environment variable expansion with default values:

```yaml
healthcare_api:
  base_url: "${HEALTHCARE_API_URL:-https://localhost:8000}"
  
database:
  password: "${POSTGRES_PASSWORD:-default_password}"
  
features:
  phi_detection: "${PHI_DETECTION_ENABLED:-true}"
```

## API Endpoints

### GET /api/transcription/chunked/config
Returns complete configuration for frontend use.

### GET /api/transcription/chunked/config/summary
Returns simplified configuration with key settings only.

### GET /api/transcription/chunked/health
Returns health status of configuration system.

## Configuration Benefits

### ✅ Centralized Management
- All settings in one place
- No more hunting through multiple files for hardcoded values
- Consistent configuration structure across components

### ✅ Environment Flexibility
- Environment-specific overrides (dev/test/prod)
- Easy deployment configuration changes
- Support for different security levels per environment

### ✅ Type Safety
- Python dataclasses provide type hints and validation
- IDE autocompletion and error checking
- Runtime type validation

### ✅ Security
- Environment variable support for sensitive values
- PHI-safe configuration (no sensitive data in logs)
- Environment-aware security settings

### ✅ Developer Experience  
- Hot-reload configuration changes
- Comprehensive test coverage
- Usage examples and documentation
- Graceful fallbacks for missing configuration

### ✅ Integration Ready
- FastAPI endpoint for frontend consumption
- WebSocket configuration integration
- Open WebUI tool integration
- Healthcare API integration

## Migration Benefits

### Before (Hardcoded)
```python
# Scattered across multiple files
chunk_duration = 5.0  # WebSocket handler
CHUNK_DURATION_SECONDS = 5  # Open WebUI tool
const chunkDuration = 5000;  // HTML file
```

### After (Centralized)
```yaml
# Single source of truth
chunk_processing:
  duration_seconds: 5
```

All components now reference the same configuration value, ensuring consistency and making changes easy.

## Testing

The configuration system includes comprehensive tests covering:

- Default configuration creation
- Environment variable expansion  
- Environment-specific overrides
- YAML file parsing and validation
- Error handling for missing/invalid files
- Configuration completeness validation
- Type safety and constraints

Run tests with:
```bash
cd /home/intelluxe/services/user/healthcare-api
python3 -m pytest tests/test_chunked_transcription_config.py -v
```

## Future Enhancements

1. **Configuration Validation**: Add JSON Schema validation for YAML files
2. **Hot Reload**: Implement file watcher for configuration changes
3. **Configuration UI**: Web interface for configuration management
4. **Audit Trail**: Log configuration changes and access
5. **Configuration Backup**: Automated backup of configuration changes
6. **Template System**: Configuration templates for common deployments

## Security Considerations

- Environment variables used for sensitive values (passwords, tokens)
- PHI detection disabled in testing environment with synthetic data
- Production environment has stricter security defaults
- Configuration loading errors logged but don't expose sensitive information
- Session keys and encryption settings properly configured per environment