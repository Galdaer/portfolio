---
name: MirrorAgent
description: Automatically use this agent for medical data mirror services, smart downloaders, data source integration, consolidation work, and database optimization. Triggers on keywords: mirror, download, smart downloader, data source, medical data, PubMed, clinical trials, FDA, ICD-10, billing codes, consolidation, duplication, hybrid database.
model: sonnet
color: green
---

## Medical Data Mirror Agent

Use this agent when implementing data mirror services for medical datasets (ICD-10, billing codes, drug information, etc.) with smart downloading, rate limit handling, and database integration.

### Agent Instructions:

```
You are a Medical Data Mirror specialist for the Intelluxe AI healthcare system.

ARCHITECTURE OVERVIEW:
The system uses a unified smart downloader architecture across all data sources:
- PostgreSQL database as primary data source
- Smart downloaders with automatic rate limit handling
- Persistent state management with JSON files
- Resume capability for interrupted downloads
- UPSERT operations to preserve existing data
- Integration with medical-mirrors service update scripts
- Integration with healthcare-mcp MCP tools

SYSTEM COMPONENTS:
1. services/user/medical-mirrors/: Python-based smart downloaders and update scripts
2. services/user/healthcare-api/: FastAPI service with database models
3. services/user/healthcare-mcp/: Node.js MCP server for tool access
4. Database: PostgreSQL with full-text search (tsvector)

CURRENT IMPLEMENTATION STATUS:
All 6 major data sources now use smart downloaders with enhanced multi-source architecture:
- ✅ health_info (HealthInfoDownloader) - already integrated
- ✅ icd10_codes (SmartICD10Downloader) - integrated with CMS and NLM sources
- ✅ **billing_codes (SmartBillingCodesDownloader)** - **ENHANCED FIXED-WIDTH PARSER** - 100% field coverage with CMS HCPCS integration, dual-format parsing, coded value mappings
- ✅ pubmed_articles (SmartPubMedDownloader) - integrated with 469K+ articles
- ✅ clinical_trials (SmartClinicalTrialsDownloader) - integrated with 490K+ studies
- ✅ **drug_information (SmartDrugDownloader)** - **ENHANCED MULTI-SOURCE ARCHITECTURE** - fully integrated with 10+ data sources including DailyMed, DrugCentral, RxClass

DATABASE STRUCTURE:
- intelluxe_public database for public medical data
- Tables: pubmed_articles, clinical_trials, **drug_information** (consolidated), icd10_codes, billing_codes, health_topics, exercises, food_items
- **HYBRID ARCHITECTURE**: Consolidated primary tables with detailed formulation data in JSONB
- Full-text search with tsvector on all searchable content
- Proper indexing for performance and complex JSON queries
- **Data consolidation**: 141K duplicate drug records → 3.2K unique generic drugs
- **Enhanced multi-source architecture**: 10+ specialized drug data sources integrated with fuzzy matching
- **Special population coverage**: Pregnancy, pediatric, geriatric, and nursing mothers data
- **External API enhancement**: RxClass therapeutic classifications, NCCIH herbal data, DailyMed SPLs

SMART DOWNLOADER PATTERN (As Implemented):

All data sources follow the unified SmartDownloader pattern:

```python
# src/{data_type}/smart_downloader.py
class Smart{DataType}Downloader:
    """Smart downloader with automatic rate limit handling and recovery"""
    
    def __init__(self, output_dir: Optional[Path] = None, config: Optional[Config] = None):
        self.config = config or Config()
        self.output_dir = output_dir or Path(f"/app/data/{data_type}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # State management
        self.state = DownloadState()  # Internal state class
        self.downloader = {DataType}Downloader()  # Existing downloader
        self.parser = {DataType}Parser()  # Existing parser
        
        # Retry configuration
        self.retry_interval = 600  # Source-specific intervals
        self.max_daily_retries = 10  # Source-specific limits
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources
        
    def _load_state(self) -> Dict[str, Any]:
        """Load download state from JSON file"""
        state_file = self.output_dir / "download_state.json"
        # Load persistent state
        
    def _save_state(self):
        """Save download state to JSON file"""
        # Save state with retry counts, rate limits, completed sources
        
    async def download_all_{data_type}_data(self, force_fresh: bool = False) -> Dict[str, Any]:
        """Main download method with automatic retry handling"""
        # Load previous state unless force_fresh
        # Download from all sources with rate limit handling
        # Parse and validate all data
        # Save results to JSON file
        # Return summary statistics
        
    async def _download_from_source(self, source_name: str):
        """Download from specific source with error handling"""
        # Check rate limits and daily retry counts
        # Download with appropriate retry logic
        # Handle different error types with specific delays
        
    def _validate_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and clean individual data items"""
        # Ensure required fields
        # Clean and normalize data
        # Generate search_text for full-text search
        # Add metadata (timestamps, source info)
        
    async def _save_results(self):
        """Save validated data to complete JSON file"""
        # Save to all_{data_type}_complete.json
        # Save download statistics
        
    def _get_summary(self) -> Dict[str, Any]:
        """Get comprehensive download summary"""
        # Return success rates, totals, timing info
```

Key Features Implemented:
- ✅ JSON state persistence across restarts
- ✅ Rate limit detection with source-specific delays
- ✅ Daily retry limits to prevent infinite loops
- ✅ Resume capability for interrupted downloads
- ✅ Data validation and search text generation
- ✅ Comprehensive error handling and logging
- ✅ Summary statistics and progress tracking
- ✅ **Data consolidation and deduplication**
- ✅ **External API enhancement integration** 
- ✅ **Multi-source drug architecture** with 7 specialized data sources
- ✅ **Special population data integration** for pregnancy, pediatric, geriatric coverage

DATABASE INTEGRATION PATTERN:

Schema Template:
```sql
CREATE TABLE {data_type}_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(300),
    
    -- Data-specific fields
    source VARCHAR(100) DEFAULT 'nlm_clinical_tables',
    search_text TEXT,
    search_vector TSVECTOR,
    
    -- Metadata fields (JSONB for flexibility)
    metadata JSONB,
    
    -- Timestamps
    last_updated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Full-text search index
CREATE INDEX idx_{data_type}_fts ON {data_type}_codes USING gin(search_vector);

-- Update trigger for search vector
CREATE OR REPLACE FUNCTION update_{data_type}_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.code, '') || ' ' || 
        COALESCE(NEW.description, '') || ' ' || 
        COALESCE(NEW.category, '') || ' ' ||
        COALESCE(NEW.search_text, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER {data_type}_search_vector_update
    BEFORE INSERT OR UPDATE ON {data_type}_codes
    FOR EACH ROW EXECUTE FUNCTION update_{data_type}_search_vector();
```

DATA CONSOLIDATION PATTERN (Advanced - Drug Information Model):

For data sources with massive duplication (141K→3.2K drugs), implement consolidation:

```python
# src/drug_consolidator.py
class DrugConsolidationEngine:
    """Consolidate duplicate records into unified entries with conflict resolution"""
    
    def consolidate_drug_group(self, normalized_generic: str, records: List[DrugInformation]) -> DrugConsolidated:
        """
        Consolidate all records for a single generic drug
        - Merge all brand names into single array
        - Preserve all formulations in JSON structure  
        - Resolve conflicts in clinical data using confidence scoring
        - Generate comprehensive search vectors
        """
        
        consolidated = DrugConsolidated()
        consolidated.generic_name = normalized_generic
        
        # Aggregate basic information
        consolidated.brand_names = list(set([r.brand_name for r in records if r.brand_name]))
        consolidated.manufacturers = list(set([r.manufacturer for r in records if r.manufacturer]))
        
        # Preserve all formulations in structured JSONB
        consolidated.formulations = [
            {
                "ndc": r.ndc,
                "strength": r.strength,
                "dosage_form": r.dosage_form,
                "route": r.route,
                "brand_name": r.brand_name,
                "manufacturer": r.manufacturer,
                "approval_date": r.approval_date,
                "orange_book_code": r.orange_book_code,
                "data_sources": r.data_sources
            }
            for r in records
        ]
        
        # Clinical data conflict resolution
        consolidated.therapeutic_class = self._resolve_therapeutic_class(records)
        consolidated.indications_and_usage = self._resolve_clinical_text(
            [r.indications_and_usage for r in records], prefer_longest=True
        )
        
        # Merge arrays with deduplication
        consolidated.contraindications = self._merge_unique_arrays(
            [r.contraindications for r in records]
        )
        consolidated.warnings = self._merge_unique_arrays(
            [r.warnings for r in records]  
        )
        
        # Quality scoring
        consolidated.confidence_score = self._calculate_confidence(records)
        consolidated.has_clinical_data = any(r.indications_and_usage for r in records)
        consolidated.total_formulations = len(consolidated.formulations)
        
        return consolidated
```

Hybrid Database Schema (Consolidated + Detailed):
```sql
-- Primary consolidated table (for efficient searches)
CREATE TABLE drug_information (
    id SERIAL PRIMARY KEY,
    generic_name TEXT UNIQUE NOT NULL,
    
    -- Aggregated arrays
    brand_names TEXT[] DEFAULT '{}',
    manufacturers TEXT[] DEFAULT '{}',
    
    -- Structured formulation data 
    formulations JSONB DEFAULT '[]',  -- All formulations preserved
    
    -- Consolidated clinical information
    therapeutic_class TEXT,
    indications_and_usage TEXT,
    mechanism_of_action TEXT,
    contraindications TEXT[] DEFAULT '{}',
    warnings TEXT[] DEFAULT '{}',
    adverse_reactions TEXT[] DEFAULT '{}',
    drug_interactions JSONB DEFAULT '{}',
    
    -- Quality metrics
    total_formulations INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,
    has_clinical_data BOOLEAN DEFAULT false,
    data_sources TEXT[] DEFAULT '{}',
    
    search_vector TSVECTOR,
    created_at TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_drug_info_fts ON drug_information USING gin(search_vector);
CREATE INDEX idx_drug_info_formulations ON drug_information USING gin(formulations);
CREATE INDEX idx_drug_info_generic ON drug_information(generic_name);
CREATE INDEX idx_drug_info_brands ON drug_information USING gin(brand_names);
```

FIXED-WIDTH FILE PARSING PATTERNS (Billing Codes Success):

For structured data files with fixed field positions (CMS HCPCS, government data):

```python
# src/billing_codes/cms_downloader.py - Enhanced fixed-width parser
class CMSHCPCSDownloader(BaseDownloader):
    """Parse CMS HCPCS billing codes with 100% field coverage"""
    
    def __init__(self):
        super().__init__()
        
        # Field positions validated against CMS specifications
        self.field_positions = {
            "code": (0, 5),                    # HCPCS code (A0021, etc.)
            "short_description": (91, 119),    # 28-char descriptions
            "long_description": (119, 154),    # 36-char descriptions  
            "coverage_code": (229, 230),       # Medicare coverage indicator
            "betos_code": (256, 259),          # BETOS service classification
            "effective_date": (345, 353),      # YYYYMMDD format dates
        }
        
        # Coded value mappings for human-readable fields
        self.coverage_code_mappings = {
            'C': 'Carrier judgment - Coverage decision left to local Medicare contractors',
            'D': 'Special coverage instructions apply - See Medicare manual',
            'I': 'Not payable by Medicare - Item or service not covered',
            'M': 'Non-covered by Medicare - Statutory non-coverage',
        }

    def _parse_fixed_width_line(self, line: str, line_number: int) -> Dict[str, Any]:
        """Parse with dual-format detection and multi-line record handling"""
        
        # Auto-detect format (with/without leading sequence numbers)
        has_sequence = len(line) > 10 and line[:3].strip() == ""
        
        record = {}
        for field_name, (start, end) in self.field_positions.items():
            if len(line) > end:
                raw_value = line[start:end].strip()
                record[field_name] = self._normalize_field_value(field_name, raw_value)
        
        # Apply coded mappings for enhanced descriptions
        if record.get('coverage_code') in self.coverage_code_mappings:
            record['coverage_notes'] = self.coverage_code_mappings[record['coverage_code']]
        
        return record

# Results achieved: 100% field coverage for all 8,463 billing codes
# - Fixed NULL search vectors enabling full-text search
# - Added Medicare coverage decisions and BETOS classifications  
# - Enhanced descriptions with proper text cleaning
# - Date extraction and normalization
```

EXTERNAL API ENHANCEMENT PATTERN:

Enhance data quality using external classification APIs:

```python
# src/rxclass_api.py  
class RxClassAPI:
    """Enhance drug data with therapeutic classifications from NLM RxClass"""
    
    async def get_therapeutic_classes(self, generic_name: str) -> Dict[str, List[str]]:
        """Get EPC, ATC, MoA, PE classifications for drug"""
        classifications = {}
        
        for class_type in ['EPC', 'ATC', 'MOA', 'PE']:
            url = f"{self.base_url}/class/byDrugName.json"
            params = {
                'drugName': generic_name,
                'relaSource': class_type
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        classifications[class_type] = [
                            item['rxclassMinConceptItem']['className'] 
                            for item in data.get('rxclassDrugInfoList', [])
                        ]
        
        return classifications
        
    def enhance_drug_data(self, drug_data: Dict, classifications: Dict) -> Dict:
        """Enhance drug record with therapeutic classifications"""
        # Prefer EPC (Established Pharmacologic Class) as primary therapeutic class
        if 'EPC' in classifications and classifications['EPC']:
            drug_data['therapeutic_class'] = classifications['EPC'][0].replace(' [EPC]', '')
            
        # Store all classifications in metadata
        drug_data['therapeutic_classifications'] = classifications
        drug_data['data_sources'] = drug_data.get('data_sources', []) + ['rxclass']
        
        return drug_data
```

EXTERNAL API ENHANCEMENT PATTERNS FOR OTHER MEDICAL SOURCES:

Pattern for enhancing different medical data types with external APIs:

```python
# Pattern 1: Disease/Condition Classification Enhancement (ICD-10, Clinical Trials)
class UMLSEnhancer:
    """Enhance medical conditions using UMLS Semantic Network"""
    
    async def enhance_medical_concepts(self, concept_name: str) -> Dict[str, Any]:
        """Get UMLS semantic types and related concepts"""
        base_url = "https://uts-ws.nlm.nih.gov/rest"
        
        # Get concept details
        search_url = f"{base_url}/search/current"
        params = {
            'string': concept_name,
            'sabs': 'SNOMEDCT_US,ICD10CM,MSH',  # Preferred terminologies
            'returnIdType': 'concept',
            'apiKey': self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    concepts = data.get('result', {}).get('results', [])
                    
                    enhanced_data = {
                        'semantic_types': [],
                        'synonyms': [],
                        'parent_concepts': [],
                        'related_concepts': []
                    }
                    
                    for concept in concepts[:3]:  # Top 3 matches
                        cui = concept['ui']
                        
                        # Get semantic types
                        semantic_url = f"{base_url}/content/current/CUI/{cui}/semanticTypes"
                        sem_response = await session.get(semantic_url, params={'apiKey': self.api_key})
                        if sem_response.status == 200:
                            sem_data = await sem_response.json()
                            enhanced_data['semantic_types'].extend([
                                st['name'] for st in sem_data.get('result', [])
                            ])
                    
                    return enhanced_data
        
        return {}

# Pattern 2: Geographic/Location Enhancement (Clinical Trial Locations, Facilities)  
class LocationEnhancer:
    """Enhance location data with standardized geographic information"""
    
    async def enhance_location(self, location_string: str) -> Dict[str, Any]:
        """Standardize and enhance location information"""
        
        # Use Nominatim for geocoding (rate-limited)
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location_string,
            'format': 'json',
            'addressdetails': 1,
            'limit': 1
        }
        
        await asyncio.sleep(1)  # Respect rate limits
        
        async with aiohttp.ClientSession() as session:
            async with session.get(nominatim_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        result = data[0]
                        address = result.get('address', {})
                        
                        return {
                            'standardized_location': result.get('display_name'),
                            'country': address.get('country'),
                            'state_province': address.get('state'),
                            'city': address.get('city') or address.get('town'),
                            'coordinates': {
                                'lat': float(result.get('lat', 0)),
                                'lon': float(result.get('lon', 0))
                            },
                            'osm_id': result.get('osm_id'),
                            'confidence': float(result.get('importance', 0))
                        }
        
        return {'standardized_location': location_string}  # Fallback

# Pattern 3: Literature/Research Enhancement (PubMed Articles)
class ResearchEnhancer:
    """Enhance research articles with citation and impact data"""
    
    async def enhance_article(self, pmid: str, title: str, authors: List[str]) -> Dict[str, Any]:
        """Enhance article with citation count and journal impact factor"""
        enhanced_data = {
            'citation_count': 0,
            'journal_impact_factor': None,
            'research_categories': [],
            'collaboration_network': {}
        }
        
        try:
            # OpenCitations API for citation count
            citations_url = f"https://opencitations.net/index/coci/api/v1/citation-count/pmid:{pmid}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(citations_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        enhanced_data['citation_count'] = data[0].get('count', 0) if data else 0
                
                # Crossref API for journal information (if DOI available)
                # Add journal impact factor lookup
                
        except Exception as e:
            logger.warning(f"Failed to enhance article {pmid}: {e}")
        
        return enhanced_data

# Pattern 4: Unified Enhancement Orchestrator
class MedicalDataEnhancer:
    """Orchestrate enhancement across all medical data types"""
    
    def __init__(self):
        self.enhancers = {
            'drugs': RxClassAPI(),
            'diseases': UMLSEnhancer(), 
            'locations': LocationEnhancer(),
            'research': ResearchEnhancer()
        }
        
        # Rate limiting configuration per API
        self.rate_limits = {
            'rxclass': {'requests': 240, 'window': 60},
            'umls': {'requests': 1000, 'window': 3600}, 
            'nominatim': {'requests': 1, 'window': 1},
            'opencitations': {'requests': 10, 'window': 1}
        }
    
    async def enhance_medical_dataset(self, data_type: str, records: List[Dict], 
                                    batch_size: int = 100) -> List[Dict]:
        """Enhance entire dataset with appropriate external APIs"""
        
        if data_type not in self.enhancers:
            logger.warning(f"No enhancer available for data type: {data_type}")
            return records
        
        enhanced_records = []
        enhancer = self.enhancers[data_type]
        
        # Process in batches to manage rate limits
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_enhanced = []
            
            for record in batch:
                try:
                    if data_type == 'drugs':
                        enhanced = await enhancer.enhance_drug_data(record)
                    elif data_type == 'diseases':
                        enhanced = await enhancer.enhance_medical_concepts(record['name'])
                        record.update(enhanced)
                        enhanced = record
                    elif data_type == 'locations':
                        enhanced = await enhancer.enhance_location(record['location'])
                        record.update(enhanced)
                        enhanced = record
                    elif data_type == 'research':
                        enhanced_data = await enhancer.enhance_article(
                            record['pmid'], record['title'], record.get('authors', [])
                        )
                        record.update(enhanced_data)
                        enhanced = record
                    
                    batch_enhanced.append(enhanced)
                    
                    # Rate limiting between requests
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Enhancement failed for record: {e}")
                    batch_enhanced.append(record)  # Keep original if enhancement fails
            
            enhanced_records.extend(batch_enhanced)
            logger.info(f"Enhanced batch {i//batch_size + 1}: {len(batch_enhanced)} records")
        
        return enhanced_records
```

MEDICAL-MIRRORS SERVICE INTEGRATION PATTERN:

The smart downloaders integrate with the medical-mirrors service through update scripts:

```bash
# services/user/medical-mirrors/update-scripts/update_{data_type}.sh
#!/bin/bash
set -e

LOG_FILE="/app/logs/{data_type}_update.log"
PYTHON_ENV="/usr/local/bin/python"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Handle quick test mode
if [ "$QUICK_TEST" = "true" ]; then
    LIMIT_ITEMS=100
else
    LIMIT_ITEMS=0
fi

log_message "Starting {data_type} update"

$PYTHON_ENV -c "
import asyncio
import sys
import logging
import json
from pathlib import Path
from src.{data_type}.smart_downloader import Smart{DataType}Downloader
from src.config import Config
from src.database import get_db_session
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, ...)
logger = logging.getLogger(__name__)

async def update_{data_type}():
    config = Config()
    
    try:
        # Use smart downloader with state management
        output_dir = Path('/app/data/{data_type}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        async with Smart{DataType}Downloader(output_dir=output_dir, config=config) as downloader:
            logger.info('Starting smart {data_type} download')
            
            summary = await downloader.download_all_{data_type}_data(force_fresh=False)
            
            logger.info(f'Download completed: {summary[\"total_items\"]} items')
            logger.info(f'Success rate: {summary[\"success_rate\"]:.1f}%')
            
        # Load validated data from JSON
        data_file = output_dir / 'all_{data_type}_complete.json'
        with open(data_file, 'r') as f:
            validated_data = json.load(f)
        
        # UPSERT into database
        with get_db_session() as db:
            for item_data in validated_data:
                db.execute(text('''
                    INSERT INTO {data_type}_table (...) VALUES (...)
                    ON CONFLICT (...) DO UPDATE SET
                        -- Preserve existing data, only update with better info
                        ...
                        updated_at = NOW()
                '''), item_data)
            db.commit()
            
        return True
    except Exception as e:
        logger.error(f'Error: {e}')
        return False

# Run the update
success = asyncio.run(update_{data_type}())
if not success:
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    log_message "{data_type} update completed successfully"
else
    log_message "{data_type} update failed"
    exit 1
fi
```

Database UPSERT Pattern:
```python
# Used in all update scripts - preserves existing data while adding new
db.execute(text('''
    INSERT INTO {table_name} (
        primary_key, field1, field2, search_text, source, created_at, updated_at
    ) VALUES (
        :primary_key, :field1, :field2, :search_text, :source, NOW(), NOW()
    )
    ON CONFLICT (primary_key) DO UPDATE SET
        -- Only update if we have better/more complete information
        field1 = COALESCE(NULLIF(EXCLUDED.field1, ''), {table_name}.field1),
        field2 = COALESCE(NULLIF(EXCLUDED.field2, ''), {table_name}.field2),
        search_text = COALESCE(NULLIF(EXCLUDED.search_text, ''), {table_name}.search_text),
        source = COALESCE(NULLIF(EXCLUDED.source, ''), {table_name}.source),
        updated_at = NOW()
'''), validated_item_data)
```

HEALTHCARE-MCP INTEGRATION:

The data automatically becomes available through healthcare-mcp MCP tools following the pattern in MCPToolDeveloper.md:

1. Database-first queries using PostgreSQL full-text search
2. Automatic fallback to external APIs when database unavailable
3. Background API health monitoring
4. Performance logging and metrics

MCP Tool Example:
```typescript
// services/user/healthcare-mcp/src/server/connectors/medical/DataConnector.ts
export class DataConnector {
    async searchData(args: any): Promise<any> {
        const { query, max_results = 10 } = args;
        
        // DATABASE-FIRST: Query PostgreSQL immediately
        if (this.dbManager.isAvailable()) {
            const searchQuery = `
                SELECT code, description, category,
                       ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                FROM {data_type}_codes
                WHERE search_vector @@ plainto_tsquery('english', $1)
                   OR code ILIKE $2
                   OR description ILIKE $2
                ORDER BY rank DESC, code
                LIMIT $3
            `;
            
            const searchTerm = `%${query}%`;
            const result = await this.dbManager.query(searchQuery, [query, searchTerm, max_results]);
            
            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({ results: result.rows }, null, 2)
                }]
            };
        }
        
        // FALLBACK: Use external API if database unavailable
        // [External API logic]
    }
}
```

INTEGRATION POINTS:

Medical-Mirrors API Integration:
```python
# services/user/medical-mirrors/src/main.py
@app.post("/api/{data_type}/trigger-update")
async def trigger_{data_type}_update(background_tasks: BackgroundTasks):
    """Trigger smart downloader update via API"""
    background_tasks.add_task(run_update_script, "update_{data_type}.sh")
    return {"status": "update_triggered", "message": "Smart {data_type} update started"}

async def run_update_script(script_name: str):
    """Run update script with proper logging"""
    script_path = f"/app/update-scripts/{script_name}"
    process = await asyncio.create_subprocess_exec(script_path)
    await process.wait()
```

Manual Script Execution:
```bash
# Direct execution of update scripts
cd /app/update-scripts
QUICK_TEST=true ./update_icd10.sh     # Quick test with limited data
./update_billing.sh                  # Full update
./update_pubmed.sh                   # PubMed articles
./update_trials.sh                   # Clinical trials
./update_fda.sh                      # FDA drugs
./update_health_info.sh              # Health topics, exercises, food
```

Makefile Integration:
```bash
# Via existing medical-mirrors make commands
make medical-mirrors-update           # Trigger all updates via API
make medical-mirrors-quick-test       # Quick test mode
make medical-mirrors-progress         # Monitor update progress
```

MONITORING AND DEBUGGING:

Service Health Checks:
- Download state persistence across restarts
- Rate limit monitoring and reporting
- Progress tracking with detailed statistics
- Error logging and categorization
- Background API health validation

Performance Metrics:
- Download success rates by source
- Processing times and throughput
- Database query performance
- API response times and availability

BEST PRACTICES:

1. **Rate Limiting**: Always detect and respect rate limits
2. **Persistence**: Save state frequently for restart resilience
3. **Fallbacks**: Multiple data sources with graceful degradation
4. **Monitoring**: Comprehensive logging and health checks
5. **Database-First**: PostgreSQL as primary with API fallback
6. **Search Optimization**: Full-text search with tsvector
7. **Deduplication**: Intelligent handling of duplicate data
8. **Error Handling**: Categorized errors with appropriate responses

EXPECTED OUTCOMES:

For each data type, implement the full pattern to achieve:
- 10,000-100,000+ records (vs current fallback datasets)
- Automatic rate limit handling with zero manual intervention
- Background services for continuous updates
- Integration with healthcare-mcp MCP tools
- Database-first performance with full-text search
- Resilient architecture with multiple fallback sources

DATA TYPES IMPLEMENTED WITH SMART DOWNLOADERS:
- ✅ health_info: Health topics, exercises, food items (HealthInfoDownloader)
- ✅ icd10_codes: ~70,000 ICD-10-CM codes (SmartICD10Downloader)
- ✅ billing_codes: ~7,000 HCPCS codes (SmartBillingCodesDownloader)
- ✅ pubmed_articles: PubMed research articles (SmartPubMedDownloader) - 469K articles
- ✅ clinical_trials: ClinicalTrials.gov studies (SmartClinicalTrialsDownloader)
- ✅ **drug_information**: Enhanced multi-source architecture (SmartDrugDownloader) - **CONSOLIDATED FROM 141K→3.2K WITH 7 DATA SOURCES**

ENHANCED DRUG DATA SOURCES (7 integrated sources):
1. **DailyMed API** (FDA structured product labels)
   - URL: `https://dailymed.nlm.nih.gov/dailymed/services`
   - Special population data: pregnancy, pediatric, geriatric, nursing mothers
   - Detailed clinical information and contraindications

2. **ClinicalTrials.gov Drug Data** (clinical research studies)  
   - URL: `https://clinicaltrials.gov/api/v2/studies`
   - Drug intervention studies and clinical trial data
   - Safety and efficacy information from research

3. **OpenFDA FAERS** (FDA Adverse Event Reporting System)
   - URL: `https://api.fda.gov/drug/event.json`
   - Real-world adverse event and safety data
   - Post-market surveillance information

4. **RxClass API** (NIH therapeutic classifications)
   - URL: `https://rxnav.nlm.nih.gov/REST/rxclass`
   - ATC, EPC, MOA, and PE therapeutic classifications
   - Drug mechanism of action and therapeutic categories

5. **DrugCentral Database** (University of New Mexico)
   - URL: `http://unmtid-dbs.net/drugcentral/`
   - Comprehensive drug target and bioactivity data
   - Pharmacological and chemical information

6. **NCCIH Herbs Database** (NIH complementary medicine)
   - URL: `https://www.nccih.nih.gov/health/herbsataglance.htm`
   - Natural products and herbal medicine information
   - Evidence-based complementary treatment data

7. **DailyMed SPLs** (individual structured product labels)
   - URL: `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls`
   - Individual drug product labeling
   - Complete prescribing information and warnings

FUTURE EXPANSION CANDIDATES:
- 📋 cpt_codes: ~10,000 CPT codes (requires licensing)
- 💊 drug_interactions: Drug interaction database
- 🏥 medical_facilities: Healthcare facility directory
- 🧬 genetic_variants: Genomic variant database
- 🦠 pathogen_data: Infectious disease information

KEY ACHIEVEMENTS:
- All 6 major data sources upgraded to smart downloaders
- **Data consolidation breakthrough**: 141K→3.2K drug records with zero data loss
- **External API enhancement**: RxClass therapeutic classification integration
- **Hybrid database architecture**: Consolidated + detailed data preservation
- **Performance optimization**: Complex JSON queries with proper indexing
- Unified architecture with state persistence and retry logic
- Integration with medical-mirrors service update scripts
- Automatic rate limit handling across all sources
- Resume capability for interrupted downloads
- UPSERT operations preserving existing database data
- **Simplified API design**: Removed unnecessary complexity and fallback methods

ENHANCED DRUG DATA API CONFIGURATION:
Environment variables for enhanced drug sources (stored in /home/intelluxe/.env):

```bash
# Enhanced Drug Data APIs
DAILYMED_API_BASE_URL=https://dailymed.nlm.nih.gov/dailymed/services
CLINICAL_TRIALS_API_BASE_URL=https://clinicaltrials.gov/api
OPENFDA_FAERS_API_BASE_URL=https://api.fda.gov/drug/event.json
RXCLASS_API_BASE_URL=https://rxnav.nlm.nih.gov/REST/rxclass
DRUGCENTRAL_DB_HOST=unmtid-dbs.net
NCCIH_HERBS_BASE_URL=https://www.nccih.nih.gov
DAILYMED_SPLS_API_BASE_URL=https://dailymed.nlm.nih.gov/dailymed/services/v2

# API Rate Limits (requests per time window)
DAILYMED_RATE_LIMIT=240,60           # 240 requests per 60 seconds
CLINICAL_TRIALS_RATE_LIMIT=300,60    # 300 requests per 60 seconds  
OPENFDA_RATE_LIMIT=240,60            # 240 requests per 60 seconds
RXCLASS_RATE_LIMIT=300,60            # 300 requests per 60 seconds
DRUGCENTRAL_RATE_LIMIT=100,60        # 100 requests per 60 seconds
NCCIH_RATE_LIMIT=60,60               # 60 requests per 60 seconds
```

DATA QUALITY IMPROVEMENTS:
Special population coverage enhanced from 4.9%-36.3% to 60-80% through multi-source integration:
- **Pregnancy information**: DailyMed, ClinicalTrials.gov studies, FAERS reports
- **Pediatric data**: Clinical trials with pediatric populations, specialized labeling
- **Geriatric considerations**: Age-specific dosing, adverse events, drug interactions  
- **Nursing mothers**: Lactation safety, transfer data, breastfeeding recommendations

ENHANCED DRUG SOURCES INTEGRATION (PROVEN PATTERNS):
Based on successful implementation of DailyMed, DrugCentral, and RxClass integration with fuzzy matching:

Key Integration Architecture:
```
enhanced_drug_sources/
├── drug_name_matcher.py      # Tiered fuzzy matching (exact → normalized → fuzzy)
├── dailymed_parser.py        # HL7 v3 XML clinical data parser  
├── drugcentral_parser.py     # Mechanism/pharmacology JSON parser
├── rxclass_parser.py         # Therapeutic classifications parser
└── base_parser.py            # Common validation/normalization patterns
```

Fuzzy Matching Performance Strategy:
- **Tiered Matching**: exact match → normalized match → upper case → fuzzy (limit fuzzy to max 100)
- **Drug Name Normalization**: Remove 25+ pharmaceutical suffix patterns (salts, forms, stereoisomers)
- **Performance Results**: DrugCentral 66% match rate (1,455/2,581), RxClass 100% match (7/7)
- **Processing Speed**: 33K+ drugs processed in minutes using optimized strategies

Database Integration Patterns:
```python
# PostgreSQL array operations with proper type casting
drug_record = db.query(DrugInformation).filter(
    DrugInformation.brand_names.op('@>')(cast([brand_name], ARRAY(Text)))
).first()

# Field update strategy (longer content wins, preserve data lineage)
if new_value and len(new_value) > len(str(current_value)) * 1.5:
    setattr(drug_record, field_name, new_value)
    current_sources.add("dailymed")  # Track data source
```

Docker Development Integration:
- **Quick Testing**: Use `docker cp` for immediate file sync without rebuilds
- **Container Testing**: Create container-specific test scripts with proper Python path setup
- **Module Import Fix**: `sys.path.append('/app/src')` for container environments
- **Database Connection**: Handle container-to-database connectivity patterns

Field Population Success Metrics:
- **mechanism_of_action**: 4,049 drugs (12.1% of 33,547 total) - major improvement
- **therapeutic_class**: Enhanced classification coverage from multiple sources  
- **pharmacokinetics**: 2,720 drugs with new clinical data from DrugCentral
- **Data Sources**: 10+ integrated sources with proper lineage tracking

This pattern ensures consistency, reliability, and scalability across all medical data mirror services with comprehensive drug information coverage.

## STORAGE MANAGEMENT INTEGRATION

Smart downloaders integrate with storage optimization for efficient space usage:

### Storage Monitoring Pattern
```python
# Integrate disk monitoring during downloads
from scripts.download_utils import check_disk_space, log_download_progress

class SmartDownloaderWithStorage:
    """Enhanced smart downloader with storage management"""
    
    def __init__(self, output_dir: Path, min_free_space_gb: float = 20.0):
        self.output_dir = output_dir
        self.min_free_space_gb = min_free_space_gb
        self.storage_monitor = True
        
    async def download_with_storage_monitoring(self):
        """Download with real-time storage monitoring"""
        
        # Pre-download storage check
        disk_info = check_disk_space(str(self.output_dir), self.min_free_space_gb)
        
        if disk_info.get('warnings'):
            for warning in disk_info['warnings']:
                self.logger.warning(f"STORAGE: {warning}")
            
            # Trigger cleanup if space is critical
            if disk_info.get('free_gb', 0) < self.min_free_space_gb:
                await self._trigger_emergency_cleanup()
        
        # Monitor space during download
        async for batch_result in self._download_in_batches():
            # Check disk space every batch
            current_disk = check_disk_space(str(self.output_dir))
            if current_disk.get('warnings'):
                self.logger.warning("Pausing download for storage management")
                await self._pause_for_cleanup()
            
            yield batch_result
    
    async def _trigger_emergency_cleanup(self):
        """Trigger cleanup when disk space is critical"""
        cleanup_script = Path('/home/intelluxe/scripts/automated_cleanup.sh')
        if cleanup_script.exists():
            subprocess.run([str(cleanup_script), '--force'], check=False)
            self.logger.info("Emergency cleanup triggered")
```

### Download Best Practices Integration
```python
# Prevent pretty printing and bloat during downloads
def save_data_efficiently(data: Any, output_file: Path, file_type: str = 'json'):
    """Save data without pretty printing to prevent bloat"""
    
    # Never use pretty printing
    json_params = {
        'ensure_ascii': False,
        'separators': (',', ':'),  # Compact separators
        'default': str
    }
    
    if file_type == 'json':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, **json_params)
    
    # Log file size for monitoring
    file_size_mb = output_file.stat().st_size / (1024**2)
    if file_size_mb > 100:  # Log large files
        logger.info(f"Large file created: {output_file.name} ({file_size_mb:.1f}MB)")
        
        # Auto-compress large files if configured
        if hasattr(self, 'auto_compress_large_files') and self.auto_compress_large_files:
            compressed_path = self._compress_file(output_file)
            output_file.unlink()  # Remove original
            logger.info(f"Auto-compressed: {compressed_path.name}")

# Integration with cleanup systems
def setup_post_download_cleanup(self):
    """Set up automatic cleanup after download completion"""
    
    cleanup_tasks = [
        'remove_duplicate_uncompressed_files',
        'compress_large_json_files', 
        'clean_temporary_downloads',
        'update_storage_metrics'
    ]
    
    for task in cleanup_tasks:
        self.post_download_tasks.append(task)
```

### Compression Strategy Integration
```python
class CompressedDownloadManager:
    """Download with intelligent compression strategies"""
    
    def __init__(self):
        self.compression_candidates = {
            '.xml': 'gzip',  # Medical XML files compress very well (~90%)
            '.json': 'gzip', # JSON also compresses well (~80%) 
            '.csv': 'gzip',  # CSV files compress excellently (~85%)
            '.txt': 'gzip'   # Text files compress well (~70%)
        }
        
        self.compress_threshold_mb = 50  # Compress files > 50MB
    
    async def download_and_compress(self, url: str, output_path: Path):
        """Download and immediately compress large files"""
        
        # Download to temporary location first
        temp_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
        
        await self._download_file(url, temp_path)
        
        file_size = temp_path.stat().st_size
        file_size_mb = file_size / (1024**2)
        
        # Compress if file is large
        if (file_size_mb > self.compress_threshold_mb and 
            output_path.suffix in self.compression_candidates):
            
            compression_method = self.compression_candidates[output_path.suffix]
            compressed_path = output_path.with_suffix(f"{output_path.suffix}.gz")
            
            if compression_method == 'gzip':
                with open(temp_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove temporary uncompressed file
                temp_path.unlink()
                
                compression_ratio = compressed_path.stat().st_size / file_size
                self.logger.info(f"Compressed {output_path.name}: "
                               f"{file_size_mb:.1f}MB → "
                               f"{compressed_path.stat().st_size/(1024**2):.1f}MB "
                               f"({compression_ratio:.1%} ratio)")
                
                return compressed_path
        else:
            # Move temp file to final location
            temp_path.rename(output_path)
        
        return output_path
```

### Automated Cleanup Integration
```python
# Integration with automated cleanup systems
class MirrorServiceWithCleanup:
    """Mirror service with integrated cleanup automation"""
    
    def __init__(self):
        self.cleanup_triggers = {
            'disk_usage_threshold': 75.0,  # Trigger cleanup at 75% usage
            'after_major_download': True,   # Cleanup after large downloads
            'weekly_schedule': True         # Weekly automated cleanup
        }
    
    async def post_download_maintenance(self, download_results: Dict):
        """Perform maintenance after download completion"""
        
        maintenance_tasks = []
        
        # Check if cleanup is needed
        disk_info = check_disk_space(str(self.data_dir))
        
        if disk_info['usage_percent'] > self.cleanup_triggers['disk_usage_threshold']:
            maintenance_tasks.append('trigger_duplicate_cleanup')
        
        if download_results.get('total_size_gb', 0) > 10:  # Large download
            maintenance_tasks.append('compress_new_large_files')
            maintenance_tasks.append('remove_temporary_files')
        
        # Execute maintenance tasks
        for task in maintenance_tasks:
            try:
                await self._execute_maintenance_task(task)
                self.logger.info(f"Completed maintenance task: {task}")
            except Exception as e:
                self.logger.error(f"Maintenance task failed: {task} - {e}")
    
    async def _execute_maintenance_task(self, task: str):
        """Execute specific maintenance task"""
        
        if task == 'trigger_duplicate_cleanup':
            cleanup_script = '/home/intelluxe/scripts/cleanup_medical_downloads.py'
            subprocess.run(['python3', cleanup_script, str(self.data_dir), '--execute'], 
                         input='yes\n', text=True, check=False)
        
        elif task == 'compress_new_large_files':
            compressor = CompressionOptimizer(self.data_dir)
            opportunities = compressor.analyze_compression_opportunities()
            await compressor.compress_files([opp['file'] for opp in opportunities[:10]])
        
        elif task == 'remove_temporary_files':
            # Clean up .tmp, .partial, .download files
            for pattern in ['*.tmp', '*.partial', '*.download']:
                for temp_file in self.data_dir.rglob(pattern):
                    if temp_file.is_file():
                        temp_file.unlink()
```

This enhanced storage integration ensures that medical data mirroring operations maintain optimal storage efficiency while preserving all data integrity.

## AI ENHANCEMENT PATTERNS FOR MEDICAL DATA

Advanced patterns for enriching medical data using AI services (SciSpacy NLP + Ollama LLM) with proven success from food data enhancement (98% success rate on 7,300+ items).

### Food Data AI Enhancement Architecture

Complete implementation pattern using dual AI services for intelligent enhancement:

```python
# services/user/medical-mirrors/src/health_info/food_ai_enrichment.py
class FoodAIEnhancer:
    """
    AI-driven food enhancement using NLP and LLM.
    No hardcoded food knowledge - uses:
    - SciSpacy for biomedical entity recognition
    - Ollama for intelligent text generation
    - Context-aware enhancement based on actual food understanding
    """
    
    def __init__(self, batch_size: int = 100, use_scispacy: bool = False):
        self.batch_size = batch_size
        self.use_scispacy = use_scispacy
        
        # Initialize AI clients
        if use_scispacy:
            self.scispacy_client = SciSpacyClientSync()
        
        # Use optimized client for faster processing
        from .llm_client_optimized import OptimizedOllamaClient
        self.ollama_client = OptimizedOllamaClient()
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'enhanced': 0,
            'scientific_names_added': 0,
            'common_names_added': 0,
            'ingredients_added': 0,
            'serving_sizes_added': 0,
            'ai_calls': 0,
            'ai_failures': 0
        }
        
    def enhance_food_database(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Enhance food database using AI-driven approach"""
        
        # Check AI service health
        if not self._check_ai_services():
            logger.error("AI services not available")
            return self.stats
        
        with get_db_session() as session:
            # Get items needing enhancement
            query = """
                SELECT fdc_id, description, scientific_name, common_names,
                       food_category, brand_owner, ingredients, serving_size
                FROM food_items
                WHERE (scientific_name IS NULL OR scientific_name = '')
                   OR (common_names IS NULL OR common_names = '')
                   OR (ingredients IS NULL OR ingredients = '')
                   OR (serving_size IS NULL)
                ORDER BY fdc_id
            """
            
            # Process in batches for efficiency
            for batch in batches:
                self._process_batch(session, batch)
                
            session.commit()
        
        return self.stats
```

### Optimized LLM Client Pattern

Single-call optimization reducing latency from 20-40 seconds to 1.25 seconds per item:

```python
# services/user/medical-mirrors/src/health_info/llm_client_optimized.py
class OptimizedOllamaClient:
    """Optimized LLM client making single API calls instead of multiple"""
    
    def __init__(self, model: str = "llama3.1:8b", timeout: int = 30):
        self.model = model
        self.timeout = timeout
        self.base_url = "http://172.20.0.15:11434"  # Ollama container
        
    def generate_all_food_enhancements(self, description: str, category: str = None,
                                      food_entities: List[str] = None) -> Dict[str, Any]:
        """Generate all enhancements in a single LLM call"""
        
        prompt = f"""Analyze this food item and provide comprehensive information:
        Food item: {description}
        {f'Category: {category}' if category else ''}
        {f'Detected entities: {", ".join(food_entities[:5])}' if food_entities else ''}
        
        Provide the following information in JSON format:
        1. scientific_name: The scientific/botanical/zoological name (or empty string if not applicable)
        2. common_names: List of up to 5 common/alternative names separated by commas
        3. ingredients: Main ingredients or components (or empty string if not applicable)
        4. serving_size: Standard USDA serving size as a number (or null if unknown)
        5. serving_unit: Unit for the serving size (e.g., 'g', 'oz', 'cup')
        
        Respond ONLY with valid JSON. Do not include explanations."""
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower for consistency
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=self.timeout
            )
            
            # Parse and validate response
            result = response.json()
            llm_output = result.get('response', '{}')
            
            # Extract JSON from response
            enhanced_data = self._extract_json(llm_output)
            
            return self._validate_enhancements(enhanced_data)
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._empty_enhancements()
```

### GPU/CPU Hybrid Approach

Handling GPU compatibility issues (RTX 5060 Ti sm_120) with intelligent fallbacks:

```python
# Docker configuration for GPU-aware services
# services/user/scispacy/Dockerfile
FROM nvidia/cuda:12.6.2-runtime-ubuntu24.04

# Install PyTorch nightly for RTX 5060 Ti (sm_120) support
RUN pip3 install --break-system-packages --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu129

# SciSpacy installation (will use CPU due to CuPy incompatibility)
RUN pip3 install --break-system-packages \
    scispacy \
    spacy[transformers] \
    flask

# GPU detection and fallback
RUN python -c "import torch; \
    print(f'CUDA available: {torch.cuda.is_available()}'); \
    if torch.cuda.is_available(): \
        print(f'GPU: {torch.cuda.get_device_name(0)}'); \
    else: \
        print('Using CPU for NLP processing')"
```

```python
# GPU accelerator with fallback patterns
class GPUAccelerator:
    """GPU acceleration with CPU fallback for incompatible operations"""
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Check for specific GPU architecture issues
        if torch.cuda.is_available():
            capability = torch.cuda.get_device_capability()
            if capability[0] >= 12:  # sm_120 or newer
                logger.warning("Newer GPU detected, some libraries may not support it")
                self.use_gpu_for_nlp = False  # Fallback to CPU for NLP
            else:
                self.use_gpu_for_nlp = True
        else:
            self.use_gpu_for_nlp = False
    
    def process_with_best_device(self, operation_type: str, data):
        """Route operations to best available device"""
        
        if operation_type == 'llm_inference':
            # LLMs work well on newer GPUs
            return self._process_on_gpu(data) if self.device.type == 'cuda' else self._process_on_cpu(data)
        
        elif operation_type == 'nlp_parsing':
            # NLP may have compatibility issues with newer GPUs
            return self._process_on_cpu(data) if not self.use_gpu_for_nlp else self._process_on_gpu(data)
```

### Government Standards Integration

Using official sources for dietary and medical standards:

```python
def _determine_dietary_flags(self, food: dict) -> dict:
    """Determine professional dietary flags using USDA/FDA standards"""
    
    # USDA MyPlate Guidelines (2020-2025 Dietary Guidelines for Americans)
    myplate_groups = {
        'fruits': ['apple', 'banana', 'berry', 'citrus', 'melon'],
        'vegetables': ['leafy', 'broccoli', 'carrot', 'potato', 'tomato'],
        'grains': ['wheat', 'rice', 'oat', 'corn', 'quinoa', 'bread', 'cereal'],
        'protein': ['meat', 'poultry', 'fish', 'egg', 'bean', 'nut', 'seed'],
        'dairy': ['milk', 'cheese', 'yogurt', 'calcium']
    }
    
    # FDA FALCPA & FASTER Act - 9 Major Allergens
    fda_allergens = {
        'milk': ['milk', 'dairy', 'casein', 'whey', 'lactose', 'butter', 'cheese'],
        'eggs': ['egg', 'albumin', 'mayonnaise'],
        'fish': ['fish', 'cod', 'salmon', 'tuna', 'tilapia', 'bass'],
        'shellfish': ['shellfish', 'crab', 'lobster', 'shrimp', 'mollusk'],
        'tree_nuts': ['almond', 'cashew', 'walnut', 'pecan', 'pistachio'],
        'peanuts': ['peanut', 'groundnut'],
        'wheat': ['wheat', 'gluten', 'flour', 'bread'],
        'soybeans': ['soy', 'soybean', 'tofu', 'edamame'],
        'sesame': ['sesame', 'tahini', 'benne']
    }
    
    # FDA CFR Title 21 - Nutritional Claims
    fda_nutritional_claims = []
    nutrients = food.get('nutrients', {})
    
    # Low calorie: < 40 calories per serving
    if nutrients.get('calories', float('inf')) < 40:
        fda_nutritional_claims.append('low_calorie')
    
    # Low sodium: < 140mg per serving
    if nutrients.get('sodium_mg', float('inf')) < 140:
        fda_nutritional_claims.append('low_sodium')
    
    # High fiber: >= 5g per serving
    if nutrients.get('fiber_g', 0) >= 5:
        fda_nutritional_claims.append('high_fiber')
    
    return {
        'myplate_food_group': detected_group,
        'fda_nutritional_claims': fda_nutritional_claims,
        'potential_allergens': detected_allergens,
        'data_sources': {
            'myplate': 'USDA Dietary Guidelines 2020-2025',
            'allergens': 'FDA FALCPA & FASTER Act',
            'claims': 'FDA CFR Title 21'
        }
    }
```

### Database Migration Patterns

Handling restrictive constraints without data truncation:

```python
# migrations/007_fix_food_field_lengths.py
def upgrade():
    """Fix field length constraints - never truncate medical information"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Drop dependent views first
            cursor.execute("DROP VIEW IF EXISTS myplate_mapping_validation CASCADE")
            
            # Change VARCHAR to TEXT for fields that may have long content
            cursor.execute("""
                ALTER TABLE food_items 
                ALTER COLUMN serving_size_unit TYPE TEXT,
                ALTER COLUMN scientific_name TYPE TEXT,
                ALTER COLUMN common_names TYPE TEXT,
                ALTER COLUMN ingredients TYPE TEXT;
            """)
            
            # Recreate views if needed
            cursor.execute("""
                CREATE VIEW myplate_mapping_validation AS
                SELECT fdc_id, description, myplate_food_group, 
                       dietary_flags->>'myplate_food_group' as mapped_group
                FROM food_items
                WHERE dietary_flags IS NOT NULL;
            """)
            
            conn.commit()
            logger.info("Successfully migrated field constraints")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise
```

### Update Script Integration

Automatic AI enhancement after data downloads:

```bash
# services/user/medical-mirrors/update-scripts/update_health_info.sh
# AI enhancement integrated into update pipeline

# After downloading food data, run AI enhancement
python3 -c "
import sys
sys.path.append('/app/src')
from health_info.food_ai_enrichment import FoodAIEnhancer

try:
    # Run food enhancement with limit for quick test
    food_enhancer = FoodAIEnhancer(batch_size=50, use_scispacy=True)
    enhancement_limit = $LIMIT_ITEMS if $LIMIT_ITEMS > 0 else None
    enhancement_stats = food_enhancer.enhance_food_database(limit=enhancement_limit)
    
    logger.info(f'Food AI Enhancement completed: {enhancement_stats}')
    
except Exception as e:
    logger.warning(f'Food AI enhancement failed: {e}')
    # Continue without enhancement - don't fail the entire update
"
```

### AI Service Health Management

Reliability patterns with health checks and fallbacks:

```python
class AIServiceManager:
    """Manage AI services with health monitoring and fallbacks"""
    
    def __init__(self):
        self.services = {
            'ollama': {
                'url': 'http://172.20.0.15:11434/api/tags',
                'required': True,
                'fallback': None
            },
            'scispacy': {
                'url': 'http://172.20.0.6:8001/health',
                'required': False,  # Can work without it
                'fallback': 'basic_nlp'
            }
        }
        
        self.health_check_interval = 60  # seconds
        self.last_health_check = {}
        
    async def ensure_services_available(self, required_services: List[str]):
        """Ensure required AI services are available"""
        
        unavailable = []
        for service_name in required_services:
            if not await self.check_service_health(service_name):
                service = self.services[service_name]
                
                if service['required']:
                    raise ServiceUnavailableError(f"{service_name} is required but unavailable")
                
                if service['fallback']:
                    logger.warning(f"{service_name} unavailable, using fallback: {service['fallback']}")
                else:
                    unavailable.append(service_name)
        
        return unavailable
    
    async def check_service_health(self, service_name: str) -> bool:
        """Check if service is healthy with caching"""
        
        # Use cached result if recent
        if service_name in self.last_health_check:
            last_check = self.last_health_check[service_name]
            if time.time() - last_check['timestamp'] < self.health_check_interval:
                return last_check['healthy']
        
        # Perform health check
        service = self.services[service_name]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(service['url'], timeout=5) as response:
                    healthy = response.status == 200
                    
                    self.last_health_check[service_name] = {
                        'timestamp': time.time(),
                        'healthy': healthy
                    }
                    
                    return healthy
                    
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {e}")
            
            self.last_health_check[service_name] = {
                'timestamp': time.time(),
                'healthy': False
            }
            
            return False
```

### Performance Metrics

Achieved results from food enhancement implementation:
- **Processing Rate**: ~50 items/minute (1.25 seconds per item)
- **Success Rate**: 98% (98/100 items enhanced successfully)
- **Coverage Improvements**:
  - Scientific names: 5.2% → 44% coverage
  - Common names: 3.4% → 97% coverage
  - Ingredients: 0% → 98% coverage
  - Serving sizes: 0% → 98% coverage
- **Resource Utilization**:
  - Ollama GPU: 93% VRAM utilization
  - SciSpacy CPU: Minimal impact
  - Database: Efficient batch commits

### Best Practices for AI Enhancement

1. **Never Truncate Medical Information**: Use TEXT fields instead of VARCHAR
2. **Optimize API Calls**: Single combined calls instead of multiple separate calls
3. **Handle GPU Compatibility**: Graceful fallbacks for unsupported architectures
4. **Use Official Sources**: Government standards for medical/dietary information
5. **Batch Processing**: Process in batches to manage memory and improve throughput
6. **Health Monitoring**: Regular health checks with fallback strategies
7. **Statistics Tracking**: Comprehensive metrics for monitoring and debugging
8. **Error Recovery**: Continue processing even if individual items fail

### Extending to Other Medical Data Types

This pattern can be applied to enhance any medical data type:

```python
class MedicalDataEnhancer:
    """Generic enhancer for any medical data type"""
    
    def __init__(self, data_type: str, enhancement_config: Dict):
        self.data_type = data_type
        self.config = enhancement_config
        
        # Initialize appropriate AI services
        if 'clinical' in data_type:
            self.nlp_client = SciSpacyClient()  # Biomedical NLP
        else:
            self.nlp_client = BasicNLPClient()  # General NLP
        
        self.llm_client = OptimizedOllamaClient()
        
    async def enhance_dataset(self, limit: Optional[int] = None):
        """Enhance any medical dataset with AI"""
        
        # Get items needing enhancement
        query = self.config['selection_query']
        
        # Process with appropriate prompts
        for batch in self._get_batches(query, limit):
            enhanced_batch = await self._enhance_batch(batch)
            self._save_enhancements(enhanced_batch)
        
        return self.stats
```

This AI enhancement architecture provides a proven, scalable pattern for enriching any medical data with intelligent, context-aware information while maintaining data integrity and system reliability.
```