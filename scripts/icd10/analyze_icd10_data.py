#!/usr/bin/env python3

from src.database import get_db_session, ICD10Code
from sqlalchemy import text

with get_db_session() as db:
    # Check current data quality
    result = db.execute(text("""
        SELECT 
            COUNT(*) as total_codes,
            COUNT(CASE WHEN category IS NOT NULL AND category != '' THEN 1 END) as has_category,
            COUNT(CASE WHEN search_vector IS NOT NULL THEN 1 END) as has_search_vector,
            COUNT(CASE WHEN chapter IS NOT NULL AND chapter != '' THEN 1 END) as has_chapter,
            COUNT(CASE WHEN is_billable IS NOT NULL THEN 1 END) as has_billable,
            COUNT(CASE WHEN parent_code IS NOT NULL AND parent_code != '' THEN 1 END) as has_parent
        FROM icd10_codes
    """)).fetchone()
    
    print('=== ICD10 DATA QUALITY ANALYSIS ===')
    print(f'Total codes: {result.total_codes:,}')
    print(f'Has category: {result.has_category:,} ({result.has_category/result.total_codes*100:.2f}%)')
    print(f'Has search_vector: {result.has_search_vector:,} ({result.has_search_vector/result.total_codes*100:.2f}%)')
    print(f'Has chapter: {result.has_chapter:,} ({result.has_chapter/result.total_codes*100:.2f}%)')
    print(f'Has billable: {result.has_billable:,} ({result.has_billable/result.total_codes*100:.2f}%)')
    print(f'Has parent: {result.has_parent:,} ({result.has_parent/result.total_codes*100:.2f}%)')
    
    # Sample records missing category
    print('\n=== SAMPLE RECORDS MISSING CATEGORY ===')
    result = db.execute(text("SELECT code, description, category FROM icd10_codes WHERE category IS NULL OR category = '' LIMIT 5")).fetchall()
    for row in result:
        print(f'{row.code}: {row.description[:60]}... | Category: "{row.category}"')
    
    # Sample records missing search_vector  
    print('\n=== SAMPLE RECORDS MISSING SEARCH_VECTOR ===')
    result = db.execute(text("SELECT code, description, search_text FROM icd10_codes WHERE search_vector IS NULL LIMIT 5")).fetchall()
    for row in result:
        print(f'{row.code}: {row.description[:60]}... | SearchText: "{row.search_text}"')
    
    # Check category field patterns
    print('\n=== CATEGORY FIELD ANALYSIS ===')
    result = db.execute(text("""
        SELECT category, COUNT(*) as count 
        FROM icd10_codes 
        WHERE category IS NOT NULL AND category != '' 
        GROUP BY category 
        ORDER BY count DESC 
        LIMIT 10
    """)).fetchall()
    
    if result:
        print("Most common categories:")
        for row in result:
            print(f'  "{row.category}": {row.count} codes')
    else:
        print("No category data found!")
    
    # Check search_text patterns
    print('\n=== SEARCH_TEXT PATTERNS ===')
    result = db.execute(text("""
        SELECT 
            COUNT(CASE WHEN search_text IS NULL THEN 1 END) as null_search_text,
            COUNT(CASE WHEN search_text = '' THEN 1 END) as empty_search_text,
            COUNT(CASE WHEN search_text IS NOT NULL AND search_text != '' THEN 1 END) as has_search_text
        FROM icd10_codes
    """)).fetchone()
    
    print(f'Null search_text: {result.null_search_text:,}')
    print(f'Empty search_text: {result.empty_search_text:,}')
    print(f'Has search_text: {result.has_search_text:,}')
    
    # Sample codes with good data
    print('\n=== SAMPLE CODES WITH GOOD DATA ===')
    result = db.execute(text("""
        SELECT code, description, category, search_text 
        FROM icd10_codes 
        WHERE category IS NOT NULL AND category != '' 
          AND search_text IS NOT NULL AND search_text != ''
        LIMIT 3
    """)).fetchall()
    
    for row in result:
        print(f'{row.code}: {row.description}')
        print(f'  Category: "{row.category}"')
        print(f'  SearchText: "{row.search_text[:100]}..."')
        print()