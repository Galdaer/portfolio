#!/usr/bin/env python3
"""
Comprehensive ICD-10 Enhancement Script
Fixes all coverage issues in ICD-10 database:
- Populates inclusion/exclusion notes (0% → 80%+)
- Generates synonyms (0.02% → 90%+) 
- Builds hierarchical relationships (2.28% → 95%+)
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, '/home/intelluxe/services/user/medical-mirrors/src')

from icd10.icd10_enrichment import ICD10DatabaseEnhancer
from database import get_db_session
from sqlalchemy import text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/icd10_enhancement.log')
    ]
)
logger = logging.getLogger(__name__)


def get_current_coverage_stats():
    """Get current coverage statistics for all fields"""
    logger.info("Analyzing current ICD-10 field coverage...")
    
    with get_db_session() as session:
        result = session.execute(text("""
            SELECT 
                COUNT(*) as total_codes,
                COUNT(CASE WHEN synonyms IS NOT NULL AND synonyms != '[]'::jsonb THEN 1 END) as with_synonyms,
                COUNT(CASE WHEN inclusion_notes IS NOT NULL AND inclusion_notes != '[]'::jsonb THEN 1 END) as with_inclusion_notes,
                COUNT(CASE WHEN exclusion_notes IS NOT NULL AND exclusion_notes != '[]'::jsonb THEN 1 END) as with_exclusion_notes,
                COUNT(CASE WHEN children_codes IS NOT NULL AND children_codes != '[]'::jsonb THEN 1 END) as with_children_codes,
                COUNT(CASE WHEN parent_code IS NOT NULL AND LENGTH(parent_code) > 0 THEN 1 END) as with_parent_code,
                COUNT(CASE WHEN category IS NOT NULL AND LENGTH(category) > 0 THEN 1 END) as with_category,
                COUNT(CASE WHEN search_vector IS NOT NULL THEN 1 END) as with_search_vector
            FROM icd10_codes
        """)).fetchone()
    
    stats = {
        'total_codes': result.total_codes,
        'synonyms': {'count': result.with_synonyms, 'pct': result.with_synonyms/result.total_codes*100},
        'inclusion_notes': {'count': result.with_inclusion_notes, 'pct': result.with_inclusion_notes/result.total_codes*100},
        'exclusion_notes': {'count': result.with_exclusion_notes, 'pct': result.with_exclusion_notes/result.total_codes*100},
        'children_codes': {'count': result.with_children_codes, 'pct': result.with_children_codes/result.total_codes*100},
        'parent_code': {'count': result.with_parent_code, 'pct': result.with_parent_code/result.total_codes*100},
        'category': {'count': result.with_category, 'pct': result.with_category/result.total_codes*100},
        'search_vector': {'count': result.with_search_vector, 'pct': result.with_search_vector/result.total_codes*100}
    }
    
    return stats


def print_coverage_report(stats, title="Current Coverage"):
    """Print formatted coverage report"""
    print(f"\n🔍 {title} (Total: {stats['total_codes']:,} codes)")
    print("=" * 60)
    
    for field, data in stats.items():
        if field != 'total_codes':
            status = "✅" if data['pct'] > 80 else "⚠️" if data['pct'] > 20 else "❌"
            print(f"{status} {field.replace('_', ' ').title():20} {data['count']:>6,} codes ({data['pct']:5.1f}%)")


def compare_coverage(before, after):
    """Compare before and after coverage statistics"""
    print(f"\n🚀 Enhancement Results Summary")
    print("=" * 80)
    print(f"{'Field':<20} {'Before':<12} {'After':<12} {'Improvement':<15} {'Status'}")
    print("-" * 80)
    
    for field in ['synonyms', 'inclusion_notes', 'exclusion_notes', 'children_codes']:
        before_pct = before[field]['pct']
        after_pct = after[field]['pct']
        improvement = after_pct - before_pct
        
        if improvement > 50:
            status = "🎉 EXCELLENT"
        elif improvement > 20:
            status = "✅ GOOD"
        elif improvement > 5:
            status = "⚠️ IMPROVED"
        else:
            status = "❌ MINIMAL"
            
        print(f"{field.replace('_', ' ').title():<20} {before_pct:>6.1f}% {after_pct:>8.1f}% {improvement:>10.1f}pp {status}")


def main():
    """Main enhancement execution"""
    print("🏥 ICD-10 Comprehensive Enhancement Script")
    print("=" * 50)
    print("Fixing critical coverage issues in ICD-10 database:")
    print("- Populating inclusion/exclusion notes (0% → 80%+)")
    print("- Generating medical synonyms (0.02% → 90%+)")
    print("- Building hierarchical relationships (2.28% → 95%+)")
    print("- Enhancing search capabilities")
    
    # Get baseline coverage
    print("\n📊 Analyzing current database state...")
    before_stats = get_current_coverage_stats()
    print_coverage_report(before_stats, "BEFORE Enhancement")
    
    # Confirm critical issues
    critical_issues = []
    if before_stats['inclusion_notes']['pct'] < 10:
        critical_issues.append(f"Inclusion notes: {before_stats['inclusion_notes']['pct']:.1f}%")
    if before_stats['exclusion_notes']['pct'] < 10:
        critical_issues.append(f"Exclusion notes: {before_stats['exclusion_notes']['pct']:.1f}%")
    if before_stats['synonyms']['pct'] < 10:
        critical_issues.append(f"Synonyms: {before_stats['synonyms']['pct']:.1f}%")
    if before_stats['children_codes']['pct'] < 50:
        critical_issues.append(f"Children codes: {before_stats['children_codes']['pct']:.1f}%")
    
    if critical_issues:
        print(f"\n⚠️ Critical coverage issues detected:")
        for issue in critical_issues:
            print(f"   ❌ {issue}")
        print("\n🚀 Proceeding with automatic enhancement...")
    
    # Initialize enhancer
    print("\n🔧 Initializing ICD-10 Database Enhancer...")
    enhancer = ICD10DatabaseEnhancer()
    
    # Run comprehensive enhancement
    try:
        print("\n🚀 Starting comprehensive enhancement process...")
        print("This may take several minutes for 46,499+ codes...")
        
        enhancement_stats = enhancer.enhance_icd10_database()
        
        print(f"\n✅ Enhancement process completed!")
        print(f"   📊 Records processed: {enhancement_stats.get('processed', 0):,}")
        print(f"   🔧 Records enhanced: {enhancement_stats.get('enhanced', 0):,}")
        print(f"   📝 Synonyms added: {enhancement_stats.get('synonyms_added', 0):,}")
        print(f"   📋 Clinical notes added: {enhancement_stats.get('notes_added', 0):,}")
        print(f"   🔗 Hierarchy relationships updated: {enhancement_stats.get('hierarchy_updated', 0):,}")
        
    except Exception as e:
        logger.exception(f"Enhancement process failed: {e}")
        print(f"\n❌ Enhancement failed: {e}")
        print("Check /tmp/icd10_enhancement.log for detailed error information")
        return
    
    # Get updated coverage
    print("\n📊 Analyzing enhanced database state...")
    after_stats = get_current_coverage_stats()
    print_coverage_report(after_stats, "AFTER Enhancement")
    
    # Compare results
    compare_coverage(before_stats, after_stats)
    
    # Final summary
    total_improvements = 0
    major_improvements = 0
    
    for field in ['synonyms', 'inclusion_notes', 'exclusion_notes', 'children_codes']:
        improvement = after_stats[field]['pct'] - before_stats[field]['pct']
        if improvement > 0:
            total_improvements += 1
        if improvement > 20:
            major_improvements += 1
    
    print(f"\n🎯 Final Results:")
    if major_improvements >= 3:
        print("🎉 PHENOMENAL SUCCESS! Major improvements across critical fields")
    elif major_improvements >= 2:
        print("✅ EXCELLENT SUCCESS! Significant improvements achieved")
    elif total_improvements >= 3:
        print("⚠️ GOOD SUCCESS! Multiple fields improved")
    else:
        print("❌ LIMITED SUCCESS! Further enhancement may be needed")
    
    # Save results
    results = {
        'timestamp': '2025-08-29T10:00:00Z',
        'before': before_stats,
        'after': after_stats,
        'enhancement_stats': enhancement_stats
    }
    
    results_file = '/tmp/icd10_enhancement_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📁 Detailed results saved to: {results_file}")
    print(f"📁 Process log available at: /tmp/icd10_enhancement.log")
    
    # Usage recommendations
    print(f"\n💡 Next Steps:")
    print("1. Test ICD-10 search functionality with enhanced synonyms")
    print("2. Validate clinical notes in healthcare applications")
    print("3. Use hierarchical relationships for code browsing")
    print("4. Monitor search vector performance improvements")


if __name__ == "__main__":
    # Ensure we're in the right directory
    os.chdir('/home/intelluxe/services/user/medical-mirrors')
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Enhancement interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)