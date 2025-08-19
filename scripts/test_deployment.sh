#!/bin/bash

# Healthcare AI Integration Test & Deployment Script
# Tests complete workflow: Open WebUI → Ollama → MCP → FastAPI Agents

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MCP_URL="http://localhost:3000"
FASTAPI_URL="http://localhost:8000"
WEBUI_URL="http://localhost:1000"
OLLAMA_URL="http://172.20.0.10:11434"

# Logging
LOG_FILE="test_deployment_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

# Test functions
test_service_health() {
    local service_name="$1"
    local url="$2"
    local timeout="${3:-10}"
    
    log_info "Testing $service_name health at $url..."
    
    if curl -s --max-time "$timeout" "$url" > /dev/null; then
        log_success "$service_name is healthy"
        return 0
    else
        log_error "$service_name is not responding"
        return 1
    fi
}

test_mcp_tools() {
    log_info "Testing MCP server tools..."
    
    local tools_request='{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
    
    local response
    response=$(curl -s -X POST "$MCP_URL/mcp" \
        -H "Content-Type: application/json" \
        -d "$tools_request")
    
    if echo "$response" | jq -e '.result.tools' > /dev/null 2>&1; then
        local tool_count
        tool_count=$(echo "$response" | jq '.result.tools | length')
        log_success "MCP server has $tool_count tools available"
        
        # List available tools
        log_info "Available MCP tools:"
        echo "$response" | jq -r '.result.tools[].name' | while read -r tool; do
            log "  - $tool"
        done
        
        return 0
    else
        log_error "Failed to get MCP tools list"
        log "Response: $response"
        return 1
    fi
}

test_mcp_agent_bridge() {
    log_info "Testing MCP-Agent bridge integration..."
    
    local intake_request='{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "clinical_intake",
            "arguments": {
                "patient_data": {
                    "patient_id": "TEST_PAT_001",
                    "first_name": "John",
                    "last_name": "Doe",
                    "date_of_birth": "1980-01-15",
                    "contact_phone": "555-123-4567",
                    "insurance_primary": "Test Insurance Co",
                    "chief_complaint": "Annual checkup"
                },
                "intake_type": "new_patient",
                "session_id": "test_session_001"
            }
        },
        "id": 1
    }'
    
    local response
    response=$(curl -s -X POST "$MCP_URL/mcp" \
        -H "Content-Type: application/json" \
        -d "$intake_request" \
        --max-time 30)
    
    if echo "$response" | jq -e '.result.intake_id' > /dev/null 2>&1; then
        log_success "MCP-Agent bridge working correctly"
        local intake_id
        intake_id=$(echo "$response" | jq -r '.result.intake_id')
        log_info "Generated intake ID: $intake_id"
        return 0
    else
        log_error "MCP-Agent bridge test failed"
        log "Response: $response"
        return 1
    fi
}

test_fastapi_agents() {
    log_info "Testing FastAPI healthcare agents..."
    
    local agents=(
        "intake"
        "document"
        "research"
        "transcription"
        "billing"
        "insurance"
        "conversation"
    )
    
    local failed_agents=()
    
    for agent in "${agents[@]}"; do
        local health_url="$FASTAPI_URL/agents/$agent/health"
        
        if curl -s --max-time 10 "$health_url" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
            log_success "Agent $agent is healthy"
        else
            log_error "Agent $agent is not healthy"
            failed_agents+=("$agent")
        fi
    done
    
    if [ ${#failed_agents[@]} -eq 0 ]; then
        log_success "All ${#agents[@]} FastAPI agents are healthy"
        return 0
    else
        log_error "${#failed_agents[@]} agents failed: ${failed_agents[*]}"
        return 1
    fi
}

test_phi_protection() {
    log_info "Testing PHI protection..."
    
    # Test with data containing potential PHI
    local phi_test_request='{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "clinical_intake",
            "arguments": {
                "patient_data": {
                    "name": "John Doe",
                    "ssn": "123-45-6789",
                    "phone": "(555) 123-4567"
                },
                "session_id": "phi_test_001"
            }
        },
        "id": 1
    }'
    
    local response
    response=$(curl -s -X POST "$MCP_URL/mcp" \
        -H "Content-Type: application/json" \
        -d "$phi_test_request" \
        --max-time 30)
    
    # Check if PHI validation is working
    if echo "$response" | jq -e '.error.message | contains("PHI validation failed")' > /dev/null 2>&1; then
        log_success "PHI protection is working - blocked request with PHI"
        return 0
    elif echo "$response" | jq -e '.result' > /dev/null 2>&1; then
        log_warning "PHI protection may not be working - request with PHI was processed"
        return 1
    else
        log_error "PHI protection test inconclusive"
        log "Response: $response"
        return 1
    fi
}

test_medical_literature_search() {
    log_info "Testing medical literature search..."
    
    local search_request='{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "research_medical_literature",
            "arguments": {
                "query": "diabetes type 2 management guidelines",
                "max_results": 5,
                "include_clinical_trials": true
            }
        },
        "id": 1
    }'
    
    local response
    response=$(curl -s -X POST "$MCP_URL/mcp" \
        -H "Content-Type: application/json" \
        -d "$search_request" \
        --max-time 30)
    
    if echo "$response" | jq -e '.result.search_results' > /dev/null 2>&1; then
        local result_count
        result_count=$(echo "$response" | jq '.result.search_results | length')
        log_success "Medical literature search returned $result_count results"
        return 0
    else
        log_error "Medical literature search failed"
        log "Response: $response"
        return 1
    fi
}

test_audio_transcription() {
    log_info "Testing audio transcription (mock mode)..."
    
    local transcription_request='{
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "transcribe_audio",
            "arguments": {
                "audio_data": {
                    "format": "wav",
                    "duration": 30,
                    "sample_rate": 16000,
                    "mock": true,
                    "content": "Patient reports feeling well today"
                },
                "session_id": "transcription_test_001",
                "doctor_id": "TEST_DOC_001"
            }
        },
        "id": 1
    }'
    
    local response
    response=$(curl -s -X POST "$MCP_URL/mcp" \
        -H "Content-Type: application/json" \
        -d "$transcription_request" \
        --max-time 30)
    
    if echo "$response" | jq -e '.result.transcription_id' > /dev/null 2>&1; then
        log_success "Audio transcription working correctly"
        local transcription_id
        transcription_id=$(echo "$response" | jq -r '.result.transcription_id')
        log_info "Generated transcription ID: $transcription_id"
        return 0
    else
        log_error "Audio transcription test failed"
        log "Response: $response"
        return 1
    fi
}

test_complete_workflow() {
    log_info "Testing complete patient workflow..."
    
    local session_id
    session_id="workflow_test_$(date +%s)"
    local workflow_steps
    read -r -a workflow_steps <<< '{"name": "clinical_intake", "args": {"patient_data": {"patient_id": "TEST_PAT_WORKFLOW", "first_name": "Jane", "last_name": "Smith", "chief_complaint": "Follow-up visit"}, "intake_type": "follow_up", "session_id": "'$session_id'"}} {"name": "research_medical_literature", "args": {"query": "hypertension management 2024", "max_results": 3}} {"name": "process_healthcare_document", "args": {"document_type": "progress_note", "content": "Patient follow-up for hypertension management", "session_id": "'$session_id'"}}'
    
    local step_num=1
    for step in "${workflow_steps[@]}"; do
        local tool_name
        tool_name=$(echo "$step" | jq -r '.name')
        local tool_args
        tool_args=$(echo "$step" | jq '.args')
        
        log_info "Workflow Step $step_num: $tool_name"
        
        local request
        request=$(jq -n \
            --arg method "tools/call" \
            --arg name "$tool_name" \
            --argjson args "$tool_args" \
            '{
                "jsonrpc": "2.0",
                "method": $method,
                "params": {
                    "name": $name,
                    "arguments": $args
                },
                "id": 1
            }')
        
        local response
        response=$(curl -s -X POST "$MCP_URL/mcp" \
            -H "Content-Type: application/json" \
            -d "$request" \
            --max-time 45)
        
        if echo "$response" | jq -e '.result' > /dev/null 2>&1; then
            log_success "Workflow Step $step_num ($tool_name) completed"
        else
            log_error "Workflow Step $step_num ($tool_name) failed"
            log "Response: $response"
            return 1
        fi
        
        ((step_num++))
    done
    
    log_success "Complete patient workflow executed successfully"
    return 0
}

test_performance_benchmarks() {
    log_info "Running performance benchmarks..."
    
    # Benchmark 1: MCP tools/list performance
    log_info "Benchmark 1: MCP tools/list (10 requests)"
    local start_time
    start_time=$(date +%s.%N)
    
    for i in {1..10}; do
        curl -s -X POST "$MCP_URL/mcp" \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}' > /dev/null
    done
    
    local end_time
    end_time=$(date +%s.%N)
    local duration
    duration=$(echo "$end_time - $start_time" | bc -l)
    local avg_time
    avg_time=$(echo "scale=3; $duration / 10" | bc -l)
    
    log_success "MCP tools/list average: ${avg_time}s per request"
    
    # Benchmark 2: Clinical intake performance
    log_info "Benchmark 2: Clinical intake (5 requests)"
    start_time=$(date +%s.%N)
    
    for i in {1..5}; do
        local request='{
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "clinical_intake",
                "arguments": {
                    "patient_data": {
                        "patient_id": "PERF_TEST_'$i'",
                        "first_name": "Test",
                        "last_name": "Patient"
                    },
                    "intake_type": "new_patient",
                    "session_id": "perf_test_'$i'"
                }
            },
            "id": 1
        }'
        
        curl -s -X POST "$MCP_URL/mcp" \
            -H "Content-Type: application/json" \
            -d "$request" \
            --max-time 30 > /dev/null
    done
    
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc -l)
    avg_time=$(echo "scale=3; $duration / 5" | bc -l)
    
    log_success "Clinical intake average: ${avg_time}s per request"
    
    # Performance assertions
    if (( $(echo "$avg_time > 10" | bc -l) )); then
        log_warning "Clinical intake performance slower than expected (>10s average)"
    else
        log_success "Clinical intake performance within acceptable range"
    fi
}

run_python_tests() {
    log_info "Running Python test suite..."
    
    if [ -f "tests/test_e2e_healthcare_workflows.py" ]; then
        if python3 -m pytest tests/test_e2e_healthcare_workflows.py -v --tb=short; then
            log_success "Python test suite passed"
            return 0
        else
            log_error "Python test suite failed"
            return 1
        fi
    else
        log_warning "Python test suite not found - skipping"
        return 0
    fi
}

generate_test_report() {
    log_info "Generating test report..."
    
    local report_file
    report_file="test_report_$(date +%Y%m%d_%H%M%S).html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Healthcare AI Integration Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f8ff; padding: 20px; border-radius: 8px; }
        .success { color: #008000; }
        .error { color: #ff0000; }
        .warning { color: #ffa500; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 Healthcare AI Integration Test Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Test Environment:</strong> Local Development</p>
    </div>
    
    <div class="test-section">
        <h2>Test Results Summary</h2>
        <pre>$(cat "$LOG_FILE")</pre>
    </div>
    
    <div class="test-section">
        <h2>Service Health Status</h2>
        <ul>
            <li>MCP Server: $(curl -s "$MCP_URL/health" && echo "✅ Healthy" || echo "❌ Unhealthy")</li>
            <li>FastAPI Agents: $(curl -s "$FASTAPI_URL/health" && echo "✅ Healthy" || echo "❌ Unhealthy")</li>
            <li>Open WebUI: $(curl -s "$WEBUI_URL" && echo "✅ Available" || echo "❌ Unavailable")</li>
        </ul>
    </div>
    
    <div class="test-section">
        <h2>Configuration</h2>
        <ul>
            <li>MCP Server URL: $MCP_URL</li>
            <li>FastAPI URL: $FASTAPI_URL</li>
            <li>Open WebUI URL: $WEBUI_URL</li>
            <li>Ollama URL: $OLLAMA_URL</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    log_success "Test report generated: $report_file"
}

# Main execution
main() {
    log_info "🏥 Healthcare AI Integration Test Suite Starting..."
    log_info "=============================================="
    
    local test_failures=0
    
    # Service health checks
    log_info "Phase 1: Service Health Checks"
    test_service_health "MCP Server" "$MCP_URL/health" || ((test_failures++))
    test_service_health "FastAPI Agents" "$FASTAPI_URL/health" || ((test_failures++))
    test_service_health "Open WebUI" "$WEBUI_URL" 5 || log_warning "Open WebUI may not be running"
    
    # MCP server tests
    log_info "Phase 2: MCP Server Integration"
    test_mcp_tools || ((test_failures++))
    test_mcp_agent_bridge || ((test_failures++))
    
    # Agent tests
    log_info "Phase 3: FastAPI Agent Validation"
    test_fastapi_agents || ((test_failures++))
    
    # Security tests
    log_info "Phase 4: Security & Compliance"
    test_phi_protection || ((test_failures++))
    
    # Functional tests
    log_info "Phase 5: Functional Testing"
    test_medical_literature_search || ((test_failures++))
    test_audio_transcription || ((test_failures++))
    test_complete_workflow || ((test_failures++))
    
    # Performance tests
    log_info "Phase 6: Performance Benchmarks"
    test_performance_benchmarks || ((test_failures++))
    
    # Python test suite
    log_info "Phase 7: Python Test Suite"
    run_python_tests || ((test_failures++))
    
    # Generate report
    generate_test_report
    
    # Final results
    log_info "=============================================="
    if [ $test_failures -eq 0 ]; then
        log_success "🎉 All tests passed! Healthcare AI Integration is ready for deployment."
        log_info "Next steps:"
        log "  1. Access Open WebUI at: $WEBUI_URL"
        log "  2. Configure MCP connection in Open WebUI settings"
        log "  3. Start using healthcare AI tools in conversations"
        exit 0
    else
        log_error "❌ $test_failures test(s) failed. Please review the issues above."
        log_info "Check the full log: $LOG_FILE"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    local missing_deps=()
    
    command -v curl >/dev/null 2>&1 || missing_deps+=("curl")
    command -v jq >/dev/null 2>&1 || missing_deps+=("jq")
    command -v bc >/dev/null 2>&1 || missing_deps+=("bc")
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Install with: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    check_dependencies
    main "$@"
fi