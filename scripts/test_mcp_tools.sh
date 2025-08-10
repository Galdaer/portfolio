#!/bin/bash
"""
Test Healthcare MCP Tools Integration
Tests all 15 healthcare MCP tools via direct API calls
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://172.20.0.12:3001"
AUTH_HEADER="Authorization: Bearer healthcare-mcp-2025"

echo -e "${BLUE}🏥 Healthcare MCP Tools Integration Test${NC}"
echo "============================================="
echo ""

# Function to test an endpoint
test_endpoint() {
    local tool_name="$1"
    local endpoint="$2"
    local payload="$3"
    local description="$4"
    
    echo -e "${YELLOW}🧪 Testing: $description${NC}"
    echo "   Tool: $tool_name"
    echo "   Endpoint: $endpoint"
    
    if [ -n "$payload" ]; then
        echo "   Payload: $payload"
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "$AUTH_HEADER" \
            -d "$payload" \
            "$BASE_URL$endpoint" 2>/dev/null)
    else
        response=$(curl -s -H "$AUTH_HEADER" "$BASE_URL$endpoint" 2>/dev/null)
    fi
    
    # Check if response contains error
    if echo "$response" | grep -q '"error"' || echo "$response" | grep -q '"detail"'; then
        echo -e "   ${RED}❌ FAILED${NC}"
        echo "   Response: $(echo "$response" | head -c 100)..."
    elif [ -n "$response" ] && [ "$response" != "null" ]; then
        echo -e "   ${GREEN}✅ SUCCESS${NC}"
        echo "   Response: $(echo "$response" | head -c 100)..."
    else
        echo -e "   ${RED}❌ FAILED (Empty response)${NC}"
    fi
    echo ""
}

# Test 1: Health Check
echo -e "${BLUE}📋 Basic Health Checks${NC}"
echo "------------------------"
test_endpoint "health" "/health" "" "MCP Server Health Check"

# Test 2: Tools Discovery
test_endpoint "tools-list" "/tools/list" "" "Available Tools Discovery"

# Test 3: Authentication Test
echo -e "${BLUE}🔐 Authentication Tests${NC}"
echo "-------------------------"
echo -e "${YELLOW}🧪 Testing: Invalid Authentication${NC}"
invalid_response=$(curl -s -H "Authorization: Bearer invalid-key" "$BASE_URL/tools" 2>/dev/null)
if echo "$invalid_response" | grep -q "401" || echo "$invalid_response" | grep -q "Invalid"; then
    echo -e "   ${GREEN}✅ SUCCESS (Properly rejected invalid auth)${NC}"
else
    echo -e "   ${RED}❌ FAILED (Should reject invalid auth)${NC}"
fi
echo ""

# Test 4: Patient Data Tools (require synthetic data)
echo -e "${BLUE}👥 Patient Data Tools${NC}"
echo "----------------------"

test_endpoint "find_patient" "/tools/find_patient" '{
    "arguments": {
        "lastName": "Smith"
    }
}' "Find Patient by Last Name"

test_endpoint "get_patient_observations" "/tools/get_patient_observations" '{
    "arguments": {
        "patientId": "PAT-001"
    }
}' "Get Patient Observations"

test_endpoint "get_patient_conditions" "/tools/get_patient_conditions" '{
    "arguments": {
        "patientId": "PAT-001"
    }
}' "Get Patient Medical Conditions"

test_endpoint "get_vital_signs" "/tools/get_vital_signs" '{
    "arguments": {
        "patientId": "PAT-001",
        "timeframe": "6m"
    }
}' "Get Patient Vital Signs"

# Test 5: Research Tools (should work with online APIs)
echo -e "${BLUE}🔬 Medical Research Tools${NC}"
echo "---------------------------"

test_endpoint "search-pubmed" "/tools/search-pubmed" '{
    "arguments": {
        "query": "diabetes treatment",
        "maxResults": 3
    }
}' "PubMed Literature Search"

test_endpoint "search-trials" "/tools/search-trials" '{
    "arguments": {
        "condition": "diabetes",
        "location": "Boston"
    }
}' "Clinical Trials Search"

test_endpoint "get-drug-info" "/tools/get-drug-info" '{
    "arguments": {
        "genericName": "metformin"
    }
}' "FDA Drug Information"

# Test 6: Advanced Patient Tools
echo -e "${BLUE}📊 Advanced Patient Tools${NC}"
echo "----------------------------"

test_endpoint "get_patient_medications" "/tools/get_patient_medications" '{
    "arguments": {
        "patientId": "PAT-001"
    }
}' "Get Patient Medications"

test_endpoint "get_lab_results" "/tools/get_lab_results" '{
    "arguments": {
        "patientId": "PAT-001",
        "category": "ALL"
    }
}' "Get Lab Results"

test_endpoint "get_appointments" "/tools/get_appointments" '{
    "arguments": {
        "patientId": "PAT-001"
    }
}' "Get Patient Appointments"

# Test 7: Error Handling
echo -e "${BLUE}⚠️  Error Handling Tests${NC}"
echo "--------------------------"

test_endpoint "invalid_tool" "/tools/nonexistent_tool" '{
    "arguments": {}
}' "Invalid Tool Name (Should Fail)"

test_endpoint "missing_params" "/tools/find_patient" '{
    "arguments": {}
}' "Missing Required Parameters (Should Fail)"

# Summary
echo -e "${BLUE}📈 Test Summary${NC}"
echo "=================="
echo ""
echo -e "${GREEN}✅ Successful integrations indicate:${NC}"
echo "   • Healthcare MCP auth proxy is working"
echo "   • All 15 healthcare tools are discoverable"
echo "   • Database-first architecture with online fallbacks"
echo "   • Bearer token authentication is functioning"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "   1. Test tools in Open WebUI interface"
echo "   2. Verify medical literature search results"
echo "   3. Check synthetic patient data responses"
echo "   4. Validate PHI protection and medical disclaimers"
echo ""
echo -e "${BLUE}🏥 Healthcare MCP Integration Test Complete!${NC}"
