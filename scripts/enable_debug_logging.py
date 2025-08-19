#!/usr/bin/env python3
"""
Enhanced Debug Logging Script for Healthcare AI System

This script enables comprehensive debug logging across all components
to help diagnose issues with medical literature search responses.
"""

import logging
import os
import sys
from pathlib import Path

def setup_enhanced_logging():
    """Setup enhanced debug logging for all healthcare components"""
    
    log_dir = Path("/home/intelluxe/logs")
    log_dir.mkdir(exist_ok=True)
    
    # Define log files for different components
    log_files = {
        "response_formatting": log_dir / "response_formatting.log",
        "phi_processing": log_dir / "phi_processing.log", 
        "agent_interactions": log_dir / "agent_interactions.log",
        "mcp_pipeline_detailed": log_dir / "mcp_pipeline_detailed.log",
        "literature_processing": log_dir / "literature_processing.log",
        "summary_generation": log_dir / "summary_generation.log"
    }
    
    # Create loggers with detailed formatting
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    formatter = logging.Formatter(log_format)
    
    loggers = {}
    for component, log_file in log_files.items():
        logger = logging.getLogger(f"healthcare.debug.{component}")
        logger.setLevel(logging.DEBUG)
        
        # Create file handler
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        loggers[component] = logger
        
        print(f"✅ Enhanced logging enabled for {component}: {log_file}")
    
    return loggers

def create_log_monitoring_script():
    """Create a script to monitor all logs in real-time"""
    
    monitor_script = Path("/home/intelluxe/scripts/monitor_logs.sh")
    
    script_content = """#!/bin/bash
# Enhanced Log Monitoring Script for Healthcare AI System

echo "🔍 Starting enhanced log monitoring for healthcare system..."
echo "Press Ctrl+C to stop monitoring"
echo ""

# Function to monitor a specific log file
monitor_log() {
    local log_file="$1"
    local log_name="$2"
    
    if [[ -f "$log_file" ]]; then
        echo "📄 Monitoring $log_name: $log_file"
        tail -f "$log_file" | while read line; do
            echo "[$log_name] $line"
        done &
    else
        echo "⚠️  Log file not found: $log_file"
    fi
}

# Monitor all healthcare logs
cd /home/intelluxe

echo "Starting log monitoring for all healthcare components..."

# Core logs
monitor_log "logs/healthcare_system.log" "MAIN"
monitor_log "logs/agent_medical_search.log" "SEARCH"
monitor_log "logs/phi_monitoring.log" "PHI"

# Enhanced debug logs
monitor_log "logs/response_formatting.log" "RESPONSE"
monitor_log "logs/phi_processing.log" "PHI_PROC"
monitor_log "logs/agent_interactions.log" "INTERACT"
monitor_log "logs/mcp_pipeline_detailed.log" "PIPELINE"
monitor_log "logs/literature_processing.log" "LITERATURE"
monitor_log "logs/summary_generation.log" "SUMMARY"

# Wait for all background processes
wait
"""
    
    monitor_script.write_text(script_content)
    monitor_script.chmod(0o755)
    
    print(f"✅ Log monitoring script created: {monitor_script}")
    return monitor_script

def create_diagnostic_queries():
    """Create test queries to help diagnose the issue"""
    
    queries_file = Path("/home/intelluxe/scripts/diagnostic_queries.txt")
    
    diagnostic_queries = """
# Diagnostic Queries for Healthcare Literature Search

## Simple queries to test different components:

1. "cardiovascular health" - Test basic medical term search
2. "heart disease" - Test condition-specific search  
3. "diabetes treatment" - Test treatment-focused search
4. "recent cancer research" - Test time-based filtering
5. "covid vaccine studies" - Test specific medical topic

## Expected behavior:
- Agent should retrieve medical literature
- PHI detection should NOT sanitize author names in medical context
- Response should show formatted article listings, not raw JSON
- Pipeline should prioritize formatted_summary over formatted_response

## Debug checkpoints:
- MCP calls succeed ✓ (confirmed in logs)
- Articles parsed correctly ✓ (confirmed in logs) 
- Response formatting ? (needs investigation)
- PHI processing ? (needs investigation)
- Pipeline response selection ? (needs investigation)
"""
    
    queries_file.write_text(diagnostic_queries)
    print(f"✅ Diagnostic queries created: {queries_file}")

def main():
    """Main function to set up comprehensive debugging"""
    
    print("🔧 Setting up enhanced debug logging for Healthcare AI System")
    print("=" * 60)
    
    # Setup enhanced logging
    loggers = setup_enhanced_logging()
    
    # Create monitoring tools
    monitor_script = create_log_monitoring_script()
    create_diagnostic_queries()
    
    print("\n" + "=" * 60)
    print("🎯 Enhanced debugging setup complete!")
    print("\nNext steps:")
    print("1. Restart healthcare-api container to pick up new logging")
    print("2. Run log monitoring: ./scripts/monitor_logs.sh")
    print("3. Test with diagnostic queries in Open WebUI")
    print("4. Review logs to identify where processing fails")
    print("\nKey log files to watch:")
    print("- logs/response_formatting.log - Response generation issues")
    print("- logs/phi_processing.log - PHI detection problems")
    print("- logs/literature_processing.log - Article processing issues")
    print("- logs/agent_medical_search.log - Agent execution flow")

if __name__ == "__main__":
    main()
