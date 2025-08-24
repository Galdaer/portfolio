#!/usr/bin/env python3
"""
Migration script to copy medical data from intelluxe to intelluxe_public database
Only copies the small tables that have some data already.
"""

import sys

import psycopg2


def migrate_medical_data():
    """Migrate medical data from intelluxe to intelluxe_public database"""

    # Database connections
    source_conn_str = "postgresql://intelluxe:secure_password@localhost:5432/intelluxe"
    target_conn_str = "postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public"

    # Tables to migrate (only small ones with existing data)
    tables_to_migrate = [
        "billing_codes",
        "exercises",
        "icd10_codes",
    ]

    try:
        # Connect to both databases
        print("Connecting to databases...")
        source_conn = psycopg2.connect(source_conn_str)
        target_conn = psycopg2.connect(target_conn_str)

        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        total_migrated = 0

        for table in tables_to_migrate:
            print(f"\n📋 Migrating table: {table}")

            try:
                # Get count from source
                source_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                source_count = source_cursor.fetchone()[0]

                # Get count from target
                target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                target_count = target_cursor.fetchone()[0]

                print(f"   Source: {source_count} records, Target: {target_count} records")

                if source_count == 0:
                    print(f"   ⚠️  No data in source table {table}, skipping")
                    continue

                if target_count > 0:
                    print(f"   🔄 Target table has {target_count} records, clearing first...")
                    target_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                    target_conn.commit()

                # Copy all data
                print(f"   🔄 Copying {source_count} records...")

                # Get all column names for the table
                source_cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}' AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in source_cursor.fetchall()]
                column_list = ", ".join(columns)

                # Handle special cases for each table
                if table == "exercises":
                    # Copy exercises with JSON field handling
                    source_cursor.execute(f"""
                        SELECT exercise_id, name, body_part, equipment, target,
                               secondary_muscles::text::jsonb, instructions::text::jsonb,
                               gif_url, difficulty_level, exercise_type, duration_estimate,
                               calories_estimate, source, search_text, search_vector,
                               last_updated, created_at
                        FROM {table}
                    """)
                    rows = source_cursor.fetchall()

                    if rows:
                        insert_sql = f"""
                            INSERT INTO {table} (
                                exercise_id, name, body_part, equipment, target,
                                secondary_muscles, instructions, gif_url, difficulty_level,
                                exercise_type, duration_estimate, calories_estimate, source,
                                search_text, search_vector, last_updated, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        target_cursor.executemany(insert_sql, rows)
                        target_conn.commit()

                elif table == "icd10_codes":
                    # Copy ICD-10 codes with array to JSONB conversion
                    source_cursor.execute(f"""
                        SELECT code, description, category, chapter, parent_code,
                               billable, CASE WHEN synonyms IS NOT NULL
                                         THEN array_to_json(synonyms)::jsonb
                                         ELSE NULL END as synonyms,
                               source, search_text, search_vector, code_length,
                               last_updated, created_at
                        FROM {table}
                    """)
                    rows = source_cursor.fetchall()

                    if rows:
                        insert_sql = f"""
                            INSERT INTO {table} (
                                code, description, category, chapter, parent_code,
                                billable, synonyms, source, search_text, search_vector,
                                code_length, last_updated, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        target_cursor.executemany(insert_sql, rows)
                        target_conn.commit()
                else:
                    # Standard copy for other tables
                    source_cursor.execute(f"SELECT {column_list} FROM {table}")
                    rows = source_cursor.fetchall()

                    if rows:
                        placeholders = ", ".join(["%s"] * len(columns))
                        insert_sql = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"
                        target_cursor.executemany(insert_sql, rows)
                        target_conn.commit()

                # Verify count for all tables
                target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                final_count = target_cursor.fetchone()[0]

                print(f"   ✅ Successfully migrated {final_count} records to {table}")
                total_migrated += final_count

            except Exception as e:
                print(f"   ❌ Error migrating {table}: {e}")
                target_conn.rollback()

        # Close connections
        source_cursor.close()
        target_cursor.close()
        source_conn.close()
        target_conn.close()

        print("\n🎉 Migration completed successfully!")
        print(f"   Total records migrated: {total_migrated}")
        print(f"   Tables processed: {', '.join(tables_to_migrate)}")

        # Show final counts in target database
        print("\n📊 Final counts in intelluxe_public:")
        target_conn = psycopg2.connect(target_conn_str)
        target_cursor = target_conn.cursor()

        all_tables = [
            "pubmed_articles", "clinical_trials", "fda_drugs",
            "health_topics", "food_items", "exercises",
            "icd10_codes", "billing_codes",
        ]

        for table in all_tables:
            try:
                target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = target_cursor.fetchone()[0]
                status = "✅" if count > 0 else "⚠️"
                print(f"   {status} {table:20} {count:8} records")
            except Exception as e:
                print(f"   ❌ {table:20} ERROR: {e}")

        target_cursor.close()
        target_conn.close()

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_medical_data()
