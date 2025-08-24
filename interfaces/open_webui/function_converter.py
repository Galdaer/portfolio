#!/usr/bin/env python3
"""
Open WebUI Function Converter
Converts Python function files to Open WebUI JSON import format.
"""

import json
import uuid
import re
from pathlib import Path
from typing import Dict, Any, Optional
import argparse


class OpenWebUIConverter:
    """Converts Python functions to Open WebUI JSON format."""
    
    def __init__(self):
        self.function_types = ["action", "filter", "pipe"]
    
    def extract_function_info(self, content: str) -> Dict[str, Any]:
        """Extract function metadata from Python code."""
        info = {
            "name": "Unknown Function",
            "description": "No description available",
            "type": "action"  # default
        }
        
        # Extract class docstring for description
        docstring_pattern = r'class Action.*?"""(.*?)"""'
        match = re.search(docstring_pattern, content, re.DOTALL)
        if match:
            description = match.group(1).strip()
            # Get first meaningful line
            lines = [line.strip() for line in description.split('\n') if line.strip()]
            if lines:
                info["description"] = lines[0]
        
        # Extract name from filename pattern or class structure
        # Look for patterns like "Medical Transcription Action" in comments
        name_patterns = [
            r'Medical Transcription Action',
            r'Healthcare Configuration Manager',
            r'(\w+ \w+ \w+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, content)
            if match:
                info["name"] = match.group(0)
                break
        
        # Determine type based on class structure
        if "class Action:" in content:
            info["type"] = "action"
        elif "class Filter:" in content:
            info["type"] = "filter"
        elif "class Pipe:" in content:
            info["type"] = "pipe"
            
        return info
    
    def remove_external_imports(self, content: str) -> str:
        """Remove or modify external imports that won't work in Open WebUI."""
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Remove sys.path modifications
            if 'sys.path.append' in line:
                processed_lines.append(f"# {line}")  # Comment out
                continue
            
            # Handle config imports - replace with environment variables
            if 'from config.' in line and ('_config_loader' in line or '_config' in line):
                processed_lines.append(f"# {line}  # Replaced with environment variables")
                continue
                
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def add_fallback_config(self, content: str) -> str:
        """Add fallback configuration for external dependencies."""
        fallback_code = '''
import os
from typing import Dict, Any

# Fallback configuration when external config files aren't available
class FallbackConfig:
    """Fallback configuration using environment variables."""
    
    def __init__(self):
        # Transcription defaults
        self.websocket_base_url = os.getenv('HEALTHCARE_WEBSOCKET_URL', 'ws://localhost:8000')
        self.rest_api_url = os.getenv('HEALTHCARE_REST_URL', 'http://localhost:8000')
        self.timeout_seconds = int(os.getenv('TRANSCRIPTION_TIMEOUT', '300'))
        self.chunk_interval = int(os.getenv('CHUNK_INTERVAL', '2'))
        self.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', '0.85'))
        
        # UI defaults
        self.developer_mode = os.getenv('DEVELOPER_MODE', 'true').lower() == 'true'
        self.debug_logging = os.getenv('DEBUG_LOGGING', 'false').lower() == 'true'
        self.mock_transcription = os.getenv('MOCK_TRANSCRIPTION', 'false').lower() == 'true'
        self.show_disclaimer = os.getenv('SHOW_MEDICAL_DISCLAIMER', 'true').lower() == 'true'
        self.phi_protection = os.getenv('PHI_PROTECTION_ENABLED', 'true').lower() == 'true'

# Create fallback configuration instances
try:
    # Try to import original configs if available
    from config.transcription_config_loader import TRANSCRIPTION_CONFIG
    from config.ui_config_loader import UI_CONFIG
except ImportError:
    # Use fallback configuration
    fallback = FallbackConfig()
    
    # Mock config objects to match expected structure
    class MockTranscriptionConfig:
        def __init__(self):
            self.websocket = type('obj', (object,), {'base_url': fallback.websocket_base_url})
            self.session = type('obj', (object,), {
                'default_timeout_seconds': fallback.timeout_seconds,
                'audio_chunk_interval_seconds': fallback.chunk_interval
            })
            self.quality = type('obj', (object,), {
                'default_confidence_threshold': fallback.confidence_threshold,
                'high_confidence_threshold': fallback.confidence_threshold + 0.05
            })
    
    class MockUIConfig:
        def __init__(self):
            self.api_integration = type('obj', (object,), {
                'websocket_url': fallback.websocket_base_url,
                'rest_api_url': fallback.rest_api_url
            })
            self.developer = type('obj', (object,), {
                'mode_enabled': fallback.developer_mode,
                'debug_logging': fallback.debug_logging,
                'mock_transcription': fallback.mock_transcription,
                'test_users': ["admin", "justin", "jeff"],
                'default_test_user': "admin"
            })
            self.compliance = type('obj', (object,), {
                'show_medical_disclaimer': fallback.show_disclaimer,
                'phi_protection_enabled': fallback.phi_protection,
                'disclaimer_text': "This system provides administrative support only, not medical advice."
            })
            self.session = type('obj', (object,), {
                'timeout_seconds': fallback.timeout_seconds,
                'chunk_interval_seconds': fallback.chunk_interval,
                'auto_soap_generation': True
            })
            self.user_experience = type('obj', (object,), {
                'show_real_time_transcription': True
            })
    
    TRANSCRIPTION_CONFIG = MockTranscriptionConfig()
    UI_CONFIG = MockUIConfig()

'''
        
        # Insert fallback code after imports but before class definition
        lines = content.split('\n')
        class_line = -1
        
        for i, line in enumerate(lines):
            if line.startswith('class Action:') or line.startswith('class Filter:') or line.startswith('class Pipe:'):
                class_line = i
                break
        
        if class_line > 0:
            lines.insert(class_line, fallback_code)
        else:
            # If no class found, add at the end
            lines.append(fallback_code)
        
        return '\n'.join(lines)
    
    def convert_to_json(self, py_file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Convert Python function file to Open WebUI JSON format."""
        py_path = Path(py_file_path)
        
        if not py_path.exists():
            raise FileNotFoundError(f"Python file not found: {py_file_path}")
        
        # Read Python content
        with open(py_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Process content
        processed_content = self.remove_external_imports(original_content)
        processed_content = self.add_fallback_config(processed_content)
        
        # Extract metadata
        info = self.extract_function_info(original_content)
        
        # Generate JSON structure
        function_json = {
            "id": str(uuid.uuid4()).replace('-', ''),
            "name": info["name"],
            "meta": {
                "description": info["description"],
                "manifest": {},
                "type": info["type"]
            },
            "content": processed_content
        }
        
        # Save to file if output path provided
        if output_path:
            output_path = Path(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(function_json, f, indent=2, ensure_ascii=False)
            print(f"✅ Converted function saved to: {output_path}")
        
        return function_json
    
    def batch_convert(self, input_dir: str, output_dir: str):
        """Convert all Python function files in a directory."""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        output_path.mkdir(exist_ok=True)
        
        py_files = list(input_path.glob("*.py"))
        converted_files = []
        
        for py_file in py_files:
            # Skip test files and converters
            if any(skip in py_file.name.lower() for skip in ['test_', 'converter', '__pycache__']):
                continue
            
            try:
                json_filename = py_file.stem + '.json'
                json_path = output_path / json_filename
                
                self.convert_to_json(str(py_file), str(json_path))
                converted_files.append(json_filename)
                
            except Exception as e:
                print(f"❌ Error converting {py_file.name}: {e}")
        
        if converted_files:
            print(f"\n🎉 Successfully converted {len(converted_files)} functions:")
            for filename in converted_files:
                print(f"   - {filename}")
        else:
            print("⚠️ No functions were converted")


def main():
    """Command-line interface for the converter."""
    parser = argparse.ArgumentParser(description='Convert Python functions to Open WebUI JSON format')
    parser.add_argument('input', help='Input Python file or directory')
    parser.add_argument('-o', '--output', help='Output JSON file or directory')
    parser.add_argument('--batch', action='store_true', help='Batch convert all Python files in directory')
    
    args = parser.parse_args()
    
    converter = OpenWebUIConverter()
    
    try:
        if args.batch:
            output_dir = args.output or str(Path(args.input) / 'json_exports')
            converter.batch_convert(args.input, output_dir)
        else:
            output_file = args.output or str(Path(args.input).with_suffix('.json'))
            converter.convert_to_json(args.input, output_file)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())