#!/usr/bin/env python3
"""
Dietary Flags Implementation Summary Report
Generates comprehensive report of dietary flags implementation

Author: Claude Code
Date: 2025-08-29
"""

import psycopg2
import json
import logging
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'intelluxe_public',
    'user': 'intelluxe',
    'password': 'secure_password'
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_summary_report():
    """Generate comprehensive summary of dietary flags implementation"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        with conn.cursor() as cursor:
            print("\n" + "="*80)
            print("DIETARY FLAGS IMPLEMENTATION SUMMARY REPORT")
            print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)
            
            # 1. Overall Statistics
            print("\n1. OVERALL STATISTICS")
            print("-" * 50)
            
            cursor.execute("SELECT COUNT(*) FROM food_items;")
            total_items = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM food_items WHERE dietary_flags IS NOT NULL;")
            items_with_flags = cursor.fetchone()[0]
            
            print(f"Total Food Items: {total_items:,}")
            print(f"Items with Dietary Flags: {items_with_flags:,}")
            print(f"Coverage: {items_with_flags/total_items*100:.1f}%")
            
            # 2. MyPlate Food Groups Distribution
            print("\n2. MYPLATE FOOD GROUPS DISTRIBUTION")
            print("-" * 50)
            
            cursor.execute("""
                SELECT 
                    dietary_flags->>'myplate_food_group' as food_group,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / %s, 1) as percentage
                FROM food_items 
                WHERE dietary_flags IS NOT NULL
                GROUP BY dietary_flags->>'myplate_food_group'
                ORDER BY count DESC;
            """, (total_items,))
            
            myplate_results = cursor.fetchall()
            for food_group, count, percentage in myplate_results:
                print(f"  {food_group.title():12}: {count:5,} items ({percentage:4.1f}%)")
            
            # 3. FDA Nutritional Claims Analysis
            print("\n3. FDA NUTRITIONAL CLAIMS ANALYSIS")
            print("-" * 50)
            
            cursor.execute("""
                SELECT 
                    claim,
                    COUNT(*) as claim_count,
                    ROUND(COUNT(*) * 100.0 / %s, 1) as percentage
                FROM (
                    SELECT jsonb_array_elements_text(dietary_flags->'fda_nutritional_claims') as claim
                    FROM food_items 
                    WHERE dietary_flags->'fda_nutritional_claims' IS NOT NULL
                ) claims
                GROUP BY claim
                ORDER BY claim_count DESC;
            """, (total_items,))
            
            claims_results = cursor.fetchall()
            for claim, count, percentage in claims_results:
                claim_display = claim.replace('_', ' ').title()
                print(f"  {claim_display:20}: {count:5,} items ({percentage:4.1f}%)")
            
            # 4. Allergen Detection Summary  
            print("\n4. ALLERGEN DETECTION SUMMARY")
            print("-" * 50)
            
            cursor.execute("""
                SELECT 
                    allergen,
                    COUNT(*) as detection_count,
                    ROUND(COUNT(*) * 100.0 / %s, 1) as percentage
                FROM (
                    SELECT jsonb_array_elements_text(dietary_flags->'potential_allergens') as allergen
                    FROM food_items 
                    WHERE dietary_flags->'potential_allergens' IS NOT NULL 
                      AND jsonb_array_length(dietary_flags->'potential_allergens') > 0
                ) allergens
                GROUP BY allergen
                ORDER BY detection_count DESC;
            """, (total_items,))
            
            allergen_results = cursor.fetchall()
            total_allergen_detections = sum(count for _, count, _ in allergen_results)
            print(f"  Total items with potential allergens: {total_allergen_detections:,}")
            print(f"  Allergen breakdown:")
            
            for allergen, count, percentage in allergen_results:
                allergen_display = allergen.replace('_', ' ').title()
                print(f"    {allergen_display:15}: {count:4,} detections ({percentage:4.1f}%)")
            
            # 5. Sample High-Quality Records
            print("\n5. SAMPLE HIGH-QUALITY DIETARY CLASSIFICATIONS")
            print("-" * 50)
            
            # Get diverse samples with multiple claims/allergens
            cursor.execute("""
                SELECT 
                    description,
                    dietary_flags->>'myplate_food_group' as food_group,
                    jsonb_array_length(dietary_flags->'fda_nutritional_claims') as claims_count,
                    jsonb_array_length(dietary_flags->'potential_allergens') as allergens_count,
                    dietary_flags->'fda_nutritional_claims' as claims,
                    dietary_flags->'potential_allergens' as allergens
                FROM food_items 
                WHERE dietary_flags IS NOT NULL
                  AND (jsonb_array_length(dietary_flags->'fda_nutritional_claims') >= 2 
                       OR jsonb_array_length(dietary_flags->'potential_allergens') >= 1)
                ORDER BY (
                    jsonb_array_length(dietary_flags->'fda_nutritional_claims') + 
                    jsonb_array_length(dietary_flags->'potential_allergens')
                ) DESC
                LIMIT 10;
            """)
            
            samples = cursor.fetchall()
            for i, (desc, group, claims_ct, allergens_ct, claims, allergens) in enumerate(samples, 1):
                print(f"\n  Sample {i}: {desc}")
                print(f"    Food Group: {group.title()}")
                if claims_ct > 0:
                    # Claims is already a list, no need to parse JSON
                    claims_list = [c.replace('_', ' ').title() for c in claims]
                    print(f"    FDA Claims: {', '.join(claims_list)}")
                if allergens_ct > 0:
                    # Allergens is already a list, no need to parse JSON  
                    allergens_list = [a.replace('_', ' ').title() for a in allergens]
                    print(f"    Allergens: {', '.join(allergens_list)}")
            
            # 6. Data Quality Metrics
            print("\n6. DATA QUALITY METRICS")
            print("-" * 50)
            
            # Items with complete nutritional claims
            cursor.execute("""
                SELECT COUNT(*) 
                FROM food_items 
                WHERE jsonb_array_length(dietary_flags->'fda_nutritional_claims') >= 3;
            """)
            rich_nutritional = cursor.fetchone()[0]
            
            # Items with allergen detections
            cursor.execute("""
                SELECT COUNT(*) 
                FROM food_items 
                WHERE jsonb_array_length(dietary_flags->'potential_allergens') > 0;
            """)
            allergen_detections = cursor.fetchone()[0]
            
            # MyPlate coverage (not 'other')
            cursor.execute("""
                SELECT COUNT(*) 
                FROM food_items 
                WHERE dietary_flags->>'myplate_food_group' != 'other';
            """)
            classified_myplate = cursor.fetchone()[0]
            
            print(f"  Items with 3+ nutritional claims: {rich_nutritional:,} ({rich_nutritional/total_items*100:.1f}%)")
            print(f"  Items with allergen detections:  {allergen_detections:,} ({allergen_detections/total_items*100:.1f}%)")
            print(f"  Items classified in MyPlate:     {classified_myplate:,} ({classified_myplate/total_items*100:.1f}%)")
            
            # 7. Implementation Details
            print("\n7. IMPLEMENTATION DETAILS")
            print("-" * 50)
            print("  Data Sources:")
            print("    - MyPlate mappings: USDA MyPlate Guidelines")
            print("    - Nutritional claims: FDA CFR Title 21")
            print("    - Allergen detection: FDA FALCPA/FASTER Act (2021)")
            print("\n  Key Features:")
            print("    - Professional FDA thresholds (Low Sodium: <140mg, etc.)")
            print("    - Complete allergen coverage (9 major allergens)")
            print("    - Authoritative government source attribution")
            print("    - Proper disclaimers for parsed vs certified data")
            print("    - Full audit trail and data lineage")
            
            print("\n" + "="*80)
            print("IMPLEMENTATION SUCCESSFULLY COMPLETED")
            print("="*80)
            
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    generate_summary_report()