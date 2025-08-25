#!/usr/bin/env python3
"""
Deduplication Monitor - Validates data integrity and detects pagination bugs
Monitors deduplication rates to catch potential duplicate data issues early
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

import asyncpg


class DeduplicationMonitor:
    """Monitor deduplication rates and data integrity across medical sources"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or "postgresql://intelluxe:secure_password@localhost/intelluxe_public"
        self.thresholds = {
            "critical_duplication_rate": 50.0,  # Alert if >50% duplication
            "warning_duplication_rate": 10.0,   # Warn if >10% duplication
            "min_expected_records": {
                "clinical_trials": 200000,    # Expect ~470k studies
                "pubmed_articles": 400000,    # Expect millions of articles  
                "drug_information": 50000,    # Expect thousands of drugs
                "billing_codes": 50000,       # Expect thousands of codes
                "icd10_codes": 70000,         # Expect ~70k codes
                "food_items": 5000,           # Expect thousands of foods
                "exercises": 10,              # Small dataset
                "health_topics": 1000,        # Expect hundreds of topics
            }
        }
        
    async def check_all_sources(self) -> Dict[str, Any]:
        """Check deduplication rates and data integrity for all sources"""
        logging.info("Starting comprehensive deduplication monitoring")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "overall_status": "healthy",
            "alerts": [],
            "warnings": [],
            "summary": {}
        }
        
        conn = await asyncpg.connect(self.db_url)
        try:
            # Check each medical data source
            for table in self.thresholds["min_expected_records"]:
                try:
                    source_result = await self._check_source(conn, table)
                    results["sources"][table] = source_result
                    
                    # Generate alerts and warnings
                    self._evaluate_source_health(table, source_result, results)
                    
                except Exception as e:
                    logging.error(f"Failed to check {table}: {e}")
                    results["sources"][table] = {"error": str(e)}
                    results["alerts"].append(f"Failed to analyze {table}: {e}")
            
            # Overall health assessment
            if results["alerts"]:
                results["overall_status"] = "critical"
            elif results["warnings"]:
                results["overall_status"] = "warning"
                
            # Create summary
            results["summary"] = self._create_summary(results["sources"])
            
        finally:
            await conn.close()
        
        return results
    
    async def _check_source(self, conn: asyncpg.Connection, table: str) -> Dict[str, Any]:
        """Check deduplication metrics for a specific source"""
        
        # Get basic counts
        total_count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        
        # Sample check for potential duplicates based on table structure
        duplicate_check = await self._check_duplicates_by_table(conn, table)
        
        # Calculate estimated deduplication rate
        unique_count = duplicate_check.get("unique_count", total_count)
        duplicate_count = total_count - unique_count if total_count > unique_count else 0
        deduplication_rate = (duplicate_count / total_count * 100) if total_count > 0 else 0
        
        # Check file vs record correlation (for downloaded sources)
        file_correlation = await self._check_file_correlation(conn, table)
        
        return {
            "total_records": total_count,
            "unique_records": unique_count,
            "duplicate_records": duplicate_count,
            "deduplication_rate": deduplication_rate,
            "file_correlation": file_correlation,
            "duplicate_analysis": duplicate_check,
            "status": self._assess_source_status(total_count, deduplication_rate, table)
        }
    
    async def _check_duplicates_by_table(self, conn: asyncpg.Connection, table: str) -> Dict[str, Any]:
        """Check for duplicates based on table-specific key fields"""
        
        duplicate_queries = {
            "clinical_trials": """
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT nct_id) as unique_nct,
                    COUNT(DISTINCT title) as unique_titles
                FROM clinical_trials
            """,
            "pubmed_articles": """
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT pmid) as unique_pmid,
                    COUNT(DISTINCT title) as unique_titles
                FROM pubmed_articles
            """,
            "drug_information": """
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT COALESCE(ndc, generic_name, brand_name)) as unique_drugs
                FROM drug_information
            """,
            "billing_codes": """
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT code) as unique_codes
                FROM billing_codes
            """,
            "icd10_codes": """
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT code) as unique_codes
                FROM icd10_codes
            """
        }
        
        if table not in duplicate_queries:
            # Generic fallback for other tables
            return {"method": "count_only", "unique_count": await conn.fetchval(f"SELECT COUNT(*) FROM {table}")}
        
        try:
            result = await conn.fetchrow(duplicate_queries[table])
            unique_field = [k for k in result.keys() if k.startswith('unique_')][0]
            
            return {
                "method": "key_field_analysis",
                "total_records": result['total'],
                "unique_count": result[unique_field],
                "duplicate_analysis": dict(result)
            }
        except Exception as e:
            logging.warning(f"Duplicate analysis failed for {table}: {e}")
            return {"method": "failed", "error": str(e), "unique_count": 0}
    
    async def _check_file_correlation(self, conn: asyncpg.Connection, table: str) -> Dict[str, Any]:
        """Check correlation between downloaded files and processed records"""
        try:
            # Check processed_files table for file processing info
            file_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as processed_files,
                    SUM(records_found) as total_records_in_files,
                    SUM(records_processed) as total_records_processed,
                    source_type
                FROM processed_files 
                WHERE source_type LIKE $1
                GROUP BY source_type
            """, f"%{table.split('_')[0]}%")
            
            if file_stats:
                processing_efficiency = (file_stats['total_records_processed'] / 
                                       file_stats['total_records_in_files'] * 100) if file_stats['total_records_in_files'] > 0 else 0
                
                return {
                    "files_processed": file_stats['processed_files'],
                    "records_in_files": file_stats['total_records_in_files'],
                    "records_processed": file_stats['total_records_processed'],
                    "processing_efficiency": processing_efficiency
                }
        except Exception as e:
            logging.debug(f"File correlation check failed for {table}: {e}")
        
        return {"status": "no_file_tracking"}
    
    def _assess_source_status(self, record_count: int, deduplication_rate: float, table: str) -> str:
        """Assess the health status of a data source"""
        min_expected = self.thresholds["min_expected_records"].get(table, 0)
        
        if record_count < min_expected * 0.1:  # Less than 10% of expected
            return "critical"
        elif deduplication_rate > self.thresholds["critical_duplication_rate"]:
            return "critical"
        elif deduplication_rate > self.thresholds["warning_duplication_rate"]:
            return "warning"
        elif record_count < min_expected * 0.5:  # Less than 50% of expected
            return "warning"
        else:
            return "healthy"
    
    def _evaluate_source_health(self, table: str, source_result: Dict[str, Any], results: Dict[str, Any]):
        """Evaluate source health and add alerts/warnings"""
        status = source_result.get("status", "unknown")
        dedup_rate = source_result.get("deduplication_rate", 0)
        record_count = source_result.get("total_records", 0)
        min_expected = self.thresholds["min_expected_records"].get(table, 0)
        
        if status == "critical":
            if dedup_rate > self.thresholds["critical_duplication_rate"]:
                results["alerts"].append(
                    f"🚨 CRITICAL: {table} has {dedup_rate:.1f}% duplication rate "
                    f"(threshold: {self.thresholds['critical_duplication_rate']}%) - possible pagination bug!"
                )
            if record_count < min_expected * 0.1:
                results["alerts"].append(
                    f"🚨 CRITICAL: {table} has only {record_count:,} records "
                    f"(expected: {min_expected:,}+) - download may have failed!"
                )
        
        elif status == "warning":
            if dedup_rate > self.thresholds["warning_duplication_rate"]:
                results["warnings"].append(
                    f"⚠️  WARNING: {table} has {dedup_rate:.1f}% duplication rate "
                    f"(threshold: {self.thresholds['warning_duplication_rate']}%)"
                )
            if record_count < min_expected * 0.5:
                results["warnings"].append(
                    f"⚠️  WARNING: {table} has {record_count:,} records "
                    f"(expected: {min_expected:,}+) - may be incomplete"
                )
    
    def _create_summary(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Create overall summary statistics"""
        total_records = sum(s.get("total_records", 0) for s in sources.values() if isinstance(s, dict))
        healthy_sources = sum(1 for s in sources.values() 
                            if isinstance(s, dict) and s.get("status") == "healthy")
        warning_sources = sum(1 for s in sources.values() 
                            if isinstance(s, dict) and s.get("status") == "warning")
        critical_sources = sum(1 for s in sources.values() 
                             if isinstance(s, dict) and s.get("status") == "critical")
        
        avg_deduplication = sum(s.get("deduplication_rate", 0) for s in sources.values() 
                              if isinstance(s, dict)) / max(len(sources), 1)
        
        return {
            "total_sources": len(sources),
            "healthy_sources": healthy_sources,
            "warning_sources": warning_sources,
            "critical_sources": critical_sources,
            "total_records": total_records,
            "average_deduplication_rate": avg_deduplication
        }


async def main():
    """Main monitoring entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Medical Data Deduplication Monitor")
    parser.add_argument("--db-url", default="postgresql://intelluxe:secure_password@localhost/intelluxe_public",
                       help="Database connection URL")
    parser.add_argument("--output", type=Path, help="Save report to JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--alerts-only", action="store_true", help="Only show alerts and warnings")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Run monitoring
    monitor = DeduplicationMonitor(args.db_url)
    results = await monitor.check_all_sources()
    
    # Output results
    if args.alerts_only:
        # Only show critical issues
        if results["alerts"]:
            print("🚨 CRITICAL ALERTS:")
            for alert in results["alerts"]:
                print(f"  {alert}")
        if results["warnings"]:
            print("\n⚠️  WARNINGS:")
            for warning in results["warnings"]:
                print(f"  {warning}")
        if not results["alerts"] and not results["warnings"]:
            print("✅ No alerts or warnings detected")
    else:
        # Full report
        print("\n" + "="*60)
        print("MEDICAL DATA DEDUPLICATION MONITORING REPORT")
        print("="*60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        
        # Summary
        summary = results["summary"]
        print(f"\n📊 Summary:")
        print(f"   Total Sources: {summary['total_sources']}")
        print(f"   Healthy: {summary['healthy_sources']} | Warning: {summary['warning_sources']} | Critical: {summary['critical_sources']}")
        print(f"   Total Records: {summary['total_records']:,}")
        print(f"   Average Deduplication Rate: {summary['average_deduplication_rate']:.2f}%")
        
        # Source details
        print(f"\n📋 Source Details:")
        for source, data in results["sources"].items():
            if isinstance(data, dict) and "total_records" in data:
                status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "🚨"}.get(data["status"], "❓")
                print(f"   {status_icon} {source}: {data['total_records']:,} records ({data['deduplication_rate']:.1f}% dedup)")
        
        # Alerts and warnings
        if results["alerts"]:
            print(f"\n🚨 CRITICAL ALERTS ({len(results['alerts'])}):")
            for alert in results["alerts"]:
                print(f"   {alert}")
        
        if results["warnings"]:
            print(f"\n⚠️  WARNINGS ({len(results['warnings'])}):")
            for warning in results["warnings"]:
                print(f"   {warning}")
        
        if not results["alerts"] and not results["warnings"]:
            print(f"\n✅ All sources appear healthy!")
    
    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Full report saved to: {args.output}")
    
    # Exit with appropriate code
    if results["alerts"]:
        sys.exit(2)  # Critical issues
    elif results["warnings"]:
        sys.exit(1)  # Warnings
    else:
        sys.exit(0)  # All good


if __name__ == "__main__":
    asyncio.run(main())