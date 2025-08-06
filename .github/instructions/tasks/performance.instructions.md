# Healthcare AI Performance Optimization Instructions

## Purpose

Specialized performance optimization guidance for healthcare AI systems emphasizing medical workflow efficiency, PHI-safe optimization techniques, and healthcare-specific performance metrics.

## Healthcare Performance Framework

### Medical Workflow Performance Optimization

```python
# ✅ CORRECT: Healthcare-specific performance optimization
from typing import Dict, List, Any, Optional, Protocol
from dataclasses import dataclass, field
import asyncio
import time
import cProfile
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

@dataclass
class HealthcarePerformanceMetrics:
    """Healthcare-specific performance metrics and targets."""

    soap_note_processing_time: float = 0.5  # Max 500ms per SOAP note
    patient_data_retrieval_time: float = 0.3  # Max 300ms per patient lookup
    concurrent_patient_limit: int = 100  # Support 100 concurrent patient sessions
    ehr_integration_timeout: float = 2.0  # Max 2s for EHR operations
    phi_encryption_overhead: float = 0.1  # Max 100ms encryption overhead
    audit_logging_latency: float = 0.05  # Max 50ms for audit logging

    def validate_performance_targets(self, actual_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Validate actual performance against healthcare targets."""

        validation_results = {
            "soap_processing": actual_metrics.get("soap_processing", 0) <= self.soap_note_processing_time,
            "patient_retrieval": actual_metrics.get("patient_retrieval", 0) <= self.patient_data_retrieval_time,
            "concurrent_capacity": actual_metrics.get("concurrent_sessions", 0) >= self.concurrent_patient_limit,
            "ehr_integration": actual_metrics.get("ehr_response", 0) <= self.ehr_integration_timeout,
            "phi_encryption": actual_metrics.get("encryption_time", 0) <= self.phi_encryption_overhead,
            "audit_logging": actual_metrics.get("audit_latency", 0) <= self.audit_logging_latency
        }

        overall_performance = all(validation_results.values())

        return {
            "meets_healthcare_standards": overall_performance,
            "metric_validation": validation_results,
            "performance_grade": self._calculate_performance_grade(validation_results),
            "optimization_recommendations": self._generate_optimization_recommendations(validation_results)
        }

    def _calculate_performance_grade(self, validation_results: Dict[str, bool]) -> str:
        """Calculate overall performance grade for healthcare requirements."""

        passed_metrics = sum(validation_results.values())
        total_metrics = len(validation_results)
        percentage = (passed_metrics / total_metrics) * 100

        if percentage >= 95:
            return "EXCELLENT"
        elif percentage >= 85:
            return "GOOD"
        elif percentage >= 75:
            return "ACCEPTABLE"
        else:
            return "NEEDS_IMPROVEMENT"

class HealthcarePerformanceOptimizer:
    """Performance optimization specifically for healthcare AI systems."""

    def __init__(self) -> None:
        self.metrics = HealthcarePerformanceMetrics()
        self.performance_cache = {}
        self.optimization_history = []

    async def optimize_soap_note_processing(
        self,
        soap_processor: Any,
        optimization_level: str = "balanced"
    ) -> Dict[str, Any]:
        """Optimize SOAP note processing for healthcare workflows."""

        optimization_strategies = {
            "conservative": self._conservative_soap_optimization,
            "balanced": self._balanced_soap_optimization,
            "aggressive": self._aggressive_soap_optimization
        }

        strategy = optimization_strategies.get(optimization_level, self._balanced_soap_optimization)

        # Baseline performance measurement
        baseline_metrics = await self._measure_soap_baseline(soap_processor)

        # Apply optimization strategy
        optimized_processor = await strategy(soap_processor)

        # Post-optimization measurement
        optimized_metrics = await self._measure_soap_baseline(optimized_processor)

        return {
            "baseline_performance": baseline_metrics,
            "optimized_performance": optimized_metrics,
            "improvement_percentage": self._calculate_improvement(baseline_metrics, optimized_metrics),
            "healthcare_compliance": self._validate_medical_safety_preserved(soap_processor, optimized_processor)
        }

    async def _balanced_soap_optimization(self, soap_processor: Any) -> Any:
        """Balanced SOAP note processing optimization for healthcare."""

        # Optimize text processing pipeline
        optimized_processor = await self._optimize_text_processing(soap_processor)

        # Add intelligent caching for common medical terms
        optimized_processor = await self._add_medical_terminology_cache(optimized_processor)

        # Optimize database operations
        optimized_processor = await self._optimize_database_operations(optimized_processor)

        # Add async processing for I/O operations
        optimized_processor = await self._add_async_io_optimization(optimized_processor)

        return optimized_processor

    async def _optimize_text_processing(self, processor: Any) -> Any:
        """Optimize text processing for medical documents."""

        # Pre-compile regex patterns for medical parsing
        medical_patterns = {
            "soap_sections": re.compile(r'(Subjective|Objective|Assessment|Plan):\s*(.+?)(?=\n(?:Subjective|Objective|Assessment|Plan):|$)', re.IGNORECASE | re.DOTALL),
            "medical_codes": re.compile(r'\b[A-Z]\d{2}(?:\.\d{1,4})?\b'),  # ICD-10 codes
            "cpt_codes": re.compile(r'\b\d{5}\b'),  # CPT codes
            "vital_signs": re.compile(r'(?:BP|Blood Pressure):\s*(\d{2,3}/\d{2,3})|(?:Temp|Temperature):\s*(\d{2,3}\.?\d?)')
        }

        # Add compiled patterns to processor
        processor.compiled_patterns = medical_patterns

        # Optimize string operations
        processor.text_optimization_enabled = True

        return processor

    async def _add_medical_terminology_cache(self, processor: Any) -> Any:
        """Add intelligent caching for medical terminology processing."""

        # Common medical term cache
        medical_term_cache = {
            "common_symptoms": ["headache", "nausea", "fever", "cough", "fatigue"],
            "vital_signs": ["blood_pressure", "temperature", "pulse", "respiration"],
            "body_systems": ["cardiovascular", "respiratory", "neurological", "gastrointestinal"],
            "common_diagnoses": ["hypertension", "diabetes", "migraine", "bronchitis"]
        }

        # Add LRU cache for processed medical terms
        from functools import lru_cache

        @lru_cache(maxsize=1000)
        def cached_medical_term_lookup(term: str) -> Dict[str, Any]:
            """Cached medical terminology lookup."""
            # Medical term processing logic
            return {"term": term, "category": "medical", "processed": True}

        processor.medical_term_cache = cached_medical_term_lookup

        return processor

    async def optimize_patient_data_operations(
        self,
        patient_service: Any,
        concurrent_limit: int = 100
    ) -> Dict[str, Any]:
        """Optimize patient data operations for healthcare performance."""

        # Implement connection pooling for database operations
        optimized_service = await self._add_connection_pooling(patient_service)

        # Add intelligent caching for frequently accessed patient data
        optimized_service = await self._add_patient_data_cache(optimized_service)

        # Optimize concurrent patient session handling
        optimized_service = await self._optimize_concurrent_sessions(optimized_service, concurrent_limit)

        # Add PHI-safe performance monitoring
        optimized_service = await self._add_phi_safe_monitoring(optimized_service)

        return {
            "service": optimized_service,
            "performance_improvements": {
                "connection_pooling": "Reduced database connection overhead",
                "patient_cache": "Faster retrieval of frequently accessed patient data",
                "concurrent_optimization": f"Support for {concurrent_limit} concurrent sessions",
                "phi_monitoring": "Privacy-preserving performance monitoring"
            }
        }

    async def _add_connection_pooling(self, service: Any) -> Any:
        """Add database connection pooling for healthcare operations."""

        # Configure connection pool for healthcare database
        pool_config = {
            "min_connections": 5,
            "max_connections": 50,
            "connection_timeout": 30,
            "idle_timeout": 300,
            "healthcare_optimized": True
        }

        # Add async connection pool
        service.connection_pool = await self._create_healthcare_connection_pool(pool_config)

        return service

    async def _add_patient_data_cache(self, service: Any) -> Any:
        """Add PHI-safe caching for patient data operations."""

        # Redis cache configuration for healthcare
        cache_config = {
            "redis_url": "redis://localhost:6379/1",  # Dedicated DB for patient cache
            "encryption_enabled": True,
            "ttl_seconds": 300,  # 5-minute TTL for patient data
            "phi_protection": True,
            "audit_logging": True
        }

        # Add encrypted cache layer
        service.patient_cache = await self._create_phi_safe_cache(cache_config)

        return service

    async def optimize_ehr_integration_performance(
        self,
        ehr_client: Any
    ) -> Dict[str, Any]:
        """Optimize EHR integration performance for healthcare workflows."""

        # Add intelligent request batching
        optimized_client = await self._add_ehr_request_batching(ehr_client)

        # Implement circuit breaker pattern for EHR resilience
        optimized_client = await self._add_ehr_circuit_breaker(optimized_client)

        # Add response caching for read-only EHR operations
        optimized_client = await self._add_ehr_response_cache(optimized_client)

        # Optimize timeout and retry strategies
        optimized_client = await self._optimize_ehr_timeouts(optimized_client)

        return {
            "client": optimized_client,
            "optimization_features": {
                "request_batching": "Batch multiple EHR requests for efficiency",
                "circuit_breaker": "Prevent cascade failures in EHR integration",
                "response_caching": "Cache read-only EHR data for performance",
                "timeout_optimization": "Optimized timeouts for healthcare workflows"
            }
        }

    async def _add_ehr_request_batching(self, ehr_client: Any) -> Any:
        """Add intelligent request batching for EHR operations."""

        class EHRRequestBatcher:
            def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
                self.batch_size = batch_size
                self.batch_timeout = batch_timeout
                self.pending_requests = []
                self.batch_timer = None

            async def add_request(self, request: Dict[str, Any]) -> Any:
                """Add request to batch with automatic flushing."""
                self.pending_requests.append(request)

                if len(self.pending_requests) >= self.batch_size:
                    return await self._flush_batch()

                if self.batch_timer is None:
                    self.batch_timer = asyncio.create_task(self._timer_flush())

                return await self._wait_for_batch_result(request)

            async def _flush_batch(self) -> List[Any]:
                """Flush current batch to EHR system."""
                if not self.pending_requests:
                    return []

                batch = self.pending_requests.copy()
                self.pending_requests.clear()

                if self.batch_timer:
                    self.batch_timer.cancel()
                    self.batch_timer = None

                # Send batch request to EHR
                return await ehr_client.batch_request(batch)

        ehr_client.request_batcher = EHRRequestBatcher()

        return ehr_client
```

### Healthcare-Specific Performance Monitoring

```python
# ✅ CORRECT: PHI-safe performance monitoring for healthcare
class HealthcarePerformanceMonitor:
    """PHI-safe performance monitoring for healthcare AI systems."""

    def __init__(self) -> None:
        self.metrics_collector = PHISafeMetricsCollector()
        self.performance_analyzer = HealthcarePerformanceAnalyzer()
        self.alert_manager = HealthcareAlertManager()

    async def monitor_healthcare_operations(
        self,
        operation_type: str,
        duration: float = 60.0
    ) -> Dict[str, Any]:
        """Monitor healthcare operations with PHI protection."""

        monitoring_session = {
            "session_id": self._generate_session_id(),
            "operation_type": operation_type,
            "start_time": time.time(),
            "duration": duration,
            "phi_safe": True
        }

        # Collect PHI-safe metrics
        metrics = await self._collect_phi_safe_metrics(monitoring_session)

        # Analyze performance patterns
        analysis = await self._analyze_healthcare_performance(metrics)

        # Generate alerts for healthcare-critical issues
        alerts = await self._check_healthcare_alerts(analysis)

        return {
            "monitoring_session": monitoring_session,
            "performance_metrics": metrics,
            "analysis": analysis,
            "alerts": alerts,
            "recommendations": self._generate_performance_recommendations(analysis)
        }

    async def _collect_phi_safe_metrics(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Collect performance metrics without exposing PHI."""

        phi_safe_metrics = {
            "patient_operations": {
                "total_count": 0,
                "average_response_time": 0.0,
                "success_rate": 0.0,
                "error_count": 0,
                # Use anonymized patient hashes instead of IDs
                "unique_patient_hashes": set()
            },
            "soap_note_operations": {
                "total_processed": 0,
                "average_processing_time": 0.0,
                "validation_failures": 0,
                "sections_processed": {"subjective": 0, "objective": 0, "assessment": 0, "plan": 0}
            },
            "ehr_integration": {
                "total_requests": 0,
                "average_response_time": 0.0,
                "timeout_count": 0,
                "circuit_breaker_trips": 0
            },
            "system_resources": {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "database_connections": 0,
                "cache_hit_rate": 0.0
            }
        }

        # Collect metrics over monitoring duration
        start_time = time.time()
        while time.time() - start_time < session["duration"]:
            current_metrics = await self._sample_current_metrics()
            self._aggregate_phi_safe_metrics(phi_safe_metrics, current_metrics)
            await asyncio.sleep(1.0)  # Sample every second

        return phi_safe_metrics

    def _aggregate_phi_safe_metrics(
        self,
        aggregated: Dict[str, Any],
        current: Dict[str, Any]
    ) -> None:
        """Aggregate metrics while preserving PHI safety."""

        # Aggregate patient operations (anonymized)
        patient_ops = aggregated["patient_operations"]
        if "patient_access" in current:
            patient_ops["total_count"] += 1
            patient_ops["average_response_time"] = self._update_moving_average(
                patient_ops["average_response_time"],
                current["patient_access"]["response_time"],
                patient_ops["total_count"]
            )

            # Add anonymized patient hash
            patient_hash = hashlib.sha256(
                current["patient_access"]["patient_id"].encode()
            ).hexdigest()[:8]
            patient_ops["unique_patient_hashes"].add(patient_hash)

        # Aggregate SOAP note operations
        soap_ops = aggregated["soap_note_operations"]
        if "soap_processing" in current:
            soap_ops["total_processed"] += 1
            soap_ops["average_processing_time"] = self._update_moving_average(
                soap_ops["average_processing_time"],
                current["soap_processing"]["processing_time"],
                soap_ops["total_processed"]
            )

    async def optimize_healthcare_database_performance(
        self,
        database_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize database performance for healthcare workloads."""

        optimization_strategies = {
            "indexing": await self._optimize_healthcare_indexes(database_config),
            "query_optimization": await self._optimize_healthcare_queries(database_config),
            "connection_pooling": await self._optimize_connection_pooling(database_config),
            "caching": await self._optimize_healthcare_caching(database_config),
            "partitioning": await self._optimize_table_partitioning(database_config)
        }

        return {
            "original_config": database_config,
            "optimizations": optimization_strategies,
            "expected_improvements": {
                "patient_lookup_time": "50% reduction",
                "soap_note_storage": "30% faster writes",
                "concurrent_capacity": "2x improvement",
                "cache_hit_rate": "85%+ for frequent operations"
            }
        }

    async def _optimize_healthcare_indexes(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize database indexes for healthcare queries."""

        healthcare_indexes = {
            "patients_table": [
                "CREATE INDEX idx_patient_id_hash ON patients USING HASH (patient_id)",
                "CREATE INDEX idx_patient_demographics ON patients (age, gender) WHERE active = true",
                "CREATE INDEX idx_patient_insurance ON patients (insurance_provider, insurance_id)",
                "CREATE INDEX idx_patient_created_date ON patients (created_at) WHERE created_at >= CURRENT_DATE - INTERVAL '1 year'"
            ],
            "encounters_table": [
                "CREATE INDEX idx_encounter_patient ON encounters (patient_id, encounter_date)",
                "CREATE INDEX idx_encounter_provider ON encounters (provider_id, encounter_date)",
                "CREATE INDEX idx_encounter_type ON encounters (encounter_type, status)",
                "CREATE INDEX idx_encounter_soap_search ON encounters USING GIN (to_tsvector('english', soap_note))"
            ],
            "lab_results_table": [
                "CREATE INDEX idx_lab_patient_date ON lab_results (patient_id, result_date)",
                "CREATE INDEX idx_lab_test_type ON lab_results (test_type, status)",
                "CREATE INDEX idx_lab_abnormal_results ON lab_results (test_type) WHERE abnormal_flag = true"
            ]
        }

        return {
            "recommended_indexes": healthcare_indexes,
            "performance_impact": "40-60% improvement in healthcare query performance",
            "maintenance_overhead": "Low - automated maintenance recommended"
        }
```

### Modern Performance Tools Integration

```python
# ✅ CORRECT: Modern performance tools for healthcare AI
class ModernHealthcarePerformanceTools:
    """Integration of modern performance tools for healthcare AI."""

    def setup_performance_monitoring_stack(self) -> Dict[str, Any]:
        """Set up modern performance monitoring for healthcare."""

        return {
            "profiling_tools": {
                "py_spy": "py-spy record -o profile.svg --duration 60 --pid <healthcare-process-pid>",
                "cProfile": "python -m cProfile -o healthcare_profile.prof main.py",
                "memory_profiler": "@profile decorator for memory-intensive healthcare operations",
                "line_profiler": "kernprof -l -v healthcare_module.py"
            },

            "async_profiling": {
                "aiomonitor": "Real-time async task monitoring for healthcare operations",
                "aiodebug": "Async debugging for healthcare I/O operations",
                "async_timeout": "Timeout monitoring for healthcare async operations"
            },

            "database_monitoring": {
                "postgresql_monitoring": "pg_stat_statements extension for query analysis",
                "redis_monitoring": "Redis INFO command automation for cache monitoring",
                "connection_pool_monitoring": "Track database connection usage patterns"
            },

            "system_monitoring": {
                "psutil": "System resource monitoring for healthcare workloads",
                "prometheus_client": "Custom healthcare metrics for Prometheus",
                "grafana_dashboards": "Healthcare-specific performance dashboards"
            }
        }

    def setup_load_testing_framework(self) -> Dict[str, str]:
        """Set up load testing for healthcare AI systems."""

        return {
            "locust_healthcare": """
from locust import HttpUser, task, between
import json
import hashlib
from datetime import datetime

class HealthcareLoadTest(HttpUser):
    wait_time = between(1, 3)  # Realistic healthcare user behavior

    def on_start(self):
        '''Set up synthetic healthcare data for load testing.'''
        self.synthetic_patients = [
            f"PAT{i:03d}" for i in range(1, 101)
        ]
        self.synthetic_providers = [
            f"PROV{i:03d}" for i in range(1, 11)
        ]

    @task(3)
    def process_soap_note(self):
        '''Test SOAP note processing under load.'''
        patient_id = self.synthetic_patients[hash(self.user.client.base_url) % len(self.synthetic_patients)]

        soap_data = {
            "patient_id": patient_id,
            "provider_id": self.synthetic_providers[0],
            "soap_note": {
                "subjective": "Patient reports symptoms consistent with test scenario",
                "objective": "Examination findings documented",
                "assessment": "Test assessment for load testing",
                "plan": "Follow-up as needed for test scenario"
            }
        }

        with self.client.post("/api/soap/process",
                            json=soap_data,
                            catch_response=True) as response:
            if response.status_code == 200:
                result = response.json()
                if result.get("medical_advice_provided", False):
                    response.failure("Medical advice detected - safety violation")
                else:
                    response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(2)
    def patient_data_retrieval(self):
        '''Test patient data retrieval performance.'''
        patient_id = self.synthetic_patients[hash(self.user.client.base_url) % len(self.synthetic_patients)]

        with self.client.get(f"/api/patients/{patient_id}",
                           catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                # Validate PHI protection
                if "ssn" in str(data) or "phone" in str(data):
                    response.failure("PHI exposure detected")
                else:
                    response.success()

    @task(1)
    def ehr_integration_test(self):
        '''Test EHR integration performance under load.'''
        with self.client.get("/api/ehr/status",
                           catch_response=True) as response:
            if response.elapsed.total_seconds() > 2.0:
                response.failure("EHR response too slow (>2s)")
            elif response.status_code == 200:
                response.success()
            """,

            "artillery_healthcare": """
# artillery-healthcare-load.yml
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 50
      name: "Healthcare peak load"
    - duration: 60
      arrivalRate: 5
      name: "Cool down"

scenarios:
  - name: "Healthcare AI Workflow"
    weight: 70
    flow:
      - post:
          url: "/api/soap/process"
          json:
            patient_id: "PAT{{ $randomInt(1, 100) | pad(3) }}"
            provider_id: "PROV001"
            soap_note:
              subjective: "Test patient symptoms"
              objective: "Test examination findings"
              assessment: "Test clinical assessment"
              plan: "Test treatment plan"
          capture:
            - json: "$.medical_advice_provided"
              as: "medical_advice_check"
          expect:
            - equals: ["{{ medical_advice_check }}", false]

  - name: "Patient Data Access"
    weight: 30
    flow:
      - get:
          url: "/api/patients/PAT{{ $randomInt(1, 100) | pad(3) }}"
          expect:
            - statusCode: 200
            - contentType: "application/json"
            """,

            "run_load_tests": """
#!/bin/bash
# Run comprehensive healthcare load testing

echo "🏥 Starting Healthcare AI Load Testing..."

# Start performance monitoring
python3 scripts/start-performance-monitoring.py &
MONITOR_PID=$!

# Run Locust load tests
echo "🔄 Running Locust healthcare load tests..."
locust -f tests/load/healthcare_load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=5m --html=reports/locust_report.html

# Run Artillery load tests
echo "⚡ Running Artillery healthcare load tests..."
artillery run tests/load/artillery-healthcare-load.yml --output=reports/artillery_report.json

# Generate performance report
echo "📊 Generating performance report..."
artillery report reports/artillery_report.json --output=reports/artillery_report.html

# Stop monitoring
kill $MONITOR_PID

echo "✅ Healthcare load testing completed!"
echo "📁 Reports: reports/"
            """
        }
```

### Performance Optimization Checklist

```python
# ✅ CORRECT: Healthcare performance optimization checklist
class HealthcarePerformanceChecklist:
    """Comprehensive performance optimization checklist for healthcare AI."""

    def validate_performance_optimization(self, system_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate performance optimization meets healthcare standards."""

        optimization_checklist = {
            "database_optimization": {
                "connection_pooling": self._check_connection_pooling(system_config),
                "query_optimization": self._check_query_optimization(system_config),
                "index_optimization": self._check_index_optimization(system_config),
                "phi_encryption_efficiency": self._check_phi_encryption_efficiency(system_config)
            },

            "application_optimization": {
                "async_operations": self._check_async_implementation(system_config),
                "caching_strategy": self._check_caching_strategy(system_config),
                "memory_management": self._check_memory_management(system_config),
                "error_handling_efficiency": self._check_error_handling(system_config)
            },

            "healthcare_specific": {
                "soap_processing_speed": self._check_soap_processing_speed(system_config),
                "patient_data_retrieval": self._check_patient_data_performance(system_config),
                "ehr_integration_performance": self._check_ehr_performance(system_config),
                "audit_logging_efficiency": self._check_audit_logging_performance(system_config)
            },

            "monitoring_and_alerting": {
                "performance_monitoring": self._check_performance_monitoring(system_config),
                "phi_safe_logging": self._check_phi_safe_logging(system_config),
                "healthcare_alerts": self._check_healthcare_alerts(system_config),
                "compliance_monitoring": self._check_compliance_monitoring(system_config)
            }
        }

        overall_score = self._calculate_optimization_score(optimization_checklist)

        return {
            "optimization_checklist": optimization_checklist,
            "overall_score": overall_score,
            "performance_grade": self._get_performance_grade(overall_score),
            "critical_improvements": self._identify_critical_improvements(optimization_checklist),
            "next_optimization_steps": self._recommend_next_steps(optimization_checklist)
        }
```

## Advanced Healthcare Performance Optimization

### Real-Time Clinical Response Patterns

```python
# ✅ ADVANCED: Healthcare-specific performance optimization for clinical workflows
class HealthcarePerformanceOptimization:
    """Performance patterns specific to healthcare AI workflows."""
    
    def optimize_clinical_response_time(self):
        """Ensure clinical AI responses meet healthcare workflow requirements."""
        
        # CRITICAL: Clinical decision support must respond within 3 seconds
        @timeout_clinical_operation(seconds=3)
        async def provide_clinical_assistance(self, query: str) -> ClinicalResponse:
            
            # Parallel processing for non-blocking clinical workflows
            cache_check = asyncio.create_task(self.check_clinical_cache(query))
            phi_scan = asyncio.create_task(self.scan_for_phi(query))
            emergency_check = asyncio.create_task(self.detect_emergency_scenario(query))
            
            # Emergency scenarios get immediate priority processing
            is_emergency = await emergency_check
            if is_emergency:
                return await self.handle_emergency_response(query, priority="immediate")
            
            # Non-blocking operations that can run in parallel
            cached_result, has_phi = await asyncio.gather(cache_check, phi_scan)
            
            if cached_result and not has_phi:
                # Fast path: cached, PHI-safe result
                return self.add_clinical_disclaimers(cached_result)
            
            # Full processing only when necessary
            return await self.full_clinical_processing(query)
    
    async def optimize_multi_agent_coordination(self, clinical_case: ClinicalCase):
        """Optimize performance for multi-agent clinical workflows."""
        
        # Intelligent agent routing to minimize resource contention
        optimal_agents = await self.select_optimal_agents(clinical_case)
        
        # Parallel execution with resource management
        with clinical_resource_pool(max_concurrent=5) as pool:
            agent_tasks = []
            
            for agent_name in optimal_agents:
                task = pool.submit(
                    self.execute_agent_analysis,
                    agent_name,
                    clinical_case,
                    timeout=2.0  # Healthcare workflow requirement
                )
                agent_tasks.append(task)
            
            # Gather results with timeout handling
            results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Performance monitoring for clinical workflows
            await self.log_clinical_performance_metrics({
                "agents_used": len(optimal_agents),
                "total_response_time": time.time() - clinical_case.start_time,
                "success_rate": len([r for r in results if not isinstance(r, Exception)]) / len(results),
                "clinical_workflow_id": clinical_case.workflow_id
            })
            
            return self.synthesize_agent_results(results, clinical_case)

    async def optimize_healthcare_database_operations(self):
        """Optimize database operations for healthcare AI performance."""
        
        # Healthcare-specific connection pooling
        db_pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=5,
            max_size=20,
            server_settings={
                'application_name': 'healthcare_ai_system',
                'log_statement': 'none'  # PHI protection in database logs
            }
        )
        
        # Optimized patient data retrieval with PHI protection
        async def get_patient_data_optimized(patient_id: str) -> PatientData:
            async with db_pool.acquire() as conn:
                # Use prepared statements for performance
                patient_query = await conn.prepare("""
                    SELECT encrypted_demographics, encrypted_medical_history 
                    FROM patients 
                    WHERE patient_hash = $1
                """)
                
                # Execute with performance monitoring
                start_time = time.time()
                result = await patient_query.fetchrow(patient_id)
                query_time = time.time() - start_time
                
                # Performance validation against healthcare targets
                if query_time > 0.3:  # 300ms target
                    logger.warning(f"Patient data retrieval exceeded target: {query_time:.3f}s")
                
                return PatientData(result) if result else None

class ClinicalWorkflowPerformanceMonitor:
    """Monitor performance specifically for clinical workflow requirements."""
    
    def __init__(self):
        self.clinical_performance_targets = {
            "emergency_response_time": 1.0,      # Emergency: <1 second
            "clinical_decision_support": 3.0,    # Decision support: <3 seconds  
            "soap_note_generation": 2.0,         # SOAP notes: <2 seconds
            "literature_search": 5.0,            # Literature: <5 seconds
            "multi_agent_coordination": 4.0,     # Multi-agent: <4 seconds
            "patient_data_retrieval": 0.3,       # Patient data: <300ms
            "phi_encryption_overhead": 0.1       # PHI encryption: <100ms
        }
    
    async def monitor_clinical_performance(self, operation: str, execution_time: float):
        """Monitor clinical operation performance against healthcare targets."""
        
        target_time = self.clinical_performance_targets.get(operation)
        if not target_time:
            logger.warning(f"No performance target defined for operation: {operation}")
            return
        
        performance_ratio = execution_time / target_time
        
        if performance_ratio > 1.0:
            # Performance target exceeded - clinical workflow impact
            logger.error(
                f"Clinical performance target exceeded: {operation}",
                extra={
                    "execution_time": execution_time,
                    "target_time": target_time,
                    "performance_ratio": performance_ratio,
                    "clinical_impact": "workflow_delay_possible"
                }
            )
        elif performance_ratio > 0.8:
            # Approaching performance limit - early warning
            logger.warning(
                f"Clinical performance approaching target: {operation}",
                extra={
                    "execution_time": execution_time,
                    "target_time": target_time,
                    "performance_ratio": performance_ratio,
                    "clinical_impact": "monitor_closely"
                }
            )
        
        # Store performance metrics for clinical workflow optimization
        await self.store_clinical_performance_metric({
            "operation": operation,
            "execution_time": execution_time,
            "target_time": target_time,
            "performance_ratio": performance_ratio,
            "timestamp": datetime.now().isoformat(),
            "meets_clinical_target": performance_ratio <= 1.0
        })
```

### Healthcare-Specific Caching Strategy

```python
# ✅ ADVANCED: PHI-safe caching for healthcare performance optimization
class HealthcareCacheManager:
    """PHI-safe caching strategies for healthcare AI performance."""
    
    def __init__(self):
        self.cache_layers = {
            "clinical_literature": self.setup_literature_cache(),
            "medical_terminology": self.setup_terminology_cache(),
            "drug_interactions": self.setup_drug_cache(),
            "clinical_guidelines": self.setup_guidelines_cache()
        }
    
    async def cache_clinical_literature(self, query: str, results: List[Dict[str, Any]]):
        """Cache clinical literature search results safely."""
        
        # Generate PHI-safe cache key
        cache_key = self.generate_safe_cache_key(query)
        
        # Sanitize results before caching
        sanitized_results = [
            self.sanitize_literature_result(result) 
            for result in results
        ]
        
        # Cache with healthcare-appropriate TTL
        await self.cache_layers["clinical_literature"].set(
            cache_key,
            sanitized_results,
            ttl=3600,  # 1 hour for clinical literature
            tags=["medical_literature", "clinical_research"]
        )
    
    def generate_safe_cache_key(self, query: str) -> str:
        """Generate PHI-safe cache keys for healthcare queries."""
        
        # Remove potential PHI from cache keys
        sanitized_query = self.remove_phi_from_query(query)
        
        # Use semantic hash for similar queries
        semantic_hash = self.generate_semantic_hash(sanitized_query)
        
        return f"clinical_query_{semantic_hash}"
```

## Healthcare Performance Best Practices

### Medical Workflow Optimization

- **Emergency Response**: Target <1s for emergency scenario detection
- **Clinical Decision Support**: <3s response time with comprehensive analysis
- **SOAP Note Processing**: Target <500ms per note with comprehensive validation
- **Patient Data Retrieval**: <300ms response time with PHI protection
- **Multi-Agent Coordination**: <4s for complex clinical workflows
- **Concurrent Sessions**: Support 100+ concurrent patient sessions
- **EHR Integration**: <2s timeout with circuit breaker patterns

### Advanced Performance Patterns

- **Parallel Clinical Processing**: Use asyncio for concurrent medical operations
- **Intelligent Agent Routing**: Route queries to optimal agents based on clinical context  
- **PHI-Safe Performance Monitoring**: Monitor performance without exposing patient data
- **Clinical Resource Pooling**: Manage computational resources for healthcare workflows
- **Emergency Priority Processing**: Immediate routing and processing for emergency scenarios

### PHI-Safe Performance Monitoring

- **Anonymized Metrics**: Use patient hashes for performance tracking
- **Audit-Safe Logging**: Performance logs must not expose PHI
- **Compliance Monitoring**: Monitor HIPAA compliance performance overhead
- **Medical Safety Validation**: Ensure optimization doesn't compromise medical safety

### Modern Tool Integration

- **Async Optimization**: Use asyncio for I/O-bound healthcare operations
- **Database Optimization**: Connection pooling and healthcare-specific indexes
- **Caching Strategy**: PHI-safe caching with encryption and TTL
- **Load Testing**: Healthcare-specific load patterns with synthetic data

### Performance Validation

- **Healthcare Benchmarks**: Meet clinical workflow performance requirements
- **Medical Safety Testing**: Ensure optimizations don't introduce medical risks
- **PHI Protection**: Validate performance improvements maintain PHI security
- **Compliance Overhead**: Account for HIPAA compliance in performance targets

Remember: Healthcare performance optimization must balance speed with medical safety, PHI protection, regulatory compliance, and clinical workflow requirements throughout the optimization process.
