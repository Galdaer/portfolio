#!/usr/bin/env python3
"""
Dietary Flags Implementation Script
Updates food_items table with professional dietary classifications
Based on FDA/USDA authoritative sources

Author: Claude Code  
Date: 2025-08-29
"""

import psycopg2
import json
import logging
from datetime import datetime
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'intelluxe_public',
    'user': 'intelluxe',
    'password': 'secure_password'
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/intelluxe/logs/dietary_flags_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_database_connection():
    """Create PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def load_sql_functions(conn):
    """Load all SQL functions from the implementation file"""
    sql_file_path = Path('/home/intelluxe/scripts/dietary_flags_implementation.sql')
    
    if not sql_file_path.exists():
        raise FileNotFoundError(f"SQL implementation file not found: {sql_file_path}")
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
    
    try:
        with conn.cursor() as cursor:
            logger.info("Loading SQL functions and procedures...")
            cursor.execute(sql_content)
            conn.commit()
            logger.info("SQL functions loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load SQL functions: {e}")
        conn.rollback()
        raise

def test_functions(conn):
    """Test individual functions before full implementation"""
    test_queries = [
        {
            'name': 'MyPlate Mapping Test',
            'query': """
                SELECT 
                    food_category, 
                    map_to_myplate_group(food_category) as myplate_group,
                    COUNT(*) as count
                FROM food_items 
                WHERE food_category IS NOT NULL 
                GROUP BY food_category, map_to_myplate_group(food_category)
                ORDER BY count DESC
                LIMIT 10;
            """
        },
        {
            'name': 'FDA Nutritional Claims Test',
            'query': """
                SELECT 
                    description,
                    calculate_fda_nutritional_flags(nutrients, serving_size) as nutritional_flags
                FROM food_items 
                WHERE nutrients IS NOT NULL 
                LIMIT 5;
            """
        },
        {
            'name': 'Allergen Detection Test', 
            'query': """
                SELECT 
                    description,
                    detect_fda_allergens(ingredients, description) as allergens
                FROM food_items 
                LIMIT 10;
            """
        }
    ]
    
    try:
        with conn.cursor() as cursor:
            for test in test_queries:
                logger.info(f"Running test: {test['name']}")
                cursor.execute(test['query'])
                results = cursor.fetchall()
                logger.info(f"Test completed successfully. Sample results: {len(results)} rows")
                
                # Log first few results for validation
                for i, row in enumerate(results[:3]):
                    logger.info(f"  Sample {i+1}: {row}")
                    
    except Exception as e:
        logger.error(f"Function testing failed: {e}")
        raise

def update_dietary_flags(conn):
    """Execute the main dietary flags update"""
    try:
        with conn.cursor() as cursor:
            logger.info("Starting dietary flags update for all food items...")
            
            # Execute the comprehensive update
            cursor.execute("SELECT * FROM update_all_dietary_flags();")
            results = cursor.fetchone()
            
            if results:
                updated_count, vegetables, fruits, grains, protein, dairy, other, \
                low_sodium, low_fat, high_fiber, high_protein, allergens = results
                
                logger.info("=== DIETARY FLAGS UPDATE COMPLETE ===")
                logger.info(f"Total items updated: {updated_count}")
                logger.info(f"MyPlate Food Groups:")
                logger.info(f"  - Vegetables: {vegetables}")
                logger.info(f"  - Fruits: {fruits}")
                logger.info(f"  - Grains: {grains}")
                logger.info(f"  - Protein: {protein}")
                logger.info(f"  - Dairy: {dairy}")
                logger.info(f"  - Other: {other}")
                logger.info(f"FDA Nutritional Claims:")
                logger.info(f"  - Low Sodium: {low_sodium}")
                logger.info(f"  - Low Fat: {low_fat}")
                logger.info(f"  - High Fiber: {high_fiber}")
                logger.info(f"  - High Protein: {high_protein}")
                logger.info(f"Potential Allergens Detected: {allergens}")
                
                # Commit the transaction
                conn.commit()
                logger.info("Database transaction committed successfully")
                
                return results
            else:
                logger.warning("No results returned from update function")
                return None
                
    except Exception as e:
        logger.error(f"Dietary flags update failed: {e}")
        conn.rollback()
        raise

def generate_validation_report(conn):
    """Generate validation reports using the created views"""
    reports = [
        {
            'name': 'MyPlate Mapping Validation',
            'query': 'SELECT * FROM myplate_mapping_validation LIMIT 20;'
        },
        {
            'name': 'FDA Nutritional Claims Summary',
            'query': 'SELECT * FROM fda_nutritional_claims_summary;'
        },
        {
            'name': 'Allergen Detection Summary',
            'query': 'SELECT * FROM allergen_detection_summary;'
        }
    ]
    
    try:
        with conn.cursor() as cursor:
            logger.info("=== VALIDATION REPORTS ===")
            
            for report in reports:
                logger.info(f"\n{report['name']}:")
                cursor.execute(report['query'])
                results = cursor.fetchall()
                
                if results:
                    # Get column names
                    columns = [desc[0] for desc in cursor.description]
                    logger.info(f"Columns: {columns}")
                    
                    for row in results:
                        logger.info(f"  {dict(zip(columns, row))}")
                else:
                    logger.info("  No results found")
                    
    except Exception as e:
        logger.error(f"Validation report generation failed: {e}")

def sample_enhanced_records(conn):
    """Show sample records with enhanced dietary flags"""
    try:
        with conn.cursor() as cursor:
            logger.info("=== SAMPLE ENHANCED RECORDS ===")
            
            # Get diverse sample records
            sample_query = """
                SELECT 
                    description,
                    food_category,
                    jsonb_pretty(dietary_flags) as enhanced_flags
                FROM food_items 
                WHERE dietary_flags IS NOT NULL
                ORDER BY 
                    CASE dietary_flags->>'myplate_food_group'
                        WHEN 'vegetables' THEN 1
                        WHEN 'fruits' THEN 2
                        WHEN 'grains' THEN 3
                        WHEN 'protein' THEN 4
                        WHEN 'dairy' THEN 5
                        ELSE 6
                    END
                LIMIT 10;
            """
            
            cursor.execute(sample_query)
            results = cursor.fetchall()
            
            for i, (description, category, flags) in enumerate(results, 1):
                logger.info(f"\nSample {i}:")
                logger.info(f"  Description: {description}")
                logger.info(f"  Category: {category}")
                logger.info(f"  Enhanced Flags: {flags}")
                
    except Exception as e:
        logger.error(f"Sample records display failed: {e}")

def main():
    """Main execution function"""
    try:
        logger.info("Starting dietary flags implementation...")
        
        # Create database connection
        conn = create_database_connection()
        logger.info("Database connection established")
        
        # Load SQL functions
        load_sql_functions(conn)
        
        # Test functions
        test_functions(conn)
        
        # Update dietary flags
        update_results = update_dietary_flags(conn)
        
        # Generate validation reports
        generate_validation_report(conn)
        
        # Show sample enhanced records
        sample_enhanced_records(conn)
        
        logger.info("=== IMPLEMENTATION COMPLETE ===")
        logger.info("Dietary flags have been successfully implemented with:")
        logger.info("- USDA MyPlate food group classifications")
        logger.info("- FDA nutritional claims based on CFR Title 21")
        logger.info("- FDA allergen detection per FALCPA/FASTER Act")
        logger.info("- Proper data source attribution and disclaimers")
        
    except Exception as e:
        logger.error(f"Implementation failed: {e}")
        raise
        
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed")

if __name__ == "__main__":
    main()