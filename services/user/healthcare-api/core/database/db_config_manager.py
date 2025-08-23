"""
Database Configuration Manager
Manages database initialization, migrations, and configuration
"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

from core.database.secure_db_manager import get_db_manager, DatabaseType
from core.infrastructure.healthcare_logger import get_healthcare_logger


class DatabaseConfigManager:
    """Manages database configuration, initialization, and migrations"""
    
    def __init__(self, config_path: str = None):
        """Initialize the database configuration manager"""
        self.logger = get_healthcare_logger("database.config_manager")
        
        # Configuration paths
        self.base_path = Path(__file__).parent.parent.parent  # healthcare-api root
        self.config_path = config_path or self.base_path / "config" / "database_config.yml"
        self.schema_path = self.base_path / "core" / "database"
        
        # Load configuration
        self.config = self._load_config()
        
        # Database manager
        self.db_manager = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load database configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
            
    async def initialize(self):
        """Initialize database manager"""
        if self.db_manager is None:
            self.db_manager = await get_db_manager()
            
    async def check_databases_exist(self) -> Dict[str, bool]:
        """Check if configured databases exist"""
        results = {}
        
        try:
            # Check public database
            public_config = self.config["databases"]["public"]
            public_exists = await self._check_database_exists(
                public_config["name"],
                public_config.get("host", "localhost"),
                public_config.get("port", 5432)
            )
            results["public"] = public_exists
            
            # Check private database
            private_config = self.config["databases"]["private"]
            private_exists = await self._check_database_exists(
                private_config["name"],
                private_config.get("host", "localhost"),
                private_config.get("port", 5433)
            )
            results["private"] = private_exists
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to check databases: {e}")
            raise
            
    async def _check_database_exists(
        self, 
        db_name: str, 
        host: str, 
        port: int
    ) -> bool:
        """Check if a specific database exists"""
        try:
            # Use psql to check if database exists
            cmd = [
                "psql",
                "-h", host,
                "-p", str(port),
                "-U", os.getenv("POSTGRES_USER", "postgres"),
                "-lqt"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env={**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "")}
            )
            
            return db_name in result.stdout
            
        except Exception as e:
            self.logger.warning(f"Could not check database {db_name}: {e}")
            return False
            
    async def create_databases(self):
        """Create databases if they don't exist"""
        try:
            db_status = await self.check_databases_exist()
            
            # Create public database if needed
            if not db_status.get("public", False):
                await self._create_database(
                    self.config["databases"]["public"]["name"],
                    self.config["databases"]["public"].get("host", "localhost"),
                    self.config["databases"]["public"].get("port", 5432)
                )
                self.logger.info("Created public database")
                
            # Create private database if needed
            if not db_status.get("private", False):
                await self._create_database(
                    self.config["databases"]["private"]["name"],
                    self.config["databases"]["private"].get("host", "localhost"),
                    self.config["databases"]["private"].get("port", 5433)
                )
                self.logger.info("Created private database")
                
        except Exception as e:
            self.logger.error(f"Failed to create databases: {e}")
            raise
            
    async def _create_database(
        self, 
        db_name: str, 
        host: str, 
        port: int
    ):
        """Create a specific database"""
        try:
            # Use createdb command
            cmd = [
                "createdb",
                "-h", host,
                "-p", str(port),
                "-U", os.getenv("POSTGRES_USER", "postgres"),
                db_name
            ]
            
            subprocess.run(
                cmd,
                check=True,
                env={**os.environ, "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", "")}
            )
            
            self.logger.info(f"Created database: {db_name}")
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create database {db_name}: {e}")
            raise
            
    async def apply_schemas(self):
        """Apply database schemas"""
        await self.initialize()
        
        try:
            # Apply public schema
            public_schema_file = self.schema_path / "public_schema.sql"
            if public_schema_file.exists():
                await self._apply_schema(
                    public_schema_file,
                    DatabaseType.PUBLIC
                )
                self.logger.info("Applied public database schema")
            
            # Apply private schema
            private_schema_file = self.schema_path / "private_schema.sql"
            if private_schema_file.exists():
                await self._apply_schema(
                    private_schema_file,
                    DatabaseType.PRIVATE
                )
                self.logger.info("Applied private database schema")
                
        except Exception as e:
            self.logger.error(f"Failed to apply schemas: {e}")
            raise
            
    async def _apply_schema(
        self, 
        schema_file: Path, 
        database: DatabaseType
    ):
        """Apply a schema file to a database"""
        try:
            # Read schema file
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
                
            # Split into individual statements
            statements = [
                stmt.strip() 
                for stmt in schema_sql.split(';') 
                if stmt.strip()
            ]
            
            # Execute each statement
            for statement in statements:
                if statement:
                    try:
                        await self.db_manager.execute(
                            statement + ';',
                            database=database,
                            user_id="system"
                        )
                    except Exception as e:
                        # Log but continue - some statements might fail if objects exist
                        self.logger.warning(f"Schema statement warning: {e}")
                        
        except Exception as e:
            self.logger.error(f"Failed to apply schema {schema_file}: {e}")
            raise
            
    async def check_tables_exist(self) -> Dict[str, Dict[str, bool]]:
        """Check which tables exist in each database"""
        await self.initialize()
        
        results = {
            "public": {},
            "private": {}
        }
        
        try:
            # Check public tables
            public_tables = self.config.get("routing", {}).get("public_tables", [])
            for table in public_tables:
                exists = await self.db_manager.check_table_exists(
                    table,
                    DatabaseType.PUBLIC
                )
                results["public"][table] = exists
                
            # Check private tables
            private_tables = self.config.get("routing", {}).get("phi_tables", [])
            for table in private_tables:
                exists = await self.db_manager.check_table_exists(
                    table,
                    DatabaseType.PRIVATE
                )
                results["private"][table] = exists
                
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to check tables: {e}")
            raise
            
    async def run_migrations(self, migration_dir: str = None):
        """Run database migrations"""
        await self.initialize()
        
        migration_path = Path(migration_dir) if migration_dir else (
            self.schema_path / "migrations"
        )
        
        if not migration_path.exists():
            self.logger.info("No migrations directory found")
            return
            
        try:
            # Get list of migration files
            migrations = sorted([
                f for f in migration_path.glob("*.sql")
                if f.is_file()
            ])
            
            if not migrations:
                self.logger.info("No migration files found")
                return
                
            # Check if migrations table exists
            await self._ensure_migrations_table()
            
            # Apply each migration
            for migration_file in migrations:
                migration_name = migration_file.name
                
                # Check if already applied
                if await self._is_migration_applied(migration_name):
                    self.logger.debug(f"Migration already applied: {migration_name}")
                    continue
                    
                # Apply migration
                await self._apply_migration(migration_file)
                
                # Record migration
                await self._record_migration(migration_name)
                
                self.logger.info(f"Applied migration: {migration_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to run migrations: {e}")
            raise
            
    async def _ensure_migrations_table(self):
        """Ensure migrations tracking table exists"""
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        # Create in both databases
        await self.db_manager.execute(
            create_table_sql,
            database=DatabaseType.PUBLIC,
            user_id="system"
        )
        
        await self.db_manager.execute(
            create_table_sql,
            database=DatabaseType.PRIVATE,
            user_id="system"
        )
        
    async def _is_migration_applied(self, migration_name: str) -> bool:
        """Check if a migration has been applied"""
        check_sql = """
            SELECT EXISTS (
                SELECT 1 FROM schema_migrations 
                WHERE migration_name = $1
            )
        """
        
        # Check in public database (migrations tracked there)
        return await self.db_manager.fetchval(
            check_sql,
            migration_name,
            database=DatabaseType.PUBLIC,
            user_id="system"
        )
        
    async def _apply_migration(self, migration_file: Path):
        """Apply a migration file"""
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
            
        # Determine target database from migration name or content
        if "private" in migration_file.name.lower() or "-- DATABASE: private" in migration_sql:
            database = DatabaseType.PRIVATE
        else:
            database = DatabaseType.PUBLIC
            
        # Split and execute statements
        statements = [
            stmt.strip() 
            for stmt in migration_sql.split(';') 
            if stmt.strip()
        ]
        
        for statement in statements:
            if statement:
                await self.db_manager.execute(
                    statement + ';',
                    database=database,
                    user_id="system"
                )
                
    async def _record_migration(self, migration_name: str):
        """Record that a migration has been applied"""
        record_sql = """
            INSERT INTO schema_migrations (migration_name)
            VALUES ($1)
            ON CONFLICT (migration_name) DO NOTHING
        """
        
        await self.db_manager.execute(
            record_sql,
            migration_name,
            database=DatabaseType.PUBLIC,
            user_id="system"
        )
        
    async def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information"""
        await self.initialize()
        
        info = {
            "configuration": {
                "public": self.config["databases"]["public"],
                "private": self.config["databases"]["private"]
            },
            "databases_exist": await self.check_databases_exist(),
            "tables_exist": await self.check_tables_exist(),
            "connection_pools": await self.db_manager.get_pool_stats(),
            "security": self.config.get("security", {})
        }
        
        return info
        
    async def validate_configuration(self) -> List[str]:
        """Validate database configuration"""
        issues = []
        
        # Check required configuration sections
        if "databases" not in self.config:
            issues.append("Missing 'databases' section in configuration")
            
        if "public" not in self.config.get("databases", {}):
            issues.append("Missing public database configuration")
            
        if "private" not in self.config.get("databases", {}):
            issues.append("Missing private database configuration")
            
        # Check security settings
        security = self.config.get("security", {})
        if not security.get("audit_all_phi_access"):
            issues.append("PHI access auditing is disabled")
            
        if not security.get("private_db_encryption"):
            issues.append("Private database encryption settings missing")
            
        # Check environment variables
        required_env = [
            "PUBLIC_DB_PASSWORD",
            "PRIVATE_DB_PASSWORD",
            "DB_ENCRYPTION_KEY"
        ]
        
        for env_var in required_env:
            if not os.getenv(env_var):
                issues.append(f"Required environment variable not set: {env_var}")
                
        return issues
        
    async def initialize_databases(self):
        """Full database initialization process"""
        self.logger.info("Starting database initialization")
        
        try:
            # Validate configuration
            issues = await self.validate_configuration()
            if issues:
                for issue in issues:
                    self.logger.warning(f"Configuration issue: {issue}")
                    
            # Create databases if needed
            await self.create_databases()
            
            # Apply schemas
            await self.apply_schemas()
            
            # Run migrations
            await self.run_migrations()
            
            # Verify setup
            info = await self.get_database_info()
            
            self.logger.info("Database initialization complete")
            return info
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise


# CLI interface for database management
async def main():
    """CLI for database management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Healthcare Database Manager")
    parser.add_argument(
        "command",
        choices=["init", "check", "migrate", "info", "validate"],
        help="Command to execute"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default=None
    )
    
    args = parser.parse_args()
    
    # Create manager
    manager = DatabaseConfigManager(args.config)
    
    try:
        if args.command == "init":
            result = await manager.initialize_databases()
            print("Database initialization complete")
            print(f"Databases: {result['databases_exist']}")
            
        elif args.command == "check":
            databases = await manager.check_databases_exist()
            tables = await manager.check_tables_exist()
            print(f"Databases exist: {databases}")
            print(f"Tables exist: {tables}")
            
        elif args.command == "migrate":
            await manager.run_migrations()
            print("Migrations complete")
            
        elif args.command == "info":
            info = await manager.get_database_info()
            print(yaml.dump(info, default_flow_style=False))
            
        elif args.command == "validate":
            issues = await manager.validate_configuration()
            if issues:
                print("Configuration issues found:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("Configuration is valid")
                
    except Exception as e:
        print(f"Error: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))