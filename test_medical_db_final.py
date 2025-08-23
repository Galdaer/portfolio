#!/usr/bin/env python3
"""Final test for updated medical_db.py with corrected schemas"""

import psycopg2
import json

connection_string = "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"

def test_all_tables():
    """Test all medical mirror tables with corrected schemas"""
    
    try:
        print("=" * 60)
        print("Testing All Medical Mirror Tables")
        print("=" * 60)
        
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # 1. Test FDA drugs (unified schema)
        print("\n1. FDA Drugs (new unified schema):")
        cursor.execute("""
            SELECT ndc, name, generic_name, brand_name, manufacturer, 
                   array_length(data_sources, 1) as source_count
            FROM fda_drugs
            WHERE search_vector @@ plainto_tsquery('aspirin')
            LIMIT 2
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  - {row[1]} (NDC: {row[0]})")
                print(f"    Sources: {row[5] or 0} data sources")
        else:
            print("  No FDA drugs with 'aspirin' found (table may be empty)")
        
        # 2. Test health topics (JSONB sections)
        print("\n2. Health Topics (JSONB sections):")
        cursor.execute("""
            SELECT topic_id, title, category, 
                   jsonb_object_keys(sections) as section_names
            FROM health_topics
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            print(f"  - {result[1]} (ID: {result[0]})")
            print(f"    Category: {result[2]}")
            # Get all section names for this topic
            cursor.execute("""
                SELECT array_agg(jsonb_object_keys(sections))
                FROM health_topics
                WHERE topic_id = %s
            """, (result[0],))
            sections = cursor.fetchone()[0]
            if sections:
                print(f"    Sections: {', '.join(sections)}")
        else:
            print("  No health topics found")
        
        # 3. Test food items (JSONB nutrition)
        print("\n3. Food Items (JSONB nutrition):")
        cursor.execute("""
            SELECT fdc_id, description, 
                   nutrition_summary->>'calories' as calories,
                   nutrition_summary->>'protein' as protein
            FROM food_items
            WHERE search_vector @@ plainto_tsquery('apple')
            LIMIT 2
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  - {row[1]} (FDC: {row[0]})")
                print(f"    Calories: {row[2]}, Protein: {row[3]}g")
        else:
            print("  No food items with 'apple' found")
        
        # 4. Test exercises (JSONB instructions)
        print("\n4. Exercises (JSONB arrays):")
        cursor.execute("""
            SELECT exercise_id, name, body_part, 
                   jsonb_array_length(instructions) as instruction_count
            FROM exercises
            WHERE body_part = 'chest'
            LIMIT 2
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  - {row[1]} (ID: {row[0]})")
                print(f"    Body Part: {row[2]}, Instructions: {row[3] or 0} steps")
        else:
            print("  No chest exercises found")
        
        # 5. Test ICD-10 codes
        print("\n5. ICD-10 Codes:")
        cursor.execute("""
            SELECT code, description, billable
            FROM icd10_codes
            WHERE code LIKE 'E11%'
            LIMIT 2
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  - {row[0]}: {row[1]}")
                print(f"    Billable: {row[2]}")
        else:
            print("  No diabetes ICD-10 codes found")
        
        # 6. Test billing codes
        print("\n6. Billing Codes:")
        cursor.execute("""
            SELECT code, code_type, short_description, is_active
            FROM billing_codes
            WHERE code_type = 'CPT' OR code_type = 'HCPCS'
            LIMIT 2
        """)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(f"  - {row[0]} ({row[1]}): {row[2]}")
                print(f"    Active: {row[3]}")
        else:
            print("  No CPT/HCPCS codes found")
        
        # 7. Summary statistics
        print("\n" + "=" * 60)
        print("Table Statistics:")
        print("=" * 60)
        
        tables = [
            "pubmed_articles", "clinical_trials", "fda_drugs",
            "health_topics", "food_items", "exercises",
            "icd10_codes", "billing_codes", "update_logs"
        ]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            # Get sample search vector usage
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE search_vector IS NOT NULL
            """)
            searchable = cursor.fetchone()[0]
            
            print(f"  {table:20} {count:8} records ({searchable} searchable)")
        
        conn.close()
        print("\n✅ All database schema tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_all_tables()