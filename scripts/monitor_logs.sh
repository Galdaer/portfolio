#!/bin/bash
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
