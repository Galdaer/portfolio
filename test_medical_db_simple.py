#!/usr/bin/env python3
"""Simple test for medical database connectivity"""


import psycopg2

# Direct connection test
connection_string = "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"

try:
    print("Testing direct database connection...")
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()

    # Test each table
    tables = [
        "pubmed_articles", "clinical_trials", "fda_drugs",
        "health_topics", "food_items", "exercises",
        "icd10_codes", "billing_codes",
    ]

    print("\nTable counts:")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  ✅ {table}: {count} records")
        except Exception as e:
            print(f"  ❌ {table}: Error - {e}")

    # Test a simple search on FDA drugs with new schema
    print("\n\nTesting FDA drugs search with new schema...")
    cursor.execute("""
        SELECT ndc, name, generic_name, brand_name, manufacturer
        FROM fda_drugs
        WHERE search_vector @@ plainto_tsquery('aspirin')
        LIMIT 3
    """)

    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} results for 'aspirin':")
        for row in results:
            print(f"  - {row[1]} (NDC: {row[0]})")
            print(f"    Generic: {row[2]}, Brand: {row[3]}")
            print(f"    Manufacturer: {row[4]}")
    else:
        print("No results found for 'aspirin'")

    # Test health topics (new table)
    print("\n\nTesting health topics search (NEW)...")
    cursor.execute("""
        SELECT topic_id, title, summary
        FROM health_topics
        WHERE search_vector @@ plainto_tsquery('diabetes')
        LIMIT 3
    """)

    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} health topics for 'diabetes':")
        for row in results:
            print(f"  - {row[1]} (ID: {row[0]})")
            if row[2]:
                print(f"    {row[2][:100]}...")
    else:
        print("No health topics found")

    # Test food items (new table)
    print("\n\nTesting food items search (NEW)...")
    cursor.execute("""
        SELECT fdc_id, description, calories, protein, fat, carbohydrates
        FROM food_items
        WHERE search_vector @@ plainto_tsquery('apple')
        LIMIT 3
    """)

    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} food items for 'apple':")
        for row in results:
            print(f"  - {row[1]} (FDC ID: {row[0]})")
            print(f"    Calories: {row[2]}, Protein: {row[3]}g, Fat: {row[4]}g, Carbs: {row[5]}g")
    else:
        print("No food items found")

    # Test exercises (new table)
    print("\n\nTesting exercises search (NEW)...")
    cursor.execute("""
        SELECT exercise_id, name, body_part, equipment
        FROM exercises
        WHERE search_vector @@ plainto_tsquery('push')
        LIMIT 3
    """)

    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} exercises for 'push':")
        for row in results:
            print(f"  - {row[1]} (ID: {row[0]})")
            print(f"    Body Part: {row[2]}, Equipment: {row[3]}")
    else:
        print("No exercises found")

    # Test ICD-10 codes (new table)
    print("\n\nTesting ICD-10 codes search (NEW)...")
    cursor.execute("""
        SELECT code, description, billable
        FROM icd10_codes
        WHERE code = 'E11.9'
        LIMIT 1
    """)

    result = cursor.fetchone()
    if result:
        print("Found ICD-10 code E11.9:")
        print(f"  - {result[0]}: {result[1]}")
        print(f"    Billable: {result[2]}")
    else:
        print("ICD-10 code E11.9 not found")

    # Test billing codes (new table)
    print("\n\nTesting billing codes search (NEW)...")
    cursor.execute("""
        SELECT code, code_type, short_description, category
        FROM billing_codes
        WHERE search_vector @@ plainto_tsquery('injection')
        LIMIT 3
    """)

    results = cursor.fetchall()
    if results:
        print(f"Found {len(results)} billing codes for 'injection':")
        for row in results:
            print(f"  - {row[0]} ({row[1]}): {row[2]}")
            print(f"    Category: {row[3]}")
    else:
        print("No billing codes found")

    conn.close()
    print("\n✅ All direct database tests completed successfully!")

except Exception as e:
    print(f"❌ Database test failed: {e}")
    import traceback
    traceback.print_exc()
