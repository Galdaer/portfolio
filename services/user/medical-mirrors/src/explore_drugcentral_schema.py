#!/usr/bin/env python3
"""
Explore DrugCentral PostgreSQL database schema
"""

import asyncio
import asyncpg
import ssl
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def explore_schema():
    """Explore DrugCentral schema to understand table structure"""
    
    # Connection parameters
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connection = None
    try:
        connection = await asyncpg.connect(
            host='unmtid-dbs.net',
            port=5433,
            database='drugcentral',
            user='drugman',
            password='dosage',
            ssl=ssl_context
        )
        
        logger.info("Connected to DrugCentral database")
        
        # List all tables
        logger.info("\n=== Available Tables ===")
        tables_query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        tables = await connection.fetch(tables_query)
        for table in tables:
            logger.info(f"Table: {table['table_name']}")
        
        # Check for drug/structure related tables
        logger.info("\n=== Structure/Drug Related Tables ===")
        drug_tables = [t['table_name'] for t in tables if any(keyword in t['table_name'].lower() for keyword in ['struct', 'drug', 'compound', 'molecule'])]
        for table in drug_tables:
            logger.info(f"Drug-related table: {table}")
        
        # Let's examine some key tables schema
        key_tables = ['structures', 'struct2drug', 'drug', 'atc', 'indication', 'contraindication']
        
        for table_name in key_tables:
            if any(t['table_name'] == table_name for t in tables):
                logger.info(f"\n=== Schema for {table_name} ===")
                schema_query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
                """
                columns = await connection.fetch(schema_query)
                for col in columns:
                    logger.info(f"  {col['column_name']}: {col['data_type']} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
                
                # Sample some data
                try:
                    sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                    samples = await connection.fetch(sample_query)
                    logger.info(f"  Sample data ({len(samples)} rows):")
                    for i, row in enumerate(samples):
                        logger.info(f"    Row {i+1}: {dict(row)}")
                except Exception as e:
                    logger.warning(f"  Could not sample data: {e}")
        
        # Look for activity/bioactivity tables
        logger.info("\n=== Activity/Bioactivity Related Tables ===")
        activity_tables = [t['table_name'] for t in tables if any(keyword in t['table_name'].lower() for keyword in ['act', 'bio', 'target', 'moa', 'mechanism'])]
        for table in activity_tables:
            logger.info(f"Activity-related table: {table}")
            
        # Look for target tables
        logger.info("\n=== Target Related Tables ===")
        target_tables = [t['table_name'] for t in tables if 'target' in t['table_name'].lower()]
        for table in target_tables:
            logger.info(f"Target-related table: {table}")
        
        # Try to find mechanism of action data
        moa_candidates = ['act_table_full', 'bioactivity', 'target_go', 'pharma_class', 'act_table_full']
        logger.info("\n=== Checking MOA candidate tables ===")
        for candidate in moa_candidates:
            if any(t['table_name'] == candidate for t in tables):
                logger.info(f"Found candidate table: {candidate}")
                try:
                    schema_query = f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = '{candidate}'
                    ORDER BY ordinal_position
                    """
                    columns = await connection.fetch(schema_query)
                    logger.info(f"  Columns: {[col['column_name'] for col in columns]}")
                except Exception as e:
                    logger.warning(f"  Error examining {candidate}: {e}")
        
    except Exception as e:
        logger.error(f"Error exploring schema: {e}")
    finally:
        if connection:
            await connection.close()


if __name__ == "__main__":
    asyncio.run(explore_schema())