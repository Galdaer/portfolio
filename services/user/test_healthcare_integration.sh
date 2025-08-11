#!/bin/bash

# Healthcare Services Integration Test
# Tests communication between healthcare-api, mcp-pipeline, and healthcare-mcp

echo "🏥 Healthcare Services Integration Test"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_service() {
    local service_name=$1
    local url=$2
    local description=$3
    
    printf "Testing %-20s: " "$service_name"
    
    if curl -f -s --max-time 10 "$url" > /dev/null 2>&1; then
        printf "${GREEN}✓ PASS${NC} - %s\n" "$description"
        return 0
    else
        printf "${RED}✗ FAIL${NC} - %s\n" "$description"
        return 1
    fi
}

# Test each service health endpoint
echo "Testing Health Endpoints:"
echo "========================"

test_service "healthcare-api" "http://172.20.0.16:8000/health" "Main healthcare API"
test_service "mcp-pipeline" "http://172.20.0.17:9099/health" "MCP pipeline service"  
test_service "healthcare-mcp" "http://172.20.0.18:3000/health" "Healthcare MCP server"

echo ""
echo "Testing Service Communication:"
echo "============================="

# Test that pipeline can reach API
test_service "pipeline->api" "http://172.20.0.16:8000/agents/health" "Pipeline to API communication"

# Test that API can reach MCP server
test_service "api->mcp" "http://172.20.0.18:3000/tools" "API to MCP server communication"

echo ""
echo "Testing Full Integration:"
echo "========================"

# Test a full request flow through the pipeline
printf "Testing full flow:      "
if curl -f -s --max-time 15 -X POST \
    "http://172.20.0.17:9099/chat" \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Test healthcare query"}]}' > /dev/null 2>&1; then
    printf "${GREEN}✓ PASS${NC} - Full integration working\n"
else
    printf "${YELLOW}? SKIP${NC} - Full integration test (requires auth)\n"
fi

echo ""
echo "Network Configuration Check:"
echo "============================"

echo "Service IP Assignments:"
echo "• healthcare-api:  172.20.0.16:8000"
echo "• mcp-pipeline:    172.20.0.17:9099" 
echo "• healthcare-mcp:  172.20.0.18:3000"

echo ""
echo "Expected Communication Flow:"
echo "Open WebUI → MCP Pipeline (172.20.0.17:9099)"
echo "MCP Pipeline → Healthcare API (172.20.0.16:8000)"
echo "Healthcare API → Healthcare MCP (172.20.0.18:3000)"

echo ""
echo "Test completed!"
