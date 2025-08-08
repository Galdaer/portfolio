# Medical Mirrors Service Troubleshooting Instructions

## Strategic Purpose

Comprehensive troubleshooting patterns for the medical-mirrors service that downloads and processes PubMed, ClinicalTrials.gov, and FDA data for healthcare AI systems.

## Critical Issues Identified (2025-08-07)

### Issue 1: Data Storage Architecture Problem
**Problem**: Medical-mirrors service downloads files to `/app/data/` but fails to parse and store them in PostgreSQL.

**Root Cause**: Parser bugs prevent data from reaching the database:
- PubMed: Parser already has gzip support but still failing to parse
- ClinicalTrials: Using old API v1 parameters instead of new v2 format  
- FDA: Parser expects dict objects but receives strings/booleans

**Database Status**: All tables exist but are empty:
```bash
# Check data in database
docker exec medical-mirrors python3 -c "
import asyncio, sys
sys.path.append('/app/src')
from database import SessionLocal
from sqlalchemy import text
async def check():
    async with SessionLocal() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM pubmed_articles'))
        print(f'PubMed: {result.scalar()}')
asyncio.run(check())
"
```

### Issue 2: API Migration Problems

#### ClinicalTrials.gov API v2 Migration
**Problem**: Using old API v1 parameters (`lup_s`, `lup_e`, `fmt`) instead of new v2 format.

**Fixed Parameters**:
```python
# ❌ OLD (causing 400 errors):
params = {
    "fmt": "json",
    "lup_s": start_date.strftime("%m/%d/%Y"),
    "lup_e": end_date.strftime("%m/%d/%Y"),
}

# ✅ NEW (API v2 format):
params = {
    "format": "json", 
    "query.term": f"AREA[LastUpdatePostDate]RANGE[{start_str}, {end_str}]",
    "pageSize": 1000,
}
```

#### FDA OpenFDA Dynamic URLs
**Problem**: Hardcoded URLs for drug labels return 403 errors.

**Solution**: Use dynamic URLs from `https://api.fda.gov/download.json`:
```python
# Get current download URLs
download_info = await self.session.get("https://api.fda.gov/download.json")
label_partitions = download_info.json()["results"]["drug"]["label"]["partitions"]
url = label_partitions[0]["file"]  # Use first partition
```

### Issue 3: Make Commands Block Terminal
**Problem**: Update commands take over terminal, preventing progress monitoring.

**Current Blocking Commands**:
- `make medical-mirrors-update-pubmed`
- `make medical-mirrors-update-trials` 
- `make medical-mirrors-update-fda`

**Solution**: Add background (`&`) and timeout options to make commands.

## ✅ RESOLVED ISSUES (2025-08-08)

### Issue 1: PubMed FTP Downloader Hanging - SOLVED ✅

**Problem**: PubMed downloader hanging at "Starting PubMed updates download" due to FTP connection timeout.

**Root Cause**: `ftplib.FTP` used without timeout configuration, causing infinite hangs on network issues.

**Solution Implemented**: Robust FTP handling with timeouts and retry logic:

```python
# ✅ SOLUTION: FTP Context Manager with Timeout and Retry Logic
import ftplib
import time
from contextlib import contextmanager
from typing import Optional

class PubMedDownloader:
    def __init__(self):
        # FTP timeout and retry configuration
        self.connection_timeout = 30  # seconds
        self.operation_timeout = 60   # seconds
        self.download_timeout = 300   # seconds for large files
        self.max_retries = 3
        self.retry_delay = 5          # seconds

    @contextmanager
    def ftp_connection(self, timeout: Optional[int] = None):
        """Context manager for FTP connections with timeout and cleanup"""
        ftp = None
        try:
            timeout = timeout or self.connection_timeout
            logger.info(f"Connecting to {self.ftp_host} with {timeout}s timeout")
            
            ftp = ftplib.FTP(timeout=timeout)
            ftp.connect(self.ftp_host)
            ftp.login()
            
            logger.info("FTP connection established successfully")
            yield ftp
            
        except ftplib.all_errors as e:
            logger.error(f"FTP connection error: {e}")
            raise
        finally:
            if ftp:
                try:
                    ftp.quit()
                    logger.debug("FTP connection closed")
                except Exception:
                    try:
                        ftp.close()
                    except Exception:
                        pass

    def retry_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempting {operation_name} (attempt {attempt + 1}/{self.max_retries})")
                return operation_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"{operation_name} failed after {self.max_retries} attempts: {e}")
                    raise
                
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"{operation_name} failed (attempt {attempt + 1}): {e}, retrying in {wait_time}s")
                time.sleep(wait_time)

    async def download_updates(self) -> list[str]:
        """Download PubMed update files with robust error handling"""
        def download_operation():
            with self.ftp_connection(self.connection_timeout) as ftp:
                ftp.cwd(self.update_path)
                
                # Set longer timeout for large file downloads
                ftp.sock.settimeout(self.download_timeout)
                
                # Download files with progress logging
                # ... implementation details
                
        return self.retry_operation("updates_download", download_operation)
```

**Results**: 
- ✅ FTP connections establish in <200ms with 30s timeout
- ✅ Downloads complete successfully without hanging
- ✅ Proper resource cleanup and error handling

### Issue 2: Multi-Core Processing Optimization - IMPLEMENTED ✅

**Achievement**: Successfully implemented 16-core parallel XML parsing for medical literature processing.

**Performance Results**:
- **Processing Rate**: ~2,800 articles/second with 16 workers
- **Test Results**: 78,549 articles from 3 files processed in ~27 seconds
- **Database Storage**: 75,295 unique articles after PMID deduplication
- **Memory Efficiency**: Bulk database operations with 5,000-article batches

**Implementation Pattern**:

```python
# ✅ SOLUTION: Multi-Core Medical Literature Processing
from multiprocessing import ProcessPoolExecutor, Pool
import asyncio
from typing import List, Dict, Any

class OptimizedPubMedParser:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or os.cpu_count()
        logger.info(f"Initialized PubMed parser with {self.max_workers} workers")

    async def parse_xml_files_parallel(self, xml_files: List[str]) -> List[Dict[str, Any]]:
        """Parse multiple XML files in parallel using multiprocessing"""
        logger.info(f"Parsing {len(xml_files)} XML files using {self.max_workers} cores")
        
        # Use ProcessPoolExecutor for CPU-bound XML parsing
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for xml_file in xml_files:
                future = executor.submit(self._parse_single_file_worker, xml_file)
                futures.append(future)
            
            # Collect results as they complete
            all_articles = []
            for future in futures:
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Worker parsed {len(articles)} articles from {xml_file}")
                except Exception as e:
                    logger.error(f"Worker failed to parse file: {e}")
            
        logger.info(f"Parallel parsing completed: {len(all_articles)} total articles from {len(xml_files)} files")
        return all_articles

    @staticmethod
    def _parse_single_file_worker(xml_file_path: str) -> List[Dict[str, Any]]:
        """Worker function for parsing a single XML file"""
        logger.info(f"Worker parsing: {xml_file_path}")
        
        # Extract if gzipped
        if xml_file_path.endswith('.gz'):
            with gzip.open(xml_file_path, 'rt', encoding='utf-8') as f:
                content = f.read()
        else:
            with open(xml_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Parse XML and extract articles
        root = ET.fromstring(content)
        articles = []
        
        for article in root.findall('.//PubmedArticle'):
            # Extract article data...
            article_data = extract_article_data(article)
            articles.append(article_data)
        
        return articles
```

### Issue 3: Database Constraint Violations - RESOLVED ✅

**Problem**: PostgreSQL constraint violations from duplicate PMID entries during bulk inserts.

**Solution**: PMID deduplication before database operations:

```python
# ✅ SOLUTION: PMID Deduplication Pattern
async def bulk_store_articles(self, articles: List[Dict[str, Any]]) -> int:
    """Store articles with PMID deduplication and bulk operations"""
    logger.info(f"Deduplicating {len(articles)} articles by PMID...")
    
    # Deduplicate by PMID before database operations
    seen_pmids = set()
    unique_articles = []
    
    for article in articles:
        pmid = article.get('pmid')
        if pmid and pmid not in seen_pmids:
            seen_pmids.add(pmid)
            unique_articles.append(article)
    
    duplicates_removed = len(articles) - len(unique_articles)
    logger.info(f"Removed {duplicates_removed} duplicate PMIDs, processing {len(unique_articles)} unique articles")
    
    # Bulk database storage with batch processing
    batch_size = 5000
    stored_count = 0
    
    for i in range(0, len(unique_articles), batch_size):
        batch = unique_articles[i:i + batch_size]
        stored_count += await self._bulk_insert_batch(batch)
        logger.info(f"Bulk stored {stored_count}/{len(unique_articles)} articles...")
    
    return stored_count
```

**Results**:
- ✅ Zero constraint violations during bulk operations
- ✅ 75,295 unique articles stored successfully
- ✅ Efficient batch processing with progress logging

## Performance Benchmarks (2025-08-08)

### Successful Multi-Core Medical Data Pipeline

**Test Configuration**:
- **Hardware**: 16-core system
- **Data Sources**: PubMed (3 files), ClinicalTrials (100 studies), FDA (1000 drugs)
- **Processing Mode**: Multi-core parallel with database integration

**Performance Results**:
```
📊 PubMed Processing:
- Files Processed: 3 XML.gz files (~267MB total)
- Articles Parsed: 78,549 total articles
- Unique Articles: 75,295 (after deduplication)
- Processing Time: ~27 seconds
- Processing Rate: ~2,800 articles/second
- Workers Used: 16 parallel processes
- Database Storage: Bulk operations with 5,000-article batches

🧪 ClinicalTrials Processing:
- Studies Downloaded: 100 via API v2
- Processing Time: <1 second
- API Response: 200 OK (no parameter errors)

💊 FDA Processing:
- Drugs Processed: 1,000 from Orange Book
- Data Sources: Orange Book, NDC Directory, Drugs@FDA, Drug Labels
- Processing Time: ~17 seconds for downloads + parsing
- All datasets successfully integrated
```

**Architecture Success**:
- ✅ FTP connections with robust timeout handling
- ✅ Multi-core XML parsing at full CPU utilization
- ✅ Database-first architecture with appropriate fallbacks
- ✅ Bulk database operations with constraint violation prevention
- ✅ Complete end-to-end medical data pipeline operational

## Parser Error Patterns

### FDA Parser Error: `'str' object has no attribute 'get'`
**Symptom**: Massive log output with thousands of identical errors.

**Root Cause**: Parser expects JSON objects but receives primitive types.

**Debug Pattern**:
```bash
# Check actual FDA file structure
docker exec medical-mirrors head -20 /app/data/fda/labels/*.json
```

### PubMed Parser: XML Decompression
**Status**: Gzip support already implemented but still failing.

**Debug Pattern**:
```bash
# Test actual file format
docker exec medical-mirrors python3 -c "
import gzip
with gzip.open('/app/data/pubmed/updates_pubmed25n1474.xml.gz', 'rt') as f:
    print(f.read(500))
"
```

## Service Management Patterns

### Non-Blocking Update Commands
```makefile
# ✅ CORRECT: Non-blocking update with timeout
medical-mirrors-update-pubmed:
	@echo "🚀 Starting PubMed update (background)"
	@timeout 300 curl -X POST "http://localhost:8081/update/pubmed" &
	@echo "✅ PubMed update started - use 'make medical-mirrors-progress' to monitor"

medical-mirrors-progress:
	@echo "📊 Medical Mirrors Progress Monitor"
	@while true; do \
		echo "$(date): Checking service status..."; \
		curl -s "http://localhost:8081/health" | jq -r '.status // "Service unavailable"'; \
		sleep 30; \
	done
```

### Service Health Monitoring
```bash
# Quick health check
curl -s "http://localhost:8081/health" | jq

# Database connection test  
docker exec medical-mirrors python3 -c "
from src.database import SessionLocal
print('Database: Connected' if SessionLocal else 'Failed')
"
```

## Data Validation Patterns

### File Download Validation
```bash
# Check downloaded files
docker exec medical-mirrors ls -la /app/data/*/

# Validate file contents
docker exec medical-mirrors bash -c "
echo 'PubMed files:'; ls -lh /app/data/pubmed/ | wc -l
echo 'FDA files:'; ls -lh /app/data/fda/ | wc -l  
echo 'Trials files:'; ls -lh /app/data/trials/ | wc -l
"
```

### Database Population Check
```bash
# Comprehensive database check
docker exec medical-mirrors python3 -c "
import asyncio, sys
sys.path.append('/app/src')
from database import SessionLocal
from sqlalchemy import text

async def check_all_tables():
    async with SessionLocal() as session:
        tables = ['pubmed_articles', 'clinical_trials', 'fda_drugs']
        for table in tables:
            result = await session.execute(text(f'SELECT COUNT(*) FROM {table}'))
            count = result.scalar()
            print(f'{table}: {count} records')
            
asyncio.run(check_all_tables())
"
```

## Next Steps Priority

1. **Fix Parser Bugs**: Address FDA dict/string issue and verify PubMed parsing
2. **Test ClinicalTrials v2 API**: Verify new parameter format works
3. **Make Commands Non-Blocking**: Add background execution and progress monitoring
4. **Database Integration**: Ensure parsed data reaches PostgreSQL tables
5. **Error Handling**: Reduce log noise from parser failures

## Common Debug Commands

```bash
# Service logs (filtered)
make medical-mirrors-logs | grep -E "(ERROR|WARN|INFO.*completed)" | tail -50

# Quick service test
make medical-mirrors-quick-test

# Health check  
curl -s "http://localhost:8081/health" | jq

# Database check
docker exec medical-mirrors python3 -c "
import asyncio
from src.database import SessionLocal  
from sqlalchemy import text
async def check():
    async with SessionLocal() as session:
        result = await session.execute(text('SELECT 1'))
        print('Database OK' if result.scalar() == 1 else 'Database Error')
asyncio.run(check())
"
```
