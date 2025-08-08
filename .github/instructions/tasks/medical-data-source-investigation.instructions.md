# Medical Data Source Investigation Instructions

## Strategic Purpose

**RESILIENT MEDICAL DATA ACQUISITION**: Provide systematic patterns for investigating, validating, and maintaining access to critical medical data sources (PubMed, FDA, ClinicalTrials.gov, etc.) with adaptive strategies for API changes and network connectivity issues.

Establish comprehensive troubleshooting methodologies that enable rapid diagnosis and resolution of medical data access problems while maintaining healthcare compliance and data integrity.

## Medical Data Source Investigation Framework

### Systematic Connectivity Diagnosis Process

**PROVEN METHODOLOGY** (Based on 2025-08-08 FDA/ClinicalTrials troubleshooting):

```bash
# Step 1: DNS Resolution Testing
nslookup target.domain.gov
nslookup www.target.domain.gov
dig target.domain.gov

# Step 2: Basic HTTP/HTTPS Connectivity
curl -I "https://target.domain.gov" --connect-timeout 10
curl -I "https://www.target.domain.gov" --connect-timeout 10

# Step 3: API Endpoint Validation
curl -G "https://api.target.gov/endpoint" \
    --data-urlencode "parameter=value" \
    --connect-timeout 10 -s | head -10

# Step 4: Alternative Domain Discovery
curl -I "https://main-site.gov/data-section" --connect-timeout 10
```

### Medical Data Source Validation Patterns

#### Pattern 1: Government Medical Domain Changes

**Problem**: Medical data domains frequently change or get retired
**Detection**: NXDOMAIN errors, 404 responses on previously working URLs
**Solution Process**:

```python
# Pattern: Systematic domain validation for medical sources
class MedicalDomainValidator:
    """Validate and discover correct medical data source URLs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Medical Research Bot - Healthcare AI System'
        })
    
    def validate_medical_domain(self, domain: str) -> Dict[str, Any]:
        """
        Comprehensive medical domain validation
        
        Returns:
            - DNS resolution status
            - HTTP connectivity status  
            - Alternative domain suggestions
            - Working URL discovery results
        """
        results = {
            'domain': domain,
            'dns_resolution': False,
            'http_connectivity': False,
            'alternatives': [],
            'working_urls': [],
            'recommendations': []
        }
        
        # Step 1: DNS Resolution
        try:
            import socket
            socket.gethostbyname(domain)
            results['dns_resolution'] = True
            self.logger.info(f"✅ DNS resolution successful: {domain}")
        except socket.gaierror:
            results['dns_resolution'] = False
            self.logger.error(f"❌ DNS resolution failed: {domain}")
            results['recommendations'].append(f"Domain {domain} is defunct - research alternatives")
        
        # Step 2: HTTP Connectivity (if DNS works)
        if results['dns_resolution']:
            for protocol in ['https', 'http']:
                try:
                    url = f"{protocol}://{domain}"
                    response = self.session.head(url, timeout=10)
                    if response.status_code < 400:
                        results['http_connectivity'] = True
                        results['working_urls'].append(url)
                        self.logger.info(f"✅ HTTP connectivity: {url}")
                        break
                except Exception as e:
                    self.logger.warning(f"❌ HTTP connectivity failed: {url} - {e}")
        
        return results
    
    def discover_alternative_sources(self, original_domain: str, data_type: str) -> List[str]:
        """
        Discover alternative sources for medical data
        
        Args:
            original_domain: The failed domain
            data_type: Type of data (e.g., 'fda_drug_labels', 'clinical_trials')
        """
        alternatives = []
        
        # Pattern: Government site alternatives
        if 'fda.gov' in original_domain:
            alternatives.extend([
                'https://www.fda.gov/drugs/drug-approvals-and-databases',
                'https://www.fda.gov/drugs/drug-approvals-and-databases/drugs-fda-data-files',
                'https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files'
            ])
        
        if 'clinicaltrials.gov' in original_domain:
            alternatives.extend([
                'https://clinicaltrials.gov/api/v2/studies',
                'https://clinicaltrials.gov/data-api/about-api',
                'https://classic.clinicaltrials.gov/ct2/resources/download'
            ])
        
        # Validate alternatives
        working_alternatives = []
        for alt_url in alternatives:
            try:
                response = self.session.head(alt_url, timeout=10)
                if response.status_code < 400:
                    working_alternatives.append(alt_url)
                    self.logger.info(f"✅ Alternative source working: {alt_url}")
            except Exception as e:
                self.logger.warning(f"❌ Alternative failed: {alt_url} - {e}")
        
        return working_alternatives
```

#### Pattern 2: API Parameter Evolution Detection

**Problem**: Medical APIs change parameters causing 400/401 errors
**Detection**: Previously working API calls returning client errors
**Solution Process**:

```python
# Pattern: API parameter validation and adaptation
class MedicalAPIParameterDiscovery:
    """Discover and validate correct API parameters for medical data sources"""
    
    def test_api_parameter_combinations(self, base_url: str, 
                                      parameter_sets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test multiple parameter combinations to find working API calls
        
        Args:
            base_url: The API endpoint base URL
            parameter_sets: List of parameter dictionaries to test
        """
        results = {
            'working_parameters': [],
            'failed_parameters': [],
            'optimal_parameters': None,
            'error_patterns': []
        }
        
        for i, params in enumerate(parameter_sets):
            try:
                self.logger.info(f"Testing parameter set {i+1}: {params}")
                
                response = self.session.get(base_url, params=params, timeout=15)
                response.raise_for_status()
                
                # Success - analyze response
                data = response.json()
                total_count = data.get('totalCount', data.get('total', 0))
                
                results['working_parameters'].append({
                    'params': params,
                    'response_size': len(response.content),
                    'total_records': total_count,
                    'response_time': response.elapsed.total_seconds()
                })
                
                self.logger.info(f"✅ Parameter set {i+1} successful: {total_count} records")
                
            except requests.exceptions.HTTPError as e:
                error_info = {
                    'params': params,
                    'status_code': e.response.status_code,
                    'error_message': str(e)
                }
                results['failed_parameters'].append(error_info)
                results['error_patterns'].append(e.response.status_code)
                
                self.logger.error(f"❌ Parameter set {i+1} failed: {e}")
                
            except Exception as e:
                self.logger.error(f"❌ Parameter set {i+1} error: {e}")
        
        # Determine optimal parameters
        if results['working_parameters']:
            # Choose parameters with best balance of records and response time
            optimal = max(results['working_parameters'], 
                         key=lambda x: (x['total_records'], -x['response_time']))
            results['optimal_parameters'] = optimal['params']
            
            self.logger.info(f"🎯 Optimal parameters: {optimal['params']}")
        
        return results
    
    def generate_clinicaltrials_parameter_sets(self) -> List[Dict[str, Any]]:
        """Generate parameter sets to test for ClinicalTrials.gov API"""
        return [
            # Minimal parameters (most likely to work)
            {'pageSize': 10},
            
            # Basic formatting
            {'pageSize': 10, 'format': 'json'},
            
            # Add count total
            {'pageSize': 10, 'format': 'json', 'countTotal': True},
            
            # Increase page size
            {'pageSize': 1000, 'format': 'json', 'countTotal': True},
            
            # Add simple filter
            {'pageSize': 1000, 'format': 'json', 'countTotal': True, 
             'filter.overallStatus': 'COMPLETED'},
            
            # Multiple statuses (problematic format)
            {'pageSize': 1000, 'format': 'json', 'countTotal': True,
             'filter.overallStatus': ['COMPLETED', 'TERMINATED']},
            
            # Original problematic parameters
            {'format': 'json', 'markupFormat': 'markdown', 'countTotal': True,
             'pageSize': 1000, 'filter.overallStatus': ['COMPLETED', 'TERMINATED', 'WITHDRAWN'],
             'filter.hasResults': 'true', 'pageToken': 1}
        ]
```

### Medical Data Source Documentation Pattern

#### Pattern 3: Proactive URL Discovery via Web Scraping

**When official documentation is unclear or outdated**:

```python
# Pattern: Web scraping for medical data source discovery
class MedicalDataSourceDiscovery:
    """Discover current medical data download URLs via web scraping"""
    
    def discover_fda_data_sources(self) -> Dict[str, List[str]]:
        """
        Scrape FDA website to discover current data download URLs
        
        Returns categorized URLs for different FDA data types
        """
        fda_data_pages = [
            'https://www.fda.gov/drugs/drug-approvals-and-databases',
            'https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files',
            'https://www.fda.gov/drugs/drug-approvals-and-databases/drugs-fda-data-files',
            'https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory'
        ]
        
        discovered_urls = {
            'orange_book': [],
            'drug_labels': [],
            'ndc_directory': [],
            'drugs_fda': []
        }
        
        for page_url in fda_data_pages:
            try:
                self.logger.info(f"Scraping FDA data page: {page_url}")
                
                response = self.session.get(page_url, timeout=15)
                response.raise_for_status()
                
                # Parse HTML for download links
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for direct download links
                download_links = soup.find_all('a', href=True)
                for link in download_links:
                    href = link.get('href')
                    if self._is_fda_data_download_link(href):
                        category = self._categorize_fda_data_link(href, link.text)
                        if category in discovered_urls:
                            full_url = self._resolve_relative_url(href, page_url)
                            discovered_urls[category].append({
                                'url': full_url,
                                'text': link.text.strip(),
                                'source_page': page_url
                            })
                
                self.logger.info(f"Found {sum(len(urls) for urls in discovered_urls.values())} data URLs")
                
            except Exception as e:
                self.logger.error(f"Failed to scrape {page_url}: {e}")
        
        return discovered_urls
    
    def _is_fda_data_download_link(self, href: str) -> bool:
        """Check if URL appears to be a data download link"""
        if not href:
            return False
        
        download_indicators = [
            '.zip', '.csv', '.txt', '.xml', '.json',
            'download', 'media/', 'export', 'bulk'
        ]
        
        return any(indicator in href.lower() for indicator in download_indicators)
    
    def _categorize_fda_data_link(self, href: str, link_text: str) -> str:
        """Categorize FDA data link by content type"""
        href_lower = href.lower()
        text_lower = link_text.lower()
        
        if 'orange' in text_lower or 'orange' in href_lower:
            return 'orange_book'
        elif 'ndc' in text_lower or 'ndc' in href_lower:
            return 'ndc_directory'
        elif 'label' in text_lower or 'label' in href_lower:
            return 'drug_labels'
        elif 'drugs' in text_lower or 'drugs' in href_lower:
            return 'drugs_fda'
        else:
            return 'other'
```

## Medical Data Source Maintenance Strategy

### Proactive Monitoring Pattern

```python
# Pattern: Automated medical data source health monitoring
class MedicalDataSourceMonitor:
    """Monitor medical data sources for changes and issues"""
    
    def __init__(self):
        self.validator = MedicalDomainValidator()
        self.api_tester = MedicalAPIParameterDiscovery()
        
    def create_health_check_schedule(self) -> Dict[str, Any]:
        """
        Create monitoring schedule for all medical data sources
        
        Returns configuration for automated health checks
        """
        return {
            'schedule': {
                'daily': ['api_connectivity', 'parameter_validation'],
                'weekly': ['url_discovery', 'alternative_source_validation'],
                'monthly': ['comprehensive_audit', 'documentation_update']
            },
            'sources': {
                'pubmed': {
                    'ftp_baseline': 'https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/',
                    'ftp_updates': 'https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/',
                    'critical': True  # Essential for literature search
                },
                'clinicaltrials': {
                    'api_v2': 'https://clinicaltrials.gov/api/v2/studies',
                    'critical': True  # Essential for clinical data
                },
                'fda': {
                    'orange_book': 'https://www.fda.gov/media/76860/download?attachment',
                    'main_site': 'https://www.fda.gov/drugs/drug-approvals-and-databases',
                    'critical': True  # Essential for drug data
                }
            },
            'alerts': {
                'immediate': ['dns_failure', 'api_auth_failure'],
                'daily': ['response_time_degradation', 'data_format_changes'],
                'weekly': ['alternative_source_discovery']
            }
        }
```

## Crisis Response Patterns

### Emergency Data Access Strategy

```python
# Pattern: Emergency fallback when primary medical data sources fail
class EmergencyMedicalDataStrategy:
    """Emergency strategies when critical medical data sources fail"""
    
    def execute_emergency_protocol(self, failed_source: str, data_type: str) -> Dict[str, Any]:
        """
        Execute emergency protocol for failed medical data source
        
        Prioritizes maintaining healthcare system functionality
        """
        emergency_plan = {
            'immediate_actions': [],
            'fallback_sources': [],
            'cache_utilization': [],
            'user_notifications': []
        }
        
        # Step 1: Activate local caches
        emergency_plan['cache_utilization'] = [
            'utilize_existing_local_data',
            'activate_emergency_cache_extension',
            'validate_cache_data_currency'
        ]
        
        # Step 2: Identify alternative sources
        if 'fda' in failed_source.lower():
            emergency_plan['fallback_sources'] = [
                'https://drugcentral.org',  # Alternative drug database
                'https://www.accessdata.fda.gov',  # FDA alternative interface
                'https://dailymed.nlm.nih.gov'  # NIH drug labels
            ]
        
        if 'clinicaltrials' in failed_source.lower():
            emergency_plan['fallback_sources'] = [
                'https://www.who.int/clinical-trials-registry-platform',
                'https://www.isrctn.com',  # International trial registry
                'https://euclinicaltrials.eu'  # European trials
            ]
        
        # Step 3: Immediate user notification
        emergency_plan['user_notifications'] = [
            f"Medical data source {failed_source} temporarily unavailable",
            f"Using cached data and alternative sources for {data_type}",
            "Healthcare system functionality maintained via backup protocols"
        ]
        
        return emergency_plan
```

## Implementation Guidelines

### Integration with Existing Systems

1. **Add to download scripts**: Integrate validation patterns before attempting downloads
2. **Create monitoring service**: Implement health check scheduler for continuous monitoring  
3. **Update error handling**: Replace generic network errors with specific medical data source guidance
4. **Documentation updates**: Maintain current status and alternative sources for all medical APIs

### Healthcare Compliance Considerations

- **Data integrity**: Validate that alternative sources provide equivalent medical data quality
- **Audit trails**: Log all data source changes and fallback activations
- **PHI protection**: Ensure alternative sources maintain same privacy standards
- **Clinical safety**: Never compromise healthcare system availability due to data source issues

This framework provides systematic approaches to medical data source investigation, ensuring resilient access to critical healthcare data while maintaining compliance and system reliability.
