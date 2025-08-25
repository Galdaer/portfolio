#!/usr/bin/env python3
"""
Medical Data Status Reporter
Simple script to check current status of all medical databases
"""

import json
import psycopg2
from datetime import datetime

def get_database_status():
    """Get current record counts from medical database"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="intelluxe_public",
            user="intelluxe", 
            password="secure_password"
        )
        
        cursor = conn.cursor()
        
        # Get counts from all medical tables
        cursor.execute("""
            SELECT 
                'pubmed_articles' as table_name, COUNT(*) as count FROM pubmed_articles 
            UNION ALL SELECT 
                'clinical_trials', COUNT(*) FROM clinical_trials 
            UNION ALL SELECT 
                'drug_information', COUNT(*) FROM drug_information 
            UNION ALL SELECT 
                'health_topics', COUNT(*) FROM health_topics 
            UNION ALL SELECT 
                'food_items', COUNT(*) FROM food_items 
            UNION ALL SELECT 
                'exercises', COUNT(*) FROM exercises 
            UNION ALL SELECT 
                'icd10_codes', COUNT(*) FROM icd10_codes 
            UNION ALL SELECT 
                'billing_codes', COUNT(*) FROM billing_codes 
            ORDER BY table_name
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format results
        status = {}
        total = 0
        for table, count in results:
            status[table] = count
            total += count
        
        status['_total'] = total
        status['_timestamp'] = datetime.now().isoformat()
        
        return status
        
    except Exception as e:
        print(f"Database error: {e}")
        return None

def print_status_report(status):
    """Print formatted status report"""
    print("\n" + "="*70)
    print("🏥 MEDICAL DATABASE STATUS REPORT")
    print("="*70)
    print(f"📅 Generated: {status['_timestamp']}")
    print(f"📊 Total Records: {status['_total']:,}")
    print()
    
    # Table status
    tables = [
        ("pubmed_articles", "PubMed Research Articles"),
        ("clinical_trials", "Clinical Trials Studies"), 
        ("drug_information", "FDA Drug Information"),
        ("icd10_codes", "ICD-10 Diagnostic Codes"),
        ("billing_codes", "Medical Billing Codes"),
        ("health_topics", "Health Topics"),
        ("food_items", "USDA Food Data"),
        ("exercises", "Exercise Database")
    ]
    
    for table, description in tables:
        count = status.get(table, 0)
        
        # Determine status
        if table == "pubmed_articles" and count >= 400000:
            icon = "✅"
        elif table == "clinical_trials" and count >= 200000:
            icon = "✅"
        elif table == "drug_information" and count >= 20000:
            icon = "✅"
        elif table == "icd10_codes" and count >= 40000:
            icon = "✅"
        elif table == "billing_codes" and count >= 8000:
            icon = "✅"
        elif table in ["health_topics", "food_items", "exercises"] and count > 0:
            icon = "✅"
        elif count > 0:
            icon = "⚠️"
        else:
            icon = "❌"
        
        print(f"{icon} {description:<30} {count:>10,}")
    
    print("="*70)
    
    # Overall assessment
    good_count = sum(1 for table, _ in tables if status.get(table, 0) > 0)
    if good_count == len(tables):
        print("🎉 STATUS: All data sources operational")
    elif good_count >= 6:
        print("✅ STATUS: System operational with minor gaps")
    else:
        print("⚠️ STATUS: Several data sources need attention")
    
    print()

def main():
    """Main function"""
    import sys
    
    status = get_database_status()
    if not status:
        print("❌ Could not connect to medical database")
        sys.exit(1)
    
    # Check for JSON output flag
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(json.dumps(status, indent=2))
    else:
        print_status_report(status)

if __name__ == "__main__":
    main()