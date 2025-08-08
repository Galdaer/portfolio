# Medical Data Pipeline Management Instructions

## Strategic Purpose

**COMPREHENSIVE MEDICAL DATA INFRASTRUCTURE ORCHESTRATION**: Provide systematic patterns for managing large-scale medical data acquisition, processing, and integration pipelines while maintaining healthcare compliance, data integrity, and operational reliability.

Establish robust pipeline management methodologies that ensure continuous availability of critical medical data for healthcare AI systems, clinical decision support, and medical research operations.

## Medical Data Pipeline Architecture

### Multi-Source Medical Data Orchestration

**ENTERPRISE-GRADE PIPELINE DESIGN** (Supporting 242GB+ medical data acquisition):

```python
# Pattern: Comprehensive medical data pipeline orchestration
class MedicalDataPipelineOrchestrator:
    """Orchestrate multi-source medical data acquisition and processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_sources = self._initialize_medical_data_sources()
        self.storage_manager = MedicalDataStorageManager()
        self.compliance_validator = HealthcareComplianceValidator()
        
    def _initialize_medical_data_sources(self) -> Dict[str, Dict[str, Any]]:
        """Initialize configuration for all medical data sources"""
        return {
            'pubmed': {
                'type': 'ftp_archive',
                'source_urls': {
                    'baseline': 'https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/',
                    'updates': 'https://ftp.ncbi.nlm.nih.gov/pubmed/updatefiles/'
                },
                'data_format': 'xml',
                'estimated_size': '180GB',
                'update_frequency': 'daily',
                'priority': 'critical',
                'compliance_requirements': ['public_domain', 'citation_required']
            },
            'fda_orange_book': {
                'type': 'direct_download',
                'source_urls': {
                    'primary': 'https://www.fda.gov/media/76860/download?attachment'
                },
                'data_format': 'zip_csv',
                'estimated_size': '50MB',
                'update_frequency': 'monthly',
                'priority': 'critical',
                'compliance_requirements': ['fda_public_data', 'no_phi']
            },
            'clinicaltrials': {
                'type': 'api_bulk',
                'source_urls': {
                    'api_v2': 'https://clinicaltrials.gov/api/v2/studies'
                },
                'data_format': 'json',
                'estimated_size': '15GB',
                'update_frequency': 'weekly',
                'priority': 'high',
                'compliance_requirements': ['public_registry', 'research_use']
            },
            'fda_drug_labels': {
                'type': 'api_pagination',
                'source_urls': {
                    'api': 'https://api.fda.gov/drug/label.json'
                },
                'data_format': 'json',
                'estimated_size': '25GB',
                'update_frequency': 'monthly',
                'priority': 'high',
                'compliance_requirements': ['fda_public_data', 'drug_safety']
            }
        }
    
    def execute_comprehensive_pipeline(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute comprehensive medical data pipeline with full orchestration
        
        Args:
            pipeline_config: Configuration for pipeline execution
            
        Returns:
            Pipeline execution results with detailed status and metrics
        """
        execution_plan = {
            'pipeline_id': f"medical_data_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'start_time': datetime.now(),
            'data_sources': list(self.data_sources.keys()),
            'execution_phases': [],
            'status': 'initializing',
            'metrics': {},
            'compliance_checks': []
        }
        
        try:
            # Phase 1: Pre-execution validation
            self.logger.info("🔍 Phase 1: Pre-execution validation")
            validation_results = self._validate_pipeline_prerequisites(pipeline_config)
            execution_plan['execution_phases'].append({
                'phase': 'validation',
                'status': 'completed' if validation_results['all_valid'] else 'failed',
                'results': validation_results
            })
            
            if not validation_results['all_valid']:
                execution_plan['status'] = 'failed'
                return execution_plan
            
            # Phase 2: Data source health checks
            self.logger.info("🔍 Phase 2: Data source health checks")
            health_results = self._perform_data_source_health_checks()
            execution_plan['execution_phases'].append({
                'phase': 'health_checks',
                'status': 'completed',
                'results': health_results
            })
            
            # Phase 3: Parallel data acquisition
            self.logger.info("📥 Phase 3: Parallel data acquisition")
            acquisition_results = self._execute_parallel_data_acquisition(pipeline_config)
            execution_plan['execution_phases'].append({
                'phase': 'data_acquisition',
                'status': 'completed' if acquisition_results['overall_success'] else 'partial',
                'results': acquisition_results
            })
            
            # Phase 4: Data processing and validation
            self.logger.info("⚙️ Phase 4: Data processing and validation")
            processing_results = self._process_and_validate_data(acquisition_results)
            execution_plan['execution_phases'].append({
                'phase': 'data_processing',
                'status': 'completed' if processing_results['all_processed'] else 'partial',
                'results': processing_results
            })
            
            # Phase 5: Healthcare compliance validation
            self.logger.info("🔒 Phase 5: Healthcare compliance validation")
            compliance_results = self._validate_healthcare_compliance(processing_results)
            execution_plan['execution_phases'].append({
                'phase': 'compliance_validation',
                'status': 'completed' if compliance_results['compliant'] else 'failed',
                'results': compliance_results
            })
            
            # Phase 6: Database integration
            self.logger.info("💾 Phase 6: Database integration")
            integration_results = self._integrate_with_healthcare_database(processing_results)
            execution_plan['execution_phases'].append({
                'phase': 'database_integration',
                'status': 'completed' if integration_results['integration_success'] else 'failed',
                'results': integration_results
            })
            
            # Final status determination
            execution_plan['status'] = self._determine_final_status(execution_plan['execution_phases'])
            execution_plan['end_time'] = datetime.now()
            execution_plan['total_duration'] = (execution_plan['end_time'] - execution_plan['start_time']).total_seconds()
            
            # Generate comprehensive metrics
            execution_plan['metrics'] = self._generate_pipeline_metrics(execution_plan)
            
            return execution_plan
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            execution_plan['status'] = 'failed'
            execution_plan['error'] = str(e)
            return execution_plan
    
    def _execute_parallel_data_acquisition(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute parallel data acquisition from all medical sources"""
        import concurrent.futures
        import threading
        
        acquisition_results = {
            'sources_attempted': 0,
            'sources_successful': 0,
            'sources_failed': 0,
            'source_results': {},
            'overall_success': False,
            'total_data_size': 0
        }
        
        # Filter sources based on pipeline configuration
        active_sources = {
            name: config for name, config in self.data_sources.items()
            if name in pipeline_config.get('enabled_sources', self.data_sources.keys())
        }
        
        acquisition_results['sources_attempted'] = len(active_sources)
        
        # Execute parallel downloads with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_source = {
                executor.submit(self._acquire_single_source_data, source_name, source_config): source_name
                for source_name, source_config in active_sources.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_source):
                source_name = future_to_source[future]
                try:
                    source_result = future.result()
                    acquisition_results['source_results'][source_name] = source_result
                    
                    if source_result['success']:
                        acquisition_results['sources_successful'] += 1
                        acquisition_results['total_data_size'] += source_result.get('data_size', 0)
                    else:
                        acquisition_results['sources_failed'] += 1
                        
                    self.logger.info(f"{'✅' if source_result['success'] else '❌'} {source_name}: {source_result['status']}")
                    
                except Exception as e:
                    acquisition_results['sources_failed'] += 1
                    acquisition_results['source_results'][source_name] = {
                        'success': False,
                        'status': f'Exception: {e}',
                        'error': str(e)
                    }
                    self.logger.error(f"❌ {source_name} failed with exception: {e}")
        
        # Determine overall success
        success_rate = acquisition_results['sources_successful'] / acquisition_results['sources_attempted']
        acquisition_results['overall_success'] = success_rate >= 0.75  # 75% success threshold
        acquisition_results['success_rate'] = success_rate
        
        return acquisition_results
    
    def _acquire_single_source_data(self, source_name: str, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Acquire data from a single medical data source"""
        source_result = {
            'source_name': source_name,
            'success': False,
            'status': 'starting',
            'data_size': 0,
            'files_downloaded': 0,
            'download_duration': 0,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            if source_config['type'] == 'ftp_archive':
                source_result = self._acquire_ftp_archive_data(source_name, source_config, source_result)
            elif source_config['type'] == 'direct_download':
                source_result = self._acquire_direct_download_data(source_name, source_config, source_result)
            elif source_config['type'] == 'api_bulk':
                source_result = self._acquire_api_bulk_data(source_name, source_config, source_result)
            elif source_config['type'] == 'api_pagination':
                source_result = self._acquire_api_pagination_data(source_name, source_config, source_result)
            else:
                source_result['error'] = f"Unknown source type: {source_config['type']}"
                source_result['status'] = 'failed'
        
        except Exception as e:
            source_result['error'] = str(e)
            source_result['status'] = 'failed'
            self.logger.error(f"Data acquisition failed for {source_name}: {e}")
        
        source_result['download_duration'] = time.time() - start_time
        return source_result
```

### Medical Data Storage Management

```python
# Pattern: Healthcare-compliant data storage management
class MedicalDataStorageManager:
    """Manage storage of medical data with healthcare compliance"""
    
    def __init__(self):
        self.storage_config = self._initialize_storage_configuration()
        self.compliance_monitor = HealthcareStorageComplianceMonitor()
        
    def _initialize_storage_configuration(self) -> Dict[str, Any]:
        """Initialize healthcare-compliant storage configuration"""
        return {
            'primary_storage': {
                'type': 'external_drive',
                'mount_point': '/home/intelluxe/database/medical_archives_complete',
                'capacity': '4TB',
                'encryption': 'required',
                'backup_frequency': 'daily',
                'retention_policy': '7_years'  # Healthcare standard
            },
            'database_storage': {
                'type': 'postgresql',
                'host': '172.20.0.13',
                'port': 5432,
                'database': 'intelluxe_healthcare',
                'encryption_at_rest': True,
                'audit_logging': True
            },
            'cache_storage': {
                'type': 'redis',
                'host': '172.20.0.14', 
                'port': 6379,
                'ttl_default': '24_hours',
                'max_memory': '2GB'
            },
            'compliance_requirements': {
                'phi_detection': True,
                'access_logging': True,
                'data_classification': True,
                'retention_tracking': True
            }
        }
    
    def manage_medical_data_storage(self, data_source: str, 
                                  data_content: Any, 
                                  storage_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage storage of medical data with compliance validation
        
        Args:
            data_source: Source of the medical data
            data_content: The actual data content
            storage_options: Storage-specific options
            
        Returns:
            Storage results with compliance status
        """
        storage_result = {
            'data_source': data_source,
            'storage_status': 'initializing',
            'storage_locations': [],
            'compliance_status': {},
            'audit_entries': [],
            'data_classification': {}
        }
        
        try:
            # Step 1: Data classification and PHI detection
            classification_result = self._classify_medical_data(data_content, data_source)
            storage_result['data_classification'] = classification_result
            
            # Step 2: Compliance validation
            compliance_result = self._validate_storage_compliance(
                data_content, classification_result, storage_options
            )
            storage_result['compliance_status'] = compliance_result
            
            if not compliance_result['compliant']:
                storage_result['storage_status'] = 'compliance_failed'
                return storage_result
            
            # Step 3: Determine storage strategy
            storage_strategy = self._determine_storage_strategy(
                data_source, classification_result, storage_options
            )
            
            # Step 4: Execute storage operations
            storage_operations = self._execute_storage_operations(
                data_content, storage_strategy
            )
            storage_result['storage_locations'] = storage_operations['locations']
            
            # Step 5: Generate audit entries
            audit_entries = self._generate_storage_audit_entries(
                data_source, storage_operations, classification_result
            )
            storage_result['audit_entries'] = audit_entries
            
            storage_result['storage_status'] = 'completed'
            
        except Exception as e:
            storage_result['storage_status'] = 'failed'
            storage_result['error'] = str(e)
            self.logger.error(f"Medical data storage failed: {e}")
        
        return storage_result
    
    def _classify_medical_data(self, data_content: Any, data_source: str) -> Dict[str, Any]:
        """Classify medical data for appropriate storage handling"""
        classification = {
            'data_source': data_source,
            'contains_phi': False,
            'data_sensitivity': 'public',
            'retention_requirements': '7_years',
            'access_restrictions': [],
            'encryption_required': False
        }
        
        # Source-based classification
        if data_source in ['pubmed', 'clinicaltrials', 'fda_orange_book']:
            classification.update({
                'contains_phi': False,
                'data_sensitivity': 'public',
                'access_restrictions': ['research_use'],
                'encryption_required': False
            })
        
        elif 'patient' in data_source.lower() or 'clinical_notes' in data_source.lower():
            classification.update({
                'contains_phi': True,
                'data_sensitivity': 'restricted',
                'access_restrictions': ['authenticated_access', 'audit_logging', 'phi_protection'],
                'encryption_required': True
            })
        
        # Content-based PHI detection (if data is textual)
        if isinstance(data_content, str):
            phi_patterns = self._detect_phi_patterns(data_content)
            if phi_patterns['detected']:
                classification['contains_phi'] = True
                classification['data_sensitivity'] = 'restricted'
                classification['encryption_required'] = True
                classification['phi_types'] = phi_patterns['types']
        
        return classification
    
    def _execute_storage_operations(self, data_content: Any, 
                                  storage_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Execute actual storage operations based on strategy"""
        operations_result = {
            'locations': [],
            'operations_performed': [],
            'success': False,
            'total_size': 0
        }
        
        for storage_location in storage_strategy['storage_locations']:
            try:
                if storage_location['type'] == 'file_system':
                    file_result = self._store_to_filesystem(
                        data_content, storage_location
                    )
                    operations_result['locations'].append(file_result)
                    
                elif storage_location['type'] == 'database':
                    db_result = self._store_to_database(
                        data_content, storage_location
                    )
                    operations_result['locations'].append(db_result)
                    
                elif storage_location['type'] == 'cache':
                    cache_result = self._store_to_cache(
                        data_content, storage_location
                    )
                    operations_result['locations'].append(cache_result)
                
                operations_result['operations_performed'].append(
                    f"Stored to {storage_location['type']}: {storage_location['path']}"
                )
                
            except Exception as e:
                self.logger.error(f"Storage operation failed for {storage_location}: {e}")
                operations_result['locations'].append({
                    'type': storage_location['type'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Determine overall success
        successful_ops = sum(1 for loc in operations_result['locations'] 
                           if loc.get('status') == 'success')
        operations_result['success'] = successful_ops > 0
        
        return operations_result
```

### Medical Data Pipeline Monitoring

```python
# Pattern: Comprehensive pipeline monitoring and alerting
class MedicalDataPipelineMonitor:
    """Monitor medical data pipeline operations with healthcare-specific alerts"""
    
    def __init__(self):
        self.monitoring_config = self._initialize_monitoring_configuration()
        self.alert_manager = HealthcareAlertManager()
        
    def _initialize_monitoring_configuration(self) -> Dict[str, Any]:
        """Initialize healthcare-specific monitoring configuration"""
        return {
            'pipeline_metrics': {
                'execution_frequency': 'daily',
                'success_rate_threshold': 0.90,
                'data_freshness_threshold': '48_hours',
                'error_escalation_threshold': 3
            },
            'data_source_monitoring': {
                'availability_check_interval': '15_minutes',
                'response_time_threshold': '30_seconds',
                'data_integrity_validation': True,
                'compliance_monitoring': True
            },
            'storage_monitoring': {
                'disk_usage_threshold': 0.85,
                'backup_validation': 'daily',
                'encryption_verification': True,
                'access_pattern_analysis': True
            },
            'compliance_monitoring': {
                'phi_detection_alerts': True,
                'audit_log_validation': 'hourly',
                'retention_policy_enforcement': True,
                'access_control_verification': True
            }
        }
    
    def execute_comprehensive_monitoring(self) -> Dict[str, Any]:
        """Execute comprehensive monitoring of medical data pipeline"""
        monitoring_results = {
            'monitoring_timestamp': datetime.now(),
            'overall_health': 'unknown',
            'pipeline_status': {},
            'data_source_status': {},
            'storage_status': {},
            'compliance_status': {},
            'alerts_generated': [],
            'recommendations': []
        }
        
        try:
            # Monitor pipeline execution status
            pipeline_status = self._monitor_pipeline_execution()
            monitoring_results['pipeline_status'] = pipeline_status
            
            # Monitor data source availability
            source_status = self._monitor_data_source_availability()
            monitoring_results['data_source_status'] = source_status
            
            # Monitor storage systems
            storage_status = self._monitor_storage_systems()
            monitoring_results['storage_status'] = storage_status
            
            # Monitor compliance requirements
            compliance_status = self._monitor_compliance_requirements()
            monitoring_results['compliance_status'] = compliance_status
            
            # Generate alerts based on monitoring results
            alerts = self._generate_alerts(monitoring_results)
            monitoring_results['alerts_generated'] = alerts
            
            # Generate recommendations
            recommendations = self._generate_recommendations(monitoring_results)
            monitoring_results['recommendations'] = recommendations
            
            # Determine overall health
            monitoring_results['overall_health'] = self._determine_overall_health(monitoring_results)
            
        except Exception as e:
            monitoring_results['overall_health'] = 'error'
            monitoring_results['error'] = str(e)
            self.logger.error(f"Monitoring execution failed: {e}")
        
        return monitoring_results
    
    def _monitor_pipeline_execution(self) -> Dict[str, Any]:
        """Monitor the execution status of medical data pipelines"""
        return {
            'last_execution': self._get_last_pipeline_execution(),
            'success_rate': self._calculate_pipeline_success_rate(),
            'average_execution_time': self._calculate_average_execution_time(),
            'data_freshness': self._check_data_freshness(),
            'error_patterns': self._analyze_error_patterns()
        }
    
    def _monitor_data_source_availability(self) -> Dict[str, Any]:
        """Monitor availability of all medical data sources"""
        source_results = {}
        
        for source_name, source_config in self.data_sources.items():
            source_results[source_name] = {
                'availability': self._check_source_availability(source_config),
                'response_time': self._measure_source_response_time(source_config),
                'data_integrity': self._validate_source_data_integrity(source_config),
                'last_successful_access': self._get_last_successful_access(source_name)
            }
        
        return source_results
```

## Implementation Guidelines

### Integration with Existing Healthcare Infrastructure

1. **Database Integration**: Connect pipeline to PostgreSQL healthcare database with proper schema
2. **Compliance Validation**: Integrate with healthcare compliance monitoring systems
3. **Error Recovery**: Implement automated recovery for common medical data pipeline failures
4. **Monitoring Integration**: Connect to existing healthcare system monitoring infrastructure

### Healthcare-Specific Considerations

- **Data Integrity**: Validate medical data quality and completeness throughout pipeline
- **Compliance Auditing**: Maintain comprehensive audit trails for all medical data operations
- **PHI Protection**: Ensure no patient health information is exposed during pipeline operations
- **Clinical Impact**: Assess impact of pipeline failures on healthcare operations and patient care

This comprehensive framework ensures reliable, compliant, and efficient management of large-scale medical data pipelines while maintaining healthcare standards and operational excellence.
