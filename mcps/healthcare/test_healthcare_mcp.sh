#!/bin/bash

echo "🏥 Healthcare MCP Server Test Suite"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://host.docker.internal:3000"

test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    
    echo -e "\n${YELLOW}Testing: $name${NC}"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" "$url")
        http_code="${response: -3}"
        body="${response%???}"
    else
        response=$(curl -s -w "%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
        http_code="${response: -3}"
        body="${response%???}"
    fi
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        echo "$body" | jq . 2>/dev/null || echo "$body"
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "$body"
    fi
}

# Test 1: Health Check
test_endpoint "Health Check" "GET" "$BASE_URL/health"

# Test 2: Tools List
test_endpoint "Tools List" "POST" "$BASE_URL/mcp" \
    '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# Test 3: PubMed Search
test_endpoint "PubMed Search" "POST" "$BASE_URL/mcp" \
    '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search-pubmed","arguments":{"query":"covid","maxResults":2}},"id":1}'

# Test 4: Clinical Trials
test_endpoint "Clinical Trials Search" "POST" "$BASE_URL/mcp" \
    '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search-trials","arguments":{"condition":"diabetes"}},"id":1}'

# Test 5: FDA Drug Info
test_endpoint "FDA Drug Info" "POST" "$BASE_URL/mcp" \
    '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get-drug-info","arguments":{"genericName":"ibuprofen"}},"id":1}'

# Test 6: Patient Search
test_endpoint "Patient Search" "POST" "$BASE_URL/mcp" \
    '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"find_patient","arguments":{"lastName":"Smith"}},"id":1}'

# Test 7: Error Handling
test_endpoint "Error Handling (Invalid Tool)" "POST" "$BASE_URL/mcp" \
    '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"invalid_tool","arguments":{}},"id":1}'

echo -e "\n${YELLOW}Test Suite Complete!${NC}"
