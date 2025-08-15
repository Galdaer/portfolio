# Intelluxe AI Setup & Testing Plan

**Your Role:** Set up n8n workflows using running services, then test real healthcare scenarios to validate clinical usefulness.

## How This Works

1. **Deploy services** using the phase documentation
2. **Configure n8n workflows** to connect services
3. **Test workflows** with realistic medical scenarios
4. **Document results** for clinical validation

---

## Phase 1: Core AI System Setup

### Running Services
```
✓ Ollama AI: http://172.20.0.10:11434
✓ Healthcare-MCP: http://localhost:3000
✓ Health Monitor: http://localhost:8080
✓ PostgreSQL: localhost:5432
✓ Redis: localhost:6379
```

### n8n Workflow Setup Tasks

**1. Create "AI Query" Workflow**
```
HTTP Request Node:
- URL: http://172.20.0.10:11434/api/generate
- Method: POST
- Body: {"model": "intelluxe-medical", "prompt": "{{$node["Start"].json["query"]}}"}

Test with: "Explain hypertension management guidelines"
Expected: Professional medical summary
```

**2. Create "Research Assistant" Workflow**
```
HTTP Request Node:
- URL: http://localhost:3000/tools/pubmed/search
- Method: POST  
- Body: {"query": "{{$node["Start"].json["query"]}}"}

Test with: "Latest insulin guidelines"
Expected: Results with PubMed citations
```

**3. Create "Health Monitor" Workflow**
```
HTTP Request Node:
- URL: http://localhost:8080/check
- Method: GET

Run: Every 5 minutes
Expected: All services "healthy"
```

---

## Phase 2: Business Services Setup

### Additional Services
```
✓ Insurance Verification: http://localhost:8003
✓ Billing Engine: http://localhost:8004
✓ Compliance Monitor: http://localhost:8005
✓ Audio Receiver: https://localhost:8443
```

### Business Workflow Tasks

**1. Create "Insurance Verification" Workflow**
```
HTTP Request Node:
- URL: http://localhost:8003/verify
- Method: POST
- Body: {
    "member_id": "{{$node["Start"].json["member_id"]}}",
    "provider_id": "{{$node["Start"].json["provider_id"]}}",
    "service_codes": {{$node["Start"].json["service_codes"]}}
  }

Test with: Real insurance member IDs
Expected: Eligibility status and coverage details
```

**2. Create "Billing Pipeline" Workflow**
```
Chain multiple nodes:
1. Insurance Verification (as above)
2. Billing Engine:
   - URL: http://localhost:8004/create_claim
   - Method: POST
   - Body: Complete claim data

Test: End-to-end claim creation
Expected: Claim ID and patient responsibility
```

**3. Create "Compliance Audit" Workflow**
```
HTTP Request Node:
- URL: http://localhost:8005/log_access
- Method: POST
- Body: Access attempt details

Trigger: On every patient data access
Expected: Audit trail created
```

---

## Phase 3: Advanced Workflows

### Complete Patient Visit Workflow
```
n8n Workflow Chain:
1. Process intake form → Extract patient data
2. Research current guidelines → Get latest protocols  
3. Generate assessment → AI summary with personalization
4. Lookup billing codes → Appropriate CPT codes
5. Create follow-up plan → Template with next steps

End-to-end test with realistic patient scenario
Time target: Under 5 minutes
```

### Voice Integration Setup (if available)
```
HTTP Request Node:
- URL: http://localhost:8083/voice
- Method: POST
- Body: {"audio": "base64_encoded_audio"}

Test: Record "What are ACE inhibitor side effects?"
Expected: Audio response with medical information
```

---

## Daily Operations

### Morning Setup Check (5 minutes)
```
1. Run "Health Monitor" workflow
2. Test basic AI query: "What is diabetes?"
3. Check monitoring dashboard: http://localhost:3001
4. Note any issues in logbook
```

### Weekly Clinical Validation (30 minutes)
```
1. Test 5 realistic patient scenarios
2. Verify medical accuracy of responses
3. Document workflow efficiency gains
4. Report any clinical concerns
```

### Quality Assessment Metrics
Track these for each workflow:
- **Response Time:** Under 30 seconds
- **Accuracy:** Medical information correct
- **Usefulness:** Saves time vs manual lookup
- **Safety:** No inappropriate medical advice

---

## Issue Reporting Workflow

Create n8n workflow for reporting issues:
```
HTTP Request Node:
- URL: http://localhost:9000/issues
- Method: POST
- Body: {
  "timestamp": "{{$now}}",
  "workflow": "{{$node["Start"].json["workflow"]}}",
  "issue": "{{$node["Start"].json["description"]}}",
  "expected": "{{$node["Start"].json["expected"]}}",
  "actual": "{{$node["Start"].json["actual"]}}"
}
```

---

## Success Criteria

**Phase 1 Ready:**
- All workflows respond within 30 seconds
- Medical information is accurate and appropriate
- Document processing handles real forms
- System stable during normal clinic hours

**Phase 2 Ready:**
- Personalized responses feel authentic
- Multiple doctor styles work consistently
- Training process completes reliably
- Quality maintained across all profiles

**Phase 3 Ready:**
- Complex workflows complete end-to-end
- Performance suitable for busy clinic
- Advanced features provide real value
- Ready for live patient scenarios

**Clinical Deployment Ready:**
- Processes 50+ patient interactions without issues
- Maintains medical accuracy under load
- Integrates smoothly with clinic workflow
- Staff can use without technical training