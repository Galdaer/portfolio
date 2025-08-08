# Medical Data Troubleshooting Instructions

## Strategic Purpose

**RELIABLE MEDICAL DATA PIPELINE OPERATIONS**: Provide systematic diagnostic and repair patterns for medical data acquisition, processing, and integration issues within healthcare AI systems.

Establish comprehensive troubleshooting methodologies that maintain healthcare compliance while ensuring continuous access to critical medical data sources for clinical decision support and research operations.

## Medical Data Pipeline Troubleshooting Framework

### Systematic Diagnostic Process (Proven 2025-08-08)

**EVIDENCE-BASED METHODOLOGY** derived from FDA Orange Book and ClinicalTrials.gov troubleshooting:

```bash
# Phase 1: Network Connectivity Diagnosis
echo "🔍 Phase 1: Network Connectivity Diagnosis"

# DNS Resolution Testing
nslookup clinicaltrials.gov
nslookup www.fda.gov
nslookup ftp.ncbi.nlm.nih.gov

# HTTP/HTTPS Connectivity
curl -I "https://clinicaltrials.gov" --connect-timeout 10
curl -I "https://www.fda.gov" --connect-timeout 10
curl -I "https://ftp.ncbi.nlm.nih.gov" --connect-timeout 10

# Phase 2: API Endpoint Validation
echo "🔍 Phase 2: API Endpoint Validation"

# Test API endpoints with minimal parameters
curl -G "https://clinicaltrials.gov/api/v2/studies" \
    --data-urlencode "pageSize=10" \
    --connect-timeout 10 -s | head -20

# Test FDA data endpoints
curl -I "https://www.fda.gov/media/76860/download" --connect-timeout 10

# Phase 3: Parameter Validation
echo "🔍 Phase 3: Parameter Validation"

# Test simplified parameters vs complex parameters
curl -G "https://clinicaltrials.gov/api/v2/studies" \
    --data-urlencode "pageSize=10" \
    --data-urlencode "format=json" \
    --connect-timeout 10 -s | jq '.totalCount'
```

### Medical Data Download Issue Patterns

#### Pattern 1: Government API Parameter Evolution

**Problem**: Medical APIs change parameter structures causing 400 Bad Request errors
**Root Cause**: APIs evolve and deprecate certain parameter formats
**Detection**: Previously working API calls now return client errors

**PROVEN SOLUTION** (Based on ClinicalTrials.gov API troubleshooting):

```python
# Pattern: Progressive parameter simplification for medical APIs
class MedicalAPIParameterTroubleshooting:
    """Systematically diagnose and fix medical API parameter issues"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
    def diagnose_api_parameter_issues(self, api_url: str, 
                                    problematic_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Progressive parameter testing to identify API compatibility issues
        
        Args:
            api_url: The API endpoint URL
            problematic_params: Parameters that are currently failing
            
        Returns:
            Diagnostic results with working parameter combinations
        """
        diagnosis = {
            'api_url': api_url,
            'original_params': problematic_params,
            'working_params': None,
            'parameter_issues': [],
            'recommendations': []
        }
        
        # Step 1: Test minimal parameters first
        minimal_params = {'pageSize': 10}
        if self._test_api_params(api_url, minimal_params):
            diagnosis['working_params'] = minimal_params
            self.logger.info("✅ Minimal parameters work - issue is with complex parameters")
        else:
            diagnosis['parameter_issues'].append("API endpoint not responding to any parameters")
            return diagnosis
        
        # Step 2: Progressive parameter addition
        parameter_tests = [
            {'pageSize': 10, 'format': 'json'},
            {'pageSize': 10, 'format': 'json', 'countTotal': True},
            {'pageSize': 1000, 'format': 'json', 'countTotal': True}
        ]
        
        for test_params in parameter_tests:
            if self._test_api_params(api_url, test_params):
                diagnosis['working_params'] = test_params
                self.logger.info(f"✅ Working parameters: {test_params}")
            else:
                diagnosis['parameter_issues'].append(f"Failed parameters: {test_params}")
        
        # Step 3: Identify problematic parameters
        problematic_keys = []
        for key, value in problematic_params.items():
            if key not in diagnosis['working_params']:
                test_params = diagnosis['working_params'].copy()
                test_params[key] = value
                
                if not self._test_api_params(api_url, test_params):
                    problematic_keys.append(key)
                    diagnosis['parameter_issues'].append(f"Problematic parameter: {key}={value}")
        
        # Step 4: Generate recommendations
        if problematic_keys:
            diagnosis['recommendations'] = [
                f"Remove problematic parameters: {problematic_keys}",
                f"Use simplified parameters: {diagnosis['working_params']}",
                "Check API documentation for parameter format changes",
                "Consider API version updates or deprecations"
            ]
        
        return diagnosis
    
    def _test_api_params(self, api_url: str, params: Dict[str, Any]) -> bool:
        """Test if API parameters work correctly"""
        try:
            response = self.session.get(api_url, params=params, timeout=15)
            response.raise_for_status()
            
            # Validate JSON response
            data = response.json()
            if 'totalCount' in data or 'total' in data:
                return True
                
        except Exception as e:
            self.logger.warning(f"Parameter test failed: {params} - {e}")
            
        return False
```

#### Pattern 2: URL Structure Changes in Medical Data Sources

**Problem**: Medical data download URLs change without notice (404 errors)
**Root Cause**: Government sites restructure URLs or add required parameters
**Detection**: Previously working download URLs now return 404 Not Found

**PROVEN SOLUTION** (Based on FDA Orange Book URL troubleshooting):

```python
# Pattern: Medical data URL discovery and validation
class MedicalDataURLTroubleshooting:
    """Systematically diagnose and fix medical data URL issues"""
    
    def diagnose_download_url_issues(self, failed_url: str, data_type: str) -> Dict[str, Any]:
        """
        Comprehensive URL troubleshooting for medical data sources
        
        Args:
            failed_url: URL that is currently failing
            data_type: Type of medical data (e.g., 'orange_book', 'clinical_trials')
            
        Returns:
            Diagnostic results with working URL alternatives
        """
        diagnosis = {
            'failed_url': failed_url,
            'data_type': data_type,
            'url_status': self._check_url_status(failed_url),
            'working_alternatives': [],
            'url_modifications': [],
            'recommendations': []
        }
        
        # Step 1: Test URL modifications for common issues
        url_modifications = self._generate_url_modifications(failed_url)
        
        for modified_url in url_modifications:
            if self._test_url_validity(modified_url):
                diagnosis['working_alternatives'].append(modified_url)
                diagnosis['url_modifications'].append({
                    'original': failed_url,
                    'modified': modified_url,
                    'modification_type': self._identify_modification_type(failed_url, modified_url)
                })
                
                self.logger.info(f"✅ Working URL found: {modified_url}")
        
        # Step 2: Discover alternatives via web scraping
        if data_type in ['orange_book', 'fda_data']:
            scraped_alternatives = self._scrape_fda_data_urls(data_type)
            diagnosis['working_alternatives'].extend(scraped_alternatives)
        
        # Step 3: Generate actionable recommendations
        if diagnosis['working_alternatives']:
            diagnosis['recommendations'] = [
                f"Replace {failed_url} with working alternative",
                "Update download script with new URL",
                "Add URL validation before downloads",
                "Implement periodic URL health checks"
            ]
        else:
            diagnosis['recommendations'] = [
                "Manual investigation required - check official documentation",
                "Contact data source provider for current URLs",
                "Implement alternative data source strategy"
            ]
        
        return diagnosis
    
    def _generate_url_modifications(self, original_url: str) -> List[str]:
        """Generate common URL modifications to test"""
        modifications = []
        
        # Add common URL parameters
        if '?' not in original_url:
            modifications.extend([
                f"{original_url}?attachment",
                f"{original_url}?download=true",
                f"{original_url}?format=download"
            ])
        
        # Try HTTPS if HTTP
        if original_url.startswith('http://'):
            modifications.append(original_url.replace('http://', 'https://'))
        
        # Try with www prefix
        if '://www.' not in original_url:
            modifications.append(original_url.replace('://', '://www.'))
        
        # Try different domain patterns
        if 'download.fda.gov' in original_url:
            modifications.append(original_url.replace('download.fda.gov', 'www.fda.gov/media'))
        
        return modifications
    
    def _test_url_validity(self, url: str) -> bool:
        """Test if URL is valid and returns expected content"""
        try:
            response = self.session.head(url, timeout=15, allow_redirects=True)
            
            # Check status code
            if response.status_code != 200:
                return False
            
            # Check content type for downloads
            content_type = response.headers.get('content-type', '').lower()
            valid_types = ['application/zip', 'application/octet-stream', 'text/plain', 'text/csv']
            
            if any(vtype in content_type for vtype in valid_types):
                return True
            
            # Check content length (downloads should have substantial size)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 1000:  # At least 1KB
                return True
                
        except Exception as e:
            self.logger.warning(f"URL test failed: {url} - {e}")
            
        return False
    
    def _scrape_fda_data_urls(self, data_type: str) -> List[str]:
        """Scrape FDA website for current data download URLs"""
        fda_pages = {
            'orange_book': 'https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files',
            'fda_data': 'https://www.fda.gov/drugs/drug-approvals-and-databases/drugs-fda-data-files'
        }
        
        if data_type not in fda_pages:
            return []
        
        try:
            response = self.session.get(fda_pages[data_type], timeout=15)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            download_urls = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if self._is_download_link(href):
                    full_url = self._resolve_relative_url(href, fda_pages[data_type])
                    if self._test_url_validity(full_url):
                        download_urls.append(full_url)
            
            return download_urls
            
        except Exception as e:
            self.logger.error(f"Failed to scrape FDA URLs: {e}")
            return []
```

#### Pattern 3: Defunct Medical Data Domains

**Problem**: Entire medical data domains become NXDOMAIN (not found)
**Root Cause**: Government restructuring moves data to different domains
**Detection**: DNS resolution fails completely

**PROVEN SOLUTION** (Based on download.fda.gov NXDOMAIN troubleshooting):

```python
# Pattern: Defunct domain detection and alternative discovery
class DefunctMedicalDomainHandler:
    """Handle defunct medical data domains with systematic alternatives"""
    
    def handle_defunct_domain(self, defunct_domain: str, data_context: str) -> Dict[str, Any]:
        """
        Systematic handling of defunct medical data domains
        
        Args:
            defunct_domain: Domain that is NXDOMAIN
            data_context: Context about what data was expected from this domain
            
        Returns:
            Alternative domain strategies and replacement URLs
        """
        strategy = {
            'defunct_domain': defunct_domain,
            'dns_status': 'NXDOMAIN',
            'alternative_domains': [],
            'replacement_strategy': {},
            'immediate_actions': []
        }
        
        # Step 1: Identify alternative domains based on context
        if 'fda.gov' in defunct_domain:
            strategy['alternative_domains'] = [
                'www.fda.gov',
                'www.accessdata.fda.gov',
                'fda.gov'
            ]
            strategy['replacement_strategy'] = {
                'primary': 'https://www.fda.gov/drugs/drug-approvals-and-databases',
                'data_files': 'https://www.fda.gov/drugs/drug-approvals-and-databases/drugs-fda-data-files',
                'search_strategy': 'scrape_current_fda_download_pages'
            }
        
        elif 'nih.gov' in defunct_domain or 'nlm.nih.gov' in defunct_domain:
            strategy['alternative_domains'] = [
                'ftp.ncbi.nlm.nih.gov',
                'www.ncbi.nlm.nih.gov',
                'pubmed.ncbi.nlm.nih.gov'
            ]
        
        elif 'clinicaltrials.gov' in defunct_domain:
            strategy['alternative_domains'] = [
                'clinicaltrials.gov',
                'classic.clinicaltrials.gov'
            ]
        
        # Step 2: Test alternative domains
        working_alternatives = []
        for alt_domain in strategy['alternative_domains']:
            if self._test_domain_connectivity(alt_domain):
                working_alternatives.append(alt_domain)
                self.logger.info(f"✅ Alternative domain working: {alt_domain}")
        
        strategy['working_alternatives'] = working_alternatives
        
        # Step 3: Define immediate actions
        strategy['immediate_actions'] = [
            f"Update all references from {defunct_domain} to working alternatives",
            "Add domain validation to download scripts",
            "Implement periodic domain health monitoring",
            "Document domain change in medical data source logs"
        ]
        
        return strategy
    
    def _test_domain_connectivity(self, domain: str) -> bool:
        """Test if domain is accessible via DNS and HTTP"""
        try:
            # DNS test
            import socket
            socket.gethostbyname(domain)
            
            # HTTP test
            response = self.session.head(f"https://{domain}", timeout=10)
            return response.status_code < 400
            
        except Exception:
            return False
```

## Medical Data Error Recovery Patterns

### Automated Recovery Strategies

```python
# Pattern: Automated medical data pipeline recovery
class MedicalDataPipelineRecovery:
    """Automated recovery for medical data pipeline failures"""
    
    def __init__(self):
        self.url_troubleshooter = MedicalDataURLTroubleshooting()
        self.api_troubleshooter = MedicalAPIParameterTroubleshooting()
        self.domain_handler = DefunctMedicalDomainHandler()
        
    def execute_recovery_protocol(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute comprehensive recovery protocol for medical data failures
        
        Args:
            error_context: Details about the failure (URL, error type, data source)
            
        Returns:
            Recovery results with updated configurations
        """
        recovery_plan = {
            'error_type': error_context.get('error_type'),
            'failed_source': error_context.get('source'),
            'recovery_actions': [],
            'updated_config': {},
            'success': False
        }
        
        # Route to appropriate recovery strategy
        if error_context.get('error_type') == 'http_404':
            recovery_plan = self._recover_from_404_error(error_context, recovery_plan)
            
        elif error_context.get('error_type') == 'http_400':
            recovery_plan = self._recover_from_400_error(error_context, recovery_plan)
            
        elif error_context.get('error_type') == 'dns_nxdomain':
            recovery_plan = self._recover_from_nxdomain_error(error_context, recovery_plan)
            
        # Generate updated configuration
        if recovery_plan['success']:
            recovery_plan['updated_config'] = self._generate_updated_config(
                error_context, recovery_plan
            )
        
        return recovery_plan
    
    def _recover_from_404_error(self, error_context: Dict[str, Any], 
                               recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from 404 URL not found errors"""
        failed_url = error_context.get('url')
        data_type = error_context.get('data_type')
        
        url_diagnosis = self.url_troubleshooter.diagnose_download_url_issues(
            failed_url, data_type
        )
        
        if url_diagnosis['working_alternatives']:
            recovery_plan['recovery_actions'].extend([
                f"Replace {failed_url} with {url_diagnosis['working_alternatives'][0]}",
                "Update download script configuration",
                "Validate new URL before deployment"
            ])
            recovery_plan['success'] = True
            recovery_plan['new_url'] = url_diagnosis['working_alternatives'][0]
        
        return recovery_plan
    
    def _recover_from_400_error(self, error_context: Dict[str, Any], 
                               recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from 400 Bad Request API errors"""
        api_url = error_context.get('url')
        failed_params = error_context.get('parameters', {})
        
        api_diagnosis = self.api_troubleshooter.diagnose_api_parameter_issues(
            api_url, failed_params
        )
        
        if api_diagnosis['working_params']:
            recovery_plan['recovery_actions'].extend([
                f"Replace API parameters with working set: {api_diagnosis['working_params']}",
                "Update API call configuration",
                "Test API parameters before deployment"
            ])
            recovery_plan['success'] = True
            recovery_plan['new_params'] = api_diagnosis['working_params']
        
        return recovery_plan
    
    def _recover_from_nxdomain_error(self, error_context: Dict[str, Any], 
                                   recovery_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Recover from DNS NXDOMAIN errors"""
        defunct_domain = error_context.get('domain')
        data_context = error_context.get('data_context')
        
        domain_strategy = self.domain_handler.handle_defunct_domain(
            defunct_domain, data_context
        )
        
        if domain_strategy['working_alternatives']:
            recovery_plan['recovery_actions'].extend([
                f"Replace {defunct_domain} with {domain_strategy['working_alternatives'][0]}",
                "Update all domain references",
                "Implement domain health monitoring"
            ])
            recovery_plan['success'] = True
            recovery_plan['new_domain'] = domain_strategy['working_alternatives'][0]
        
        return recovery_plan
```

## Implementation Guidelines

### Integration with Existing Medical Data Scripts

1. **Add diagnostic functions**: Integrate troubleshooting patterns before download attempts
2. **Implement recovery protocols**: Add automated recovery for common failure patterns
3. **Create monitoring alerts**: Set up proactive monitoring for medical data source health
4. **Update error handling**: Replace generic error messages with specific troubleshooting guidance

### Healthcare Compliance Integration

- **Audit logging**: Log all troubleshooting actions and recovery attempts
- **Data integrity validation**: Ensure recovered data sources provide equivalent medical data quality
- **PHI protection**: Maintain privacy standards during troubleshooting processes
- **Clinical impact assessment**: Evaluate impact of data source failures on healthcare operations

### Monitoring and Alerting Strategy

```python
# Pattern: Medical data source health monitoring
class MedicalDataSourceHealthMonitor:
    """Continuous health monitoring for medical data sources"""
    
    def create_monitoring_configuration(self) -> Dict[str, Any]:
        """Create comprehensive monitoring for all medical data sources"""
        return {
            'health_checks': {
                'interval': '15_minutes',
                'timeout': '30_seconds',
                'retry_attempts': 3
            },
            'alert_thresholds': {
                'response_time': '10_seconds',
                'error_rate': '5_percent',
                'consecutive_failures': 3
            },
            'escalation_policy': {
                'immediate': ['dns_failure', 'authentication_failure'],
                'urgent': ['api_parameter_errors', 'data_format_changes'],
                'warning': ['slow_response_times', 'intermittent_failures']
            },
            'recovery_automation': {
                'enable_auto_recovery': True,
                'max_recovery_attempts': 3,
                'recovery_cooldown': '5_minutes'
            }
        }
```

This comprehensive troubleshooting framework ensures reliable medical data pipeline operations while maintaining healthcare compliance and providing systematic recovery strategies for common medical data source issues.
