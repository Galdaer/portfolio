#!/usr/bin/env python3
"""
Database Migration Script
Migrates from single database to separated PHI/non-PHI databases
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database.db_config_manager import DatabaseConfigManager
from core.infrastructure.healthcare_logger import get_healthcare_logger

logger = get_healthcare_logger("database.migration")


class DatabaseMigrator:
    """Handles migration from single database to separated databases"""
    
    def __init__(self):
        self.logger = logger
        self.config_manager = DatabaseConfigManager()
        
        # Database connection parameters
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = os.getenv("POSTGRES_PORT", "5432")
        self.postgres_user = os.getenv("POSTGRES_USER", "intelluxe")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "secure_password")
        
        # Target database names
        self.public_db = "intelluxe_public"
        self.private_db = "intelluxe_clinical"
        
        # Source database (existing)
        self.source_db = os.getenv("POSTGRES_DB", "intelluxe")
        
    def _get_connection(self, database="postgres"):
        """Get PostgreSQL connection"""
        return psycopg2.connect(
            host=self.postgres_host,
            port=self.postgres_port,
            user=self.postgres_user,
            password=self.postgres_password,
            database=database
        )
        
    def backup_existing_database(self):
        """Create backup of existing database"""
        try:
            backup_file = f"/tmp/intelluxe_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            self.logger.info(f"Creating backup of {self.source_db} to {backup_file}")
            
            cmd = [
                "pg_dump",
                "-h", self.postgres_host,
                "-p", str(self.postgres_port),
                "-U", self.postgres_user,
                "-d", self.source_db,
                "-f", backup_file,
                "--verbose"
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = self.postgres_password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Backup completed successfully: {backup_file}")
                return backup_file
            else:
                self.logger.error(f"Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
            
    def create_databases(self):
        """Create public and private databases if they don't exist"""
        try:
            conn = self._get_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check and create public database
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.public_db}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {self.public_db}")
                self.logger.info(f"Created database: {self.public_db}")
            else:
                self.logger.info(f"Database already exists: {self.public_db}")
                
            # Check and create private database
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.private_db}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {self.private_db}")
                self.logger.info(f"Created database: {self.private_db}")
            else:
                self.logger.info(f"Database already exists: {self.private_db}")
                
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create databases: {e}")
            return False
            
    async def apply_schemas(self):
        """Apply schema files to databases"""
        try:
            # Initialize config manager
            await self.config_manager.initialize()
            
            # Apply schemas
            await self.config_manager.apply_schemas()
            
            self.logger.info("Successfully applied database schemas")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply schemas: {e}")
            return False
            
    def migrate_medical_reference_data(self):
        """Ensure medical reference data is in public database"""
        try:
            # Medical reference tables that should be in public database
            medical_tables = [
                "pubmed_articles",
                "clinical_trials",
                "fda_drugs",
                "health_topics",
                "food_items",
                "exercises",
                "icd10_codes",
                "billing_codes",
                "update_logs"
            ]
            
            # Check if tables exist in source database
            source_conn = self._get_connection(self.source_db)
            source_cursor = source_conn.cursor()
            
            public_conn = self._get_connection(self.public_db)
            public_cursor = public_conn.cursor()
            
            for table in medical_tables:
                # Check if table exists in source
                source_cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """)
                
                if source_cursor.fetchone()[0]:
                    # Check if table exists in public database
                    public_cursor.execute(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table}'
                        )
                    """)
                    
                    if not public_cursor.fetchone()[0]:
                        self.logger.info(f"Migrating table {table} to public database")
                        
                        # Use pg_dump/pg_restore for table migration
                        dump_file = f"/tmp/{table}_dump.sql"
                        
                        # Dump table from source
                        dump_cmd = [
                            "pg_dump",
                            "-h", self.postgres_host,
                            "-p", str(self.postgres_port),
                            "-U", self.postgres_user,
                            "-d", self.source_db,
                            "-t", table,
                            "-f", dump_file,
                            "--data-only" if table != "update_logs" else "--clean"
                        ]
                        
                        env = os.environ.copy()
                        env["PGPASSWORD"] = self.postgres_password
                        
                        subprocess.run(dump_cmd, env=env, check=True)
                        
                        # Restore to public database
                        restore_cmd = [
                            "psql",
                            "-h", self.postgres_host,
                            "-p", str(self.postgres_port),
                            "-U", self.postgres_user,
                            "-d", self.public_db,
                            "-f", dump_file
                        ]
                        
                        subprocess.run(restore_cmd, env=env, check=True)
                        
                        # Clean up temp file
                        os.remove(dump_file)
                        
                        self.logger.info(f"Successfully migrated {table}")
                    else:
                        self.logger.info(f"Table {table} already exists in public database")
                else:
                    self.logger.info(f"Table {table} not found in source database")
                    
            source_cursor.close()
            source_conn.close()
            public_cursor.close()
            public_conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate medical reference data: {e}")
            return False
            
    def migrate_phi_data(self):
        """Migrate any PHI data to private database"""
        try:
            # Check for any existing PHI tables in source database
            # (In a fresh setup, these might not exist yet)
            phi_tables = [
                "appointments",
                "patient_scheduling_preferences",
                "appointment_wait_times",
                "scheduling_clinical_notes",
                "patient_communications"
            ]
            
            source_conn = self._get_connection(self.source_db)
            source_cursor = source_conn.cursor()
            
            private_conn = self._get_connection(self.private_db)
            private_cursor = private_conn.cursor()
            
            for table in phi_tables:
                # Check if table exists in source
                source_cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    )
                """)
                
                if source_cursor.fetchone()[0]:
                    self.logger.info(f"Found PHI table {table} in source - migrating to private database")
                    
                    # Similar migration process as above
                    dump_file = f"/tmp/{table}_phi_dump.sql"
                    
                    dump_cmd = [
                        "pg_dump",
                        "-h", self.postgres_host,
                        "-p", str(self.postgres_port),
                        "-U", self.postgres_user,
                        "-d", self.source_db,
                        "-t", table,
                        "-f", dump_file,
                        "--data-only"
                    ]
                    
                    env = os.environ.copy()
                    env["PGPASSWORD"] = self.postgres_password
                    
                    subprocess.run(dump_cmd, env=env, check=True)
                    
                    restore_cmd = [
                        "psql",
                        "-h", self.postgres_host,
                        "-p", str(self.postgres_port),
                        "-U", self.postgres_user,
                        "-d", self.private_db,
                        "-f", dump_file
                    ]
                    
                    subprocess.run(restore_cmd, env=env, check=True)
                    
                    os.remove(dump_file)
                    
                    self.logger.info(f"Successfully migrated PHI table {table}")
                else:
                    self.logger.info(f"PHI table {table} not found in source (expected for new setup)")
                    
            source_cursor.close()
            source_conn.close()
            private_cursor.close()
            private_conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate PHI data: {e}")
            return False
            
    def update_environment_variables(self):
        """Update environment variables for new database configuration"""
        try:
            env_updates = {
                "PUBLIC_DB_HOST": self.postgres_host,
                "PUBLIC_DB_PORT": self.postgres_port,
                "PUBLIC_DB_USER": self.postgres_user,
                "PUBLIC_DB_PASSWORD": self.postgres_password,
                "PUBLIC_DB_NAME": self.public_db,
                "PRIVATE_DB_HOST": self.postgres_host,
                "PRIVATE_DB_PORT": self.postgres_port,
                "PRIVATE_DB_USER": self.postgres_user,
                "PRIVATE_DB_PASSWORD": self.postgres_password,
                "PRIVATE_DB_NAME": self.private_db,
                "DB_ENCRYPTION_KEY": os.getenv("DB_ENCRYPTION_KEY", "")
            }
            
            # Check if .env file exists
            env_file = Path(__file__).parent.parent / ".env"
            
            if env_file.exists():
                self.logger.info(f"Updating {env_file}")
                
                # Read existing env file
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                    
                # Update or add new variables
                updated_lines = []
                updated_keys = set()
                
                for line in lines:
                    if '=' in line:
                        key = line.split('=')[0].strip()
                        if key in env_updates:
                            updated_lines.append(f"{key}={env_updates[key]}\n")
                            updated_keys.add(key)
                        else:
                            updated_lines.append(line)
                    else:
                        updated_lines.append(line)
                        
                # Add missing variables
                for key, value in env_updates.items():
                    if key not in updated_keys:
                        updated_lines.append(f"{key}={value}\n")
                        
                # Write back
                with open(env_file, 'w') as f:
                    f.writelines(updated_lines)
                    
                self.logger.info("Updated environment variables")
            else:
                self.logger.warning(f"No .env file found at {env_file}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update environment variables: {e}")
            return False
            
    async def run_migration(self):
        """Run the complete migration process"""
        try:
            self.logger.info("Starting database migration process")
            
            # Step 1: Backup existing database
            backup_file = self.backup_existing_database()
            if not backup_file:
                self.logger.warning("Backup failed, but continuing with migration")
                
            # Step 2: Create databases
            if not self.create_databases():
                raise Exception("Failed to create databases")
                
            # Step 3: Apply schemas
            if not await self.apply_schemas():
                raise Exception("Failed to apply schemas")
                
            # Step 4: Migrate medical reference data
            if not self.migrate_medical_reference_data():
                raise Exception("Failed to migrate medical reference data")
                
            # Step 5: Migrate PHI data (if any exists)
            if not self.migrate_phi_data():
                raise Exception("Failed to migrate PHI data")
                
            # Step 6: Update environment variables
            if not self.update_environment_variables():
                self.logger.warning("Failed to update environment variables - manual update may be needed")
                
            # Step 7: Verify migration
            await self.verify_migration()
            
            self.logger.info("Database migration completed successfully!")
            
            if backup_file:
                self.logger.info(f"Backup saved at: {backup_file}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False
            
    async def verify_migration(self):
        """Verify the migration was successful"""
        try:
            # Get database info from config manager
            info = await self.config_manager.get_database_info()
            
            self.logger.info("Migration verification:")
            self.logger.info(f"Databases exist: {info['databases_exist']}")
            
            # Check table counts
            public_conn = self._get_connection(self.public_db)
            public_cursor = public_conn.cursor()
            
            public_cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            public_table_count = public_cursor.fetchone()[0]
            
            private_conn = self._get_connection(self.private_db)
            private_cursor = private_conn.cursor()
            
            private_cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            private_table_count = private_cursor.fetchone()[0]
            
            self.logger.info(f"Public database tables: {public_table_count}")
            self.logger.info(f"Private database tables: {private_table_count}")
            
            # Check medical data
            medical_tables = ["pubmed_articles", "clinical_trials", "fda_drugs"]
            for table in medical_tables:
                public_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = public_cursor.fetchone()[0]
                self.logger.info(f"  {table}: {count} records")
                
            public_cursor.close()
            public_conn.close()
            private_cursor.close()
            private_conn.close()
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")


async def main():
    """Main migration entry point"""
    print("=" * 60)
    print("Database Migration Tool")
    print("Migrating to separated PHI/non-PHI databases")
    print("=" * 60)
    
    # Check for required environment variables
    required_env = ["POSTGRES_PASSWORD"]
    missing = [var for var in required_env if not os.getenv(var)]
    
    if missing:
        print(f"\nError: Missing required environment variables: {', '.join(missing)}")
        print("Please set these variables and try again.")
        return 1
        
    # Confirm migration
    print("\nThis will:")
    print("1. Backup the existing database")
    print("2. Create new public and private databases")
    print("3. Apply security-hardened schemas")
    print("4. Migrate medical reference data to public database")
    print("5. Migrate any PHI data to private database")
    print("6. Update environment configuration")
    
    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != "yes":
        print("Migration cancelled")
        return 0
        
    # Run migration
    migrator = DatabaseMigrator()
    success = await migrator.run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Restart the healthcare-api service")
        print("2. Test database connections")
        print("3. Verify PHI audit logging")
        return 0
    else:
        print("\n❌ Migration failed. Check logs for details.")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))