# Medical Mirrors Service

Local mirrors for Healthcare MCP API sources providing unlimited access to medical literature, clinical trials, and drug information without external API rate limits.

## Overview

The Medical Mirrors service creates comprehensive local mirrors of three major medical data sources:
- **PubMed** - Medical literature and research papers
- **ClinicalTrials.gov** - Clinical trial information
- **FDA Databases** - Drug information from Orange Book, NDC Directory, and Drug@FDA

## Architecture

```
services/user/medical-mirrors/
├── medical-mirrors.conf          # Docker service configuration
├── Dockerfile                    # Container definition
├── requirements.txt              # Python dependencies
├── src/                          # Source code
│   ├── main.py                   # FastAPI application
│   ├── config.py                 # Configuration settings
│   ├── database.py               # Database models and connection
│   ├── pubmed/                   # PubMed mirror components
│   │   ├── downloader.py         # Download XML from NCBI FTP
│   │   ├── parser.py             # Parse PubMed XML files
│   │   └── api.py                # Search API
│   ├── clinicaltrials/           # ClinicalTrials.gov mirror
│   │   ├── downloader.py         # Download JSON from API
│   │   ├── parser.py             # Parse study data
│   │   └── api.py                # Search API
│   └── fda/                      # FDA databases mirror
│       ├── downloader.py         # Download FDA datasets
│       ├── parser.py             # Parse drug data
│       └── api.py                # Search API
├── migrations/                   # Database migrations
└── update-scripts/               # Automated update scripts
    ├── update_pubmed.sh          # Daily PubMed updates
    ├── update_trials.sh          # Weekly trials updates
    ├── update_fda.sh             # Monthly FDA updates
    └── update_all.sh             # Master update script
```

## Database Design

### PostgreSQL Tables

- **pubmed_articles** - PubMed articles with full-text search
- **clinical_trials** - ClinicalTrials.gov studies
- **fda_drugs** - FDA drug information
- **update_logs** - Update history and status

### Full-Text Search

All tables include PostgreSQL `tsvector` fields for optimized full-text search:
- PubMed: title, abstract, authors, MeSH terms
- Trials: title, conditions, interventions, locations, sponsors
- FDA: drug names, ingredients, manufacturer, therapeutic class

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /status` - All mirrors status and data freshness

### PubMed Mirror
- `GET /pubmed/search?query=diabetes&max_results=10` - Search articles
- `GET /pubmed/article/{pmid}` - Get specific article

### ClinicalTrials Mirror
- `GET /trials/search?condition=diabetes&location=boston&max_results=10` - Search trials
- `GET /trials/study/{nct_id}` - Get specific trial

### FDA Mirror
- `GET /fda/search?generic_name=insulin&max_results=10` - Search drugs
- `GET /fda/drug/{ndc}` - Get specific drug

### Update Triggers
- `POST /update/pubmed` - Trigger PubMed update
- `POST /update/trials` - Trigger trials update
- `POST /update/fda` - Trigger FDA update

## Healthcare MCP Integration

The service provides drop-in replacement APIs that match the existing Healthcare MCP tool interfaces:

### PubMed Integration
- Replaces external NCBI E-utilities API calls
- Maintains same response format as `search-pubmed` tool
- Automatic fallback to external API if local mirror unavailable

### ClinicalTrials Integration
- Replaces external ClinicalTrials.gov API calls
- Maintains same response format as `search-trials` tool
- Supports condition and location filtering

### FDA Integration
- Replaces external openFDA API calls
- Maintains same response format as `get-drug-info` tool
- Eliminates 240 requests/minute rate limit

## Data Sources & Updates

### PubMed Data
- **Source**: NCBI FTP (ftp://ftp.ncbi.nlm.nih.gov/pubmed/)
- **Format**: XML (gzipped)
- **Update**: Daily incremental updates
- **Baseline**: Full dataset on initialization

### ClinicalTrials Data
- **Source**: ClinicalTrials.gov API v2
- **Format**: JSON
- **Update**: Weekly full refresh
- **Coverage**: All registered clinical trials

### FDA Data
- **Sources**: 
  - openFDA NDC Directory
  - openFDA Drugs@FDA
  - FDA Orange Book
  - FDA Drug Labels
- **Format**: JSON, CSV, TXT
- **Update**: Monthly full refresh
- **Coverage**: All FDA-approved drugs

## Setup Instructions

### 1. Deploy Service

The service is configured as a Docker container in the services/user/ directory:

```bash
# Service will be available at http://172.20.0.20:8080
# Database connection: postgresql://intelluxe:password@172.20.0.13:5432/intelluxe
```

### 2. Initialize Database

```bash
# Run database migrations
python migrations/001_initial_schema.py
```

### 3. Initialize Data

The service will automatically download and process initial datasets on first run. This process may take several hours:

- PubMed: ~5GB of XML files, millions of articles
- ClinicalTrials: ~500MB of JSON, hundreds of thousands of trials  
- FDA: ~1GB of various formats, hundreds of thousands of drugs

### 4. Configure Healthcare MCP

The Healthcare MCP connectors are automatically updated to use local mirrors by default. Set environment variable to disable:

```bash
USE_LOCAL_MEDICAL_MIRRORS=false  # Use external APIs
```

### 5. Schedule Updates

Add cron jobs for regular data updates:

```bash
# Daily PubMed updates at 2 AM
0 2 * * * /app/update-scripts/update_pubmed.sh

# Weekly trial updates on Sundays at 3 AM  
0 3 * * 0 /app/update-scripts/update_trials.sh

# Monthly FDA updates on 1st at 4 AM
0 4 1 * * /app/update-scripts/update_fda.sh
```

## Performance

### Search Performance
- Full-text search using PostgreSQL GIN indexes
- Sub-second response times for typical queries
- Supports complex search queries with ranking

### Storage Requirements
- PubMed: ~20GB (articles + indexes)
- ClinicalTrials: ~2GB (studies + indexes)
- FDA: ~5GB (drugs + indexes)
- Total: ~30GB disk space

### Update Performance
- PubMed daily: ~100MB, 10-15 minutes
- Trials weekly: ~500MB, 30-45 minutes
- FDA monthly: ~1GB, 60-90 minutes

## Healthcare Compliance

### Data Sources
- All data sourced from official government/public repositories
- PubMed: Public domain medical literature
- ClinicalTrials.gov: Federally mandated trial registry
- FDA: Official drug approval and safety data

### Privacy & Security
- No PHI (Protected Health Information) stored
- Public domain data only
- Same data available through external APIs
- Complies with existing Healthcare MCP security patterns

### Disclaimers
- For research and administrative use only
- Not for medical diagnosis or treatment decisions
- Healthcare compliance disclaimers maintained in all API responses

## Monitoring & Logging

### Health Checks
- Database connectivity
- Data freshness indicators
- Update success/failure status
- Service availability metrics

### Logging
- Structured logging with configurable levels
- Update history tracking in database
- Error reporting for failed updates
- Performance metrics collection

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Verify PostgreSQL service is running
   - Check connection string in environment

2. **Data Download Failed**
   - Check internet connectivity
   - Verify data source URLs are accessible
   - Review disk space availability

3. **Search Returns No Results**
   - Verify data initialization completed
   - Check search vector updates
   - Review query syntax

4. **Healthcare MCP Fallback**
   - Local mirror automatically falls back to external APIs
   - Check logs for fallback triggers
   - Verify mirror service availability

### Performance Tuning

1. **Database Optimization**
   - Monitor index usage
   - Adjust PostgreSQL memory settings
   - Consider partitioning for large datasets

2. **Search Optimization**
   - Use specific search terms
   - Limit result counts for large queries
   - Consider search term preprocessing

## Development

### Adding New Data Sources

1. Create downloader module
2. Create parser module  
3. Create API module
4. Add database model
5. Update main.py endpoints
6. Add update script
7. Update Healthcare MCP connector

### Testing

```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# API tests
python -m pytest tests/api/
```

## Support

For issues related to the Medical Mirrors service:
1. Check service logs: `/app/logs/`
2. Verify database status: `GET /status`
3. Test individual endpoints: `GET /health`
4. Review update logs: `update_logs` table

The service provides unlimited access to medical data for Healthcare AI workflows while maintaining compatibility with existing Healthcare MCP tools.
