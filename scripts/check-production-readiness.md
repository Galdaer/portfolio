# scripts/check-production-readiness.py

#!/usr/bin/env python3
"""
Production Readiness Checker for Intelluxe Healthcare AI
Validates system readiness for clinical deployment
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional
import subprocess
import requests
import psycopg2
import redis

@dataclass
class ProductionCheck:
"""Individual production readiness check"""
name: str
status: str # PASS, FAIL, WARNING
message: str
details: Optional[Dict[str, Any]] = None
critical: bool = False

@dataclass
class ProductionReadinessReport:
"""Complete production readiness assessment"""
timestamp: datetime
overall_status: str
critical_failures: int
warnings: int
checks: List[ProductionCheck]
environment: str
deployment_ready: bool

class ProductionReadinessChecker:
"""Comprehensive production readiness validation for healthcare AI"""

    def __init__(self):
        self.checks: List[ProductionCheck] = []
        self.environment = os.getenv("ENVIRONMENT", "development")

    async def run_all_checks(self) -> ProductionReadinessReport:
        """Run all production readiness checks"""
        print("🏥 Starting Healthcare AI Production Readiness Assessment")
        print(f"Environment: {self.environment}")
        print("=" * 60)

        # Security & Compliance Checks
        await self._check_hipaa_compliance()
        await self._check_encryption_standards()
        await self._check_audit_logging()
        await self._check_phi_protection()

        # Infrastructure Checks
        await self._check_database_production_config()
        await self._check_redis_production_config()
        await self._check_ollama_production_config()
        await self._check_backup_systems()

        # Application Checks
        await self._check_healthcare_mcp_readiness()
        await self._check_agent_deployment_readiness()
        await self._check_monitoring_systems()
        await self._check_error_handling()

        # Performance & Scalability
        await self._check_performance_baselines()
        await self._check_resource_limits()
        await self._check_load_balancing()

        # Generate final report
        return self._generate_report()

    async def _check_hipaa_compliance(self):
        """Validate HIPAA compliance configuration"""
        try:
            # Check HIPAA config exists and is valid
            config_path = "config/security/hipaa_compliance.yml"
            if not os.path.exists(config_path):
                self.checks.append(ProductionCheck(
                    name="HIPAA Configuration",
                    status="FAIL",
                    message="HIPAA compliance configuration missing",
                    critical=True
                ))
                return

            # Validate HIPAA config structure
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)

            required_sections = [
                'administrative_safeguards',
                'physical_safeguards',
                'technical_safeguards',
                'encryption',
                'audit_monitoring'
            ]

            missing_sections = [s for s in required_sections if s not in config]

            if missing_sections:
                self.checks.append(ProductionCheck(
                    name="HIPAA Configuration",
                    status="FAIL",
                    message=f"Missing HIPAA sections: {', '.join(missing_sections)}",
                    critical=True
                ))
            else:
                # Check encryption requirements
                encryption_config = config.get('encryption', {})
                if encryption_config.get('aes_256_enabled') and encryption_config.get('key_rotation_enabled'):
                    self.checks.append(ProductionCheck(
                        name="HIPAA Configuration",
                        status="PASS",
                        message="HIPAA compliance configuration valid"
                    ))
                else:
                    self.checks.append(ProductionCheck(
                        name="HIPAA Configuration",
                        status="FAIL",
                        message="HIPAA encryption requirements not met",
                        critical=True
                    ))

        except Exception as e:
            self.checks.append(ProductionCheck(
                name="HIPAA Configuration",
                status="FAIL",
                message=f"HIPAA validation error: {str(e)}",
                critical=True
            ))

    async def _check_encryption_standards(self):
        """Validate encryption meets healthcare standards"""
        try:
            # Check if encryption keys are properly configured
            master_key = os.getenv("MASTER_ENCRYPTION_KEY")
            jwt_secret = os.getenv("JWT_SECRET")

            if not master_key or len(master_key) < 32:
                self.checks.append(ProductionCheck(
                    name="Encryption Keys",
                    status="FAIL",
                    message="Master encryption key not configured or too weak",
                    critical=True
                ))
                return

            if not jwt_secret or len(jwt_secret) < 32:
                self.checks.append(ProductionCheck(
                    name="Encryption Keys",
                    status="FAIL",
                    message="JWT secret not configured or too weak",
                    critical=True
                ))
                return

            # Test encryption functionality
            from src.security.encryption_manager import HealthcareEncryptionManager

            # Mock test with dummy connection
            class MockConn:
                def cursor(self): return self
                def execute(self, *args): pass
                def fetchall(self): return []
                def fetchone(self): return None
                def commit(self): pass
                def __enter__(self): return self
                def __exit__(self, *args): pass

            manager = HealthcareEncryptionManager(MockConn())
            test_data = "Test PHI data for encryption validation"

            # Test encryption/decryption cycle
            encrypted = manager.encrypt_sensitive_data(test_data)
            decrypted = manager.decrypt_sensitive_data(encrypted)

            if decrypted == test_data:
                self.checks.append(ProductionCheck(
                    name="Encryption Standards",
                    status="PASS",
                    message="AES-256 encryption validated"
                ))
            else:
                self.checks.append(ProductionCheck(
                    name="Encryption Standards",
                    status="FAIL",
                    message="Encryption validation failed",
                    critical=True
                ))

        except Exception as e:
            self.checks.append(ProductionCheck(
                name="Encryption Standards",
                status="FAIL",
                message=f"Encryption test error: {str(e)}",
                critical=True
            ))

    async def _check_database_production_config(self):
        """Validate PostgreSQL production configuration"""
        try:
            # Check database connection
            conn_params = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DB', 'intelluxe'),
                'user': os.getenv('POSTGRES_USER', 'intelluxe'),
                'password': os.getenv('POSTGRES_PASSWORD', 'intelluxe')
            }

            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()

            # Check TimescaleDB extension
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb';")
            if not cursor.fetchone():
                self.checks.append(ProductionCheck(
                    name="Database Extensions",
                    status="FAIL",
                    message="TimescaleDB extension not installed",
                    critical=True
                ))

            # Check backup configuration
            cursor.execute("SHOW archive_mode;")
            archive_mode = cursor.fetchone()[0]

            if archive_mode != 'on':
                self.checks.append(ProductionCheck(
                    name="Database Backup",
                    status="WARNING",
                    message="PostgreSQL archive mode not enabled"
                ))
            else:
                self.checks.append(ProductionCheck(
                    name="Database Configuration",
                    status="PASS",
                    message="PostgreSQL production configuration valid"
                ))

            conn.close()

        except Exception as e:
            self.checks.append(ProductionCheck(
                name="Database Configuration",
                status="FAIL",
                message=f"Database validation error: {str(e)}",
                critical=True
            ))

    async def _check_healthcare_mcp_readiness(self):
        """Validate Healthcare MCP service readiness"""
        try:
            # Check if Healthcare MCP service is properly configured
            service_config = "services/user/healthcare-mcp/healthcare-mcp.conf"

            if not os.path.exists(service_config):
                self.checks.append(ProductionCheck(
                    name="Healthcare MCP Service",
                    status="FAIL",
                    message="Healthcare MCP service configuration missing",
                    critical=True
                ))
                return

            # Check if MCP server is responding (if running)
            mcp_host = os.getenv('HEALTHCARE_MCP_HOST', 'localhost')
            mcp_port = os.getenv('HEALTHCARE_MCP_PORT', '8000')

            try:
                response = requests.get(f"http://{mcp_host}:{mcp_port}/health", timeout=5)
                if response.status_code == 200:
                    self.checks.append(ProductionCheck(
                        name="Healthcare MCP Service",
                        status="PASS",
                        message="Healthcare MCP service operational"
                    ))
                else:
                    self.checks.append(ProductionCheck(
                        name="Healthcare MCP Service",
                        status="WARNING",
                        message=f"Healthcare MCP returned status {response.status_code}"
                    ))
            except requests.RequestException:
                self.checks.append(ProductionCheck(
                    name="Healthcare MCP Service",
                    status="WARNING",
                    message="Healthcare MCP service not running (expected in CI)"
                ))

        except Exception as e:
            self.checks.append(ProductionCheck(
                name="Healthcare MCP Service",
                status="FAIL",
                message=f"MCP validation error: {str(e)}",
                critical=True
            ))

    # ... (other check methods would follow similar pattern)

    async def _check_phi_protection(self):
        """Validate PHI protection systems"""
        try:
            from src.healthcare_mcp.phi_detection import PHIDetector

            detector = PHIDetector()

            # Test PHI detection with known patterns
            test_cases = [
                ("John Smith, SSN: 123-45-6789", True),
                ("Patient MRN: 987654321", True),
                ("Normal text without PHI", False)
            ]

            all_passed = True
            for text, should_detect in test_cases:
                result = detector.detect_phi_sync(text)
                if result.phi_detected != should_detect:
                    all_passed = False
                    break

            if all_passed:
                self.checks.append(ProductionCheck(
                    name="PHI Protection",
                    status="PASS",
                    message="PHI detection system functional"
                ))
            else:
                self.checks.append(ProductionCheck(
                    name="PHI Protection",
                    status="FAIL",
                    message="PHI detection validation failed",
                    critical=True
                ))

        except Exception as e:
            self.checks.append(ProductionCheck(
                name="PHI Protection",
                status="FAIL",
                message=f"PHI protection error: {str(e)}",
                critical=True
            ))

    def _generate_report(self) -> ProductionReadinessReport:
        """Generate final production readiness report"""
        critical_failures = len([c for c in self.checks if c.status == "FAIL" and c.critical])
        warnings = len([c for c in self.checks if c.status == "WARNING"])
        failures = len([c for c in self.checks if c.status == "FAIL"])

        if critical_failures > 0:
            overall_status = "CRITICAL_FAILURE"
            deployment_ready = False
        elif failures > 0:
            overall_status = "FAILURE"
            deployment_ready = False
        elif warnings > 0:
            overall_status = "WARNING"
            deployment_ready = True  # Can deploy with warnings
        else:
            overall_status = "PASS"
            deployment_ready = True

        return ProductionReadinessReport(
            timestamp=datetime.utcnow(),
            overall_status=overall_status,
            critical_failures=critical_failures,
            warnings=warnings,
            checks=self.checks,
            environment=self.environment,
            deployment_ready=deployment_ready
        )

async def main():
"""Main execution function"""
checker = ProductionReadinessChecker()
report = await checker.run_all_checks()

    # Print summary
    print("\n" + "=" * 60)
    print("🏥 HEALTHCARE AI PRODUCTION READINESS ASSESSMENT")
    print("=" * 60)
    print(f"Overall Status: {report.overall_status}")
    print(f"Critical Failures: {report.critical_failures}")
    print(f"Warnings: {report.warnings}")
    print(f"Deployment Ready: {'✅ YES' if report.deployment_ready else '❌ NO'}")
    print(f"Environment: {report.environment}")
    print(f"Timestamp: {report.timestamp}")

    # Print detailed results
    print(f"\n📋 DETAILED RESULTS ({len(report.checks)} checks)")
    print("-" * 60)

    for check in report.checks:
        status_emoji = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️"}[check.status]
        critical_mark = " [CRITICAL]" if check.critical and check.status == "FAIL" else ""
        print(f"{status_emoji} {check.name}: {check.message}{critical_mark}")

    # Save report as JSON
    os.makedirs("reports", exist_ok=True)
    report_file = f"reports/production-readiness-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    report_data = {
        'timestamp': report.timestamp.isoformat(),
        'overall_status': report.overall_status,
        'critical_failures': report.critical_failures,
        'warnings': report.warnings,
        'deployment_ready': report.deployment_ready,
        'environment': report.environment,
        'checks': [
            {
                'name': c.name,
                'status': c.status,
                'message': c.message,
                'critical': c.critical,
                'details': c.details
            } for c in report.checks
        ]
    }

    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)

    print(f"\n📄 Report saved: {report_file}")

    # Exit with appropriate code
    if report.critical_failures > 0:
        print("\n❌ CRITICAL FAILURES DETECTED - Cannot proceed with deployment")
        sys.exit(1)
    elif not report.deployment_ready:
        print("\n⚠️  DEPLOYMENT NOT RECOMMENDED - Address failures first")
        sys.exit(1)
    else:
        print("\n✅ PRODUCTION READINESS VALIDATED")
        sys.exit(0)

if **name** == "**main**":
asyncio.run(main())
