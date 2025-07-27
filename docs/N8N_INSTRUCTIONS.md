## Phase 8: n8n Integration - Detailed Instructions

### 8.1 Access n8n and Create New Workflow

**Step 1: Access n8n Interface**
```bash
# Open your browser and navigate to:
http://localhost:5678

# If you have authentication enabled, log in with your credentials
```

**Step 2: Create New Workflow**
1. Click "New Workflow" button in the top right
2. Name it: "Clinical AI Assistant Pipeline"
3. Add description: "Processes audio transcripts through AI for clinical insights"

### 8.2 Build the Clinical Workflow

**Step 1: Add Webhook Trigger Node**
1. Click the "+" button to add a new node
2. Search for "Webhook" and select it
3. Configure:
   - **Webhook URL**: `clinical-webhook`
   - **HTTP Method**: POST
   - **Response Mode**: "Immediately"
   - **Response Code**: 200
   - **Response Data**: "First Entry JSON"

4. Click "Listen for Test Event" to get the full webhook URL
   - It will be something like: `http://localhost:5678/webhook/clinical-webhook`

**Step 2: Add Session Update Node (HTTP Request)**
1. Add a new "HTTP Request" node
2. Connect it to the Webhook node
3. Configure:
   - **Method**: POST
   - **URL**: `http://clinical-session:8090/session/{{ $json.sessionId }}/append`
   - **Authentication**: None
   - **Send Body**: Yes
   - **Body Content Type**: JSON
   - **Body**:
   ```json
   {
     "text": "{{ $json.transcript }}",
     "timestamp": "{{ $now.toISO() }}"
   }
   ```

**Step 3: Add Decision Node (IF)**
1. Add an "IF" node
2. Connect it to the Session Update node
3. Configure conditions:
   - **Value 1**: `{{ $json.triggerAnalysis }}`
   - **Operation**: "Equal"
   - **Value 2**: `true`

**Step 4: Add AgentCare-MCP Analysis Node (HTTP Request)**
1. Add another "HTTP Request" node
2. Connect it to the TRUE output of the IF node
3. Configure:
   - **Method**: POST
   - **URL**: `http://healthcare-mcp:3000/v1/messages`
   - **Send Body**: Yes
   - **Body Content Type**: JSON
   - **Body**:
   ```json
   {
     "messages": [
       {
         "role": "system",
         "content": "You are a medical AI assistant. Analyze the following clinical conversation and provide relevant insights."
       },
       {
         "role": "user", 
         "content": "{{ $json.sessionContext.recentTranscript }}"
       }
     ],
     "model": "meditron-7b",
     "temperature": 0.3
   }
   ```

**Step 5: Add Response Processing Node (Code)**
1. Add a "Code" node (JavaScript)
2. Connect it to the AgentCare-MCP node
3. Add code:
```javascript
// Extract relevant insights from AI response
const aiResponse = $input.first().json;
const insights = aiResponse.choices?.[0]?.message?.content || '';

// Parse for specific clinical alerts
const hasUrgentFlag = insights.toLowerCase().includes('urgent') || 
                      insights.toLowerCase().includes('immediate');

// Structure the response
return {
  json: {
    sessionId: $node["Webhook"].json.sessionId,
    insights: insights,
    urgent: hasUrgentFlag,
    timestamp: new Date().toISOString(),
    // Extract any medication mentions
    medications: insights.match(/\b(?:prescribe|medication|drug):\s*([^\n,]+)/gi) || [],
    // Extract any diagnosis mentions  
    diagnoses: insights.match(/\b(?:diagnosis|condition):\s*([^\n,]+)/gi) || []
  }
};
```

**Step 6: Add Notification Router (Switch)**
1. Add a "Switch" node
2. Connect it to the Code node
3. Configure routing rules:
   - **Rule 1**: `{{ $json.urgent }}` equals `true` → Route to "Urgent Alert"
   - **Rule 2**: `{{ $json.medications.length }}` greater than `0` → Route to "Medication Alert"
   - **Rule 3**: Default → Route to "Standard Update"

**Step 7: Add Alert Nodes**

**Urgent Alert (HTTP Request):**
```json
{
  "method": "POST",
  "url": "http://your-ui:3000/api/alerts/urgent",
  "body": {
    "sessionId": "{{ $json.sessionId }}",
    "message": "{{ $json.insights }}",
    "type": "urgent"
  }
}
```

**Medication Alert (HTTP Request):**
```json
{
  "method": "POST", 
  "url": "http://your-ui:3000/api/alerts/medication",
  "body": {
    "sessionId": "{{ $json.sessionId }}",
    "medications": "{{ $json.medications }}",
    "insights": "{{ $json.insights }}"
  }
}
```

### 8.3 Configure Error Handling

**Step 1: Add Error Trigger**
1. Click on any node
2. Go to "Settings" tab
3. Enable "Continue On Fail"
4. Add error output

**Step 2: Add Error Logger Node**
```javascript
// Error logging node
const error = $input.first().error;
const nodeName = $input.first().nodeName;

console.error(`Error in ${nodeName}:`, error);

// Send to monitoring
return {
  json: {
    error: error.message,
    node: nodeName,
    timestamp: new Date().toISOString(),
    workflow: 'Clinical AI Assistant'
  }
};
```

### 8.4 Test the Workflow

**Step 1: Enable Test Mode**
1. Click "Execute Workflow" button
2. Keep the workflow in test mode

**Step 2: Send Test Webhook**
```bash
# Test with a simple transcript
curl -X POST http://localhost:5678/webhook/clinical-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-001",
    "transcript": "Patient reports severe chest pain for the last 2 hours"
  }'
```

**Step 3: Verify Each Node**
1. Click on each node to see the output
2. Check for any errors in red
3. Verify the data flow is correct

**Step 4: Test Different Scenarios**
```bash
# Test non-urgent case
curl -X POST http://localhost:5678/webhook/clinical-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-002",
    "transcript": "Patient mentions mild seasonal allergies"
  }'

# Test medication mention
curl -X POST http://localhost:5678/webhook/clinical-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-003",
    "transcript": "Discussing whether to prescribe amoxicillin for infection"
  }'
```

### 8.5 Production Deployment

**Step 1: Save and Activate**
1. Click "Save" button
2. Toggle the workflow to "Active" 
3. Note the workflow ID for monitoring

**Step 2: Add Monitoring**
Create a monitoring webhook in n8n:
```json
{
  "name": "Workflow Monitor",
  "trigger": "Every 5 minutes",
  "actions": [
    {
      "type": "Check workflow status",
      "workflowId": "YOUR_WORKFLOW_ID"
    }
  ]
}
```

**Step 3: Configure Persistence**
Ensure n8n data persists:
```bash
# Check your n8n.conf has proper volume mapping
VOLUMES="./data:/home/node/.n8n ./workflows:/workflows"
```

### 8.6 Integration Testing

**Complete End-to-End Test:**
```bash
# 1. Start all services
./clinic-bootstrap.sh
# Select: ollama, healthcare-mcp, clinical-session, n8n

# 2. Verify all services are running
docker ps | grep -E "(ollama|healthcare|clinical-session|n8n)"

# 3. Create a test session
SESSION_ID=$(curl -s -X POST http://localhost:8090/session/create \
  -H "Content-Type: application/json" \
  -d '{"doctorId": "dr-smith"}' | jq -r '.sessionId')

echo "Created session: $SESSION_ID"

# 4. Send test transcript through n8n
curl -X POST http://localhost:5678/webhook/clinical-webhook \
  -H "Content-Type: application/json" \
  -d "{
    \"sessionId\": \"$SESSION_ID\",
    \"transcript\": \"Patient presents with headache and fever of 101.5F\"
  }"

# 5. Check session was updated
curl http://localhost:8090/session/$SESSION_ID/status

# 6. Monitor n8n execution
# Go to n8n UI > Executions to see the results
```

### 8.7 Troubleshooting

**Common Issues:**

1. **Service Discovery Problems**
   ```bash
   # If services can't find each other, check network
   docker network inspect clinical-net
   
   # Ensure all services are on same network
   docker inspect healthcare-mcp | grep NetworkMode
   ```

2. **Webhook Not Receiving**
   ```bash
   # Test webhook directly
   docker exec -it n8n wget -qO- http://localhost:5678/webhook/clinical-webhook
   ```

3. **AgentCare-MCP Connection Issues**
   ```bash
   # Test MCP endpoint
   docker exec -it n8n curl http://healthcare-mcp:3000/health
   ```

**Debug Mode:**
In n8n workflow:
1. Add "Console" nodes between steps
2. Log all JSON data
3. Check execution history for errors

This completes the detailed n8n integration phase. The workflow will now automatically process incoming transcripts, analyze them with AI, and route alerts appropriately.
