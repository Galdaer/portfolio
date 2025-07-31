# Practice-Level API Key Deployment Guide

## Overview

Intelluxe AI uses **practice-level API keys** for healthcare integrations. Each medical practice/clinic gets one set of API keys shared across all doctors and staff.

## API Key Scoping

### ✅ Recommended: Practice-Level Keys

```
Dr. Smith Family Practice
├── 5 doctors + 15 staff
├── Epic API Key: "smith_practice_epic_2024"
├── PubMed API Key: "smith_practice_nlm_2024"
└── All users share same keys with individual authentication
```

**Benefits:**

- **Cost effective** - $200/month vs $1000/month (5 doctors × $200 each)
- **Easier management** - One set of credentials per practice
- **HIPAA compliant** - Practice is the "covered entity"
- **Team collaboration** - Doctors in practice share patient data anyway

### 🚫 Not Recommended: Individual Doctor Keys

```
Dr. Smith Practice
├── Dr. Smith: Epic key #1 ($200/month)
├── Dr. Jones: Epic key #2 ($200/month)
├── Dr. Wilson: Epic key #3 ($200/month)
└── Total: $600/month for same functionality
```

## Deployment Process

### 1. Practice receives universal Docker image

```bash
# Same image for all practices
docker pull intelluxe/healthcare-mcp:latest
```

### 2. Practice configures their .env file

```bash
# Copy template and fill in practice-specific values
cp .env.example .env

# Edit with practice's actual API keys
vim .env
```

### 3. Deploy with practice configuration

```bash
# Start with practice-specific environment
./bootstrap.sh
```

## Example Practice Configurations

### Small Practice (Epic Integration)

```env
# Dr. Johnson Family Medicine (3 doctors, 8 staff)
FHIR_BASE_URL=https://epic.johnsonmed.com/fhir/r4
OAUTH_CLIENT_ID=johnson_practice_epic_client_2024
OAUTH_CLIENT_SECRET=johnson_practice_epic_secret_2024
PUBMED_API_KEY=johnson_practice_nlm_key_2024
```

### Large Practice (Cerner Integration)

```env
# Metro Health Associates (15 doctors, 45 staff)
FHIR_BASE_URL=https://cerner.metrohealth.com/fhir/r4
OAUTH_CLIENT_ID=metro_health_cerner_client_2024
OAUTH_CLIENT_SECRET=metro_health_cerner_secret_2024
PUBMED_API_KEY=metro_health_nlm_key_2024
```

### Multi-Location Practice

```env
# Regional Medical Group (3 locations, 25 doctors)
FHIR_BASE_URL=https://epic.regionalmed.com/fhir/r4
OAUTH_CLIENT_ID=regional_med_epic_client_2024
OAUTH_CLIENT_SECRET=regional_med_epic_secret_2024
PUBMED_API_KEY=regional_med_nlm_key_2024
# Same keys used across all 3 locations
```

## Security Within Practice

### Individual User Tracking

Even with shared API keys, individual users are tracked:

```json
{
  "practice_api_key": "johnson_practice_epic_2024",
  "user_id": "dr.martinez@johnsonmed.com",
  "session_id": "session_abc123",
  "patient_context": "patient_456",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Audit Logging

All API calls are logged with:

- Practice identifier
- Individual user making the request
- Patient accessed (if applicable)
- Timestamp and action taken
- Session information

## Cost Comparison

### Practice-Level Keys (Recommended)

```
Epic API: $200/month per practice
PubMed API: Free (reasonable usage)
Total: $200/month for entire practice
```

### Individual Doctor Keys (Not Recommended)

```
Epic API: $200/month × 5 doctors = $1000/month
PubMed API: Free
Total: $1000/month for same functionality
```

## Getting API Keys

### Epic (MyChart Integration)

1. Contact Epic App Orchard: appmarket@epic.com
2. Request sandbox access for development
3. Apply for production keys after testing
4. Expect 2-4 week approval process

### Cerner (HealtheLife Integration)

1. Register at: https://fhir.cerner.com/
2. Request sandbox access
3. Apply for production after development
4. Expect 1-3 week approval process

### PubMed/NCBI

1. Register at: https://www.ncbi.nlm.nih.gov/account/
2. Request API key (usually instant)
3. Free for reasonable usage
4. Rate limits: 10 requests/second

## Support

For deployment assistance:

- Email: support@intelluxe.ai
- Documentation: docs.intelluxe.ai/deployment
- Practice onboarding: Available for enterprise customers

This approach ensures cost-effective, secure, and compliant deployment across healthcare practices of all sizes.
