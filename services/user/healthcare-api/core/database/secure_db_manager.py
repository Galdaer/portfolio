"""
Secure Database Manager with PHI Protection
Manages connections to both public and private databases with proper security controls
"""

import asyncio
import hashlib
import os
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any

import asyncpg
import yaml
from cryptography.fernet import Fernet

from core.infrastructure.healthcare_logger import get_healthcare_logger
from core.infrastructure.phi_detector import PHIDetector


class DatabaseType(Enum):
    """Database type enumeration"""
    PUBLIC = "public"
    PRIVATE = "private"


class QueryType(Enum):
    """Query type for routing and auditing"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DDL = "DDL"
    TRANSACTION = "TRANSACTION"


class SecureDatabaseManager:
    """
    Manages secure connections to public and private databases
    with PHI protection, audit logging, and query routing
    """

    def __init__(self, config_path: str = None):
        """Initialize the secure database manager"""
        self.logger = get_healthcare_logger("database.secure_manager")
        self.phi_detector = PHIDetector()

        # Load configuration
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__),
            "../../config/database_config.yml",
        )
        self.config = self._load_config()

        # Connection pools
        self.public_pool: asyncpg.Pool | None = None
        self.private_pool: asyncpg.Pool | None = None

        # Encryption for sensitive data
        self.cipher_suite = self._initialize_encryption()

        # Audit configuration
        self.audit_enabled = self.config.get("security", {}).get("audit_all_phi_access", True)

        # Query routing rules
        self.phi_tables = set(self.config.get("routing", {}).get("phi_tables", []))
        self.public_tables = set(self.config.get("routing", {}).get("public_tables", []))

    def _load_config(self) -> dict[str, Any]:
        """Load database configuration from YAML file"""
        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            # Override with environment variables
            env = os.getenv("ENVIRONMENT", "development")
            if env in config.get("environments", {}):
                env_config = config["environments"][env]
                for db_type, db_config in env_config.get("databases", {}).items():
                    config["databases"][db_type].update(db_config)

            return config
        except Exception as e:
            self.logger.exception(f"Failed to load database configuration: {e}")
            raise

    def _initialize_encryption(self) -> Fernet:
        """Initialize encryption for sensitive data"""
        # Get or generate encryption key
        key = os.getenv("DB_ENCRYPTION_KEY")
        if not key:
            # Generate a new key for development (should be provided in production)
            key = Fernet.generate_key().decode()
            self.logger.warning("Generated new encryption key - provide DB_ENCRYPTION_KEY in production")

        return Fernet(key.encode() if isinstance(key, str) else key)

    async def initialize(self):
        """Initialize database connection pools"""
        try:
            # Create public database pool
            public_config = self.config["databases"]["public"]
            self.public_pool = await asyncpg.create_pool(
                host=os.getenv("PUBLIC_DB_HOST") or public_config.get("host", "localhost"),
                port=int(os.getenv("PUBLIC_DB_PORT") or public_config.get("port", 5432)),
                user=os.getenv("PUBLIC_DB_USER") or public_config.get("user", "intelluxe"),
                password=os.getenv("PUBLIC_DB_PASSWORD") or public_config.get("password", "secure_password"),
                database=public_config.get("name", "intelluxe_public"),
                min_size=public_config.get("min_pool_size", 5),
                max_size=public_config.get("max_pool_size", 50),
                command_timeout=public_config.get("timeout", 30),
                ssl=None,  # Disable SSL for local development
            )

            # Create private database pool with enhanced security
            private_config = self.config["databases"]["private"]
            self.private_pool = await asyncpg.create_pool(
                host=os.getenv("PRIVATE_DB_HOST") or private_config.get("host", "localhost"),
                port=int(os.getenv("PRIVATE_DB_PORT") or private_config.get("port", 5432)),
                user=os.getenv("PRIVATE_DB_USER") or private_config.get("user", "intelluxe"),
                password=os.getenv("PRIVATE_DB_PASSWORD") or private_config.get("password", "secure_password"),
                database=private_config.get("name", "intelluxe_clinical"),
                min_size=private_config.get("min_pool_size", 2),
                max_size=private_config.get("max_pool_size", 25),
                command_timeout=private_config.get("timeout", 30),
                ssl=None,  # Disable SSL for local development (enable in production)
            )

            self.logger.info("Database pools initialized successfully")

            # Test connections
            await self._test_connections()

        except Exception as e:
            self.logger.exception(f"Failed to initialize database pools: {e}")
            raise

    async def _test_connections(self):
        """Test database connections"""
        try:
            # Test public database
            async with self.public_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                assert result == 1
                self.logger.info("Public database connection successful")

            # Test private database
            async with self.private_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                assert result == 1
                self.logger.info("Private database connection successful")

        except Exception as e:
            self.logger.exception(f"Database connection test failed: {e}")
            raise

    async def close(self):
        """Close database connection pools"""
        if self.public_pool:
            await self.public_pool.close()
        if self.private_pool:
            await self.private_pool.close()
        self.logger.info("Database pools closed")

    def _determine_database(self, query: str, tables: list[str] = None) -> DatabaseType:
        """
        Determine which database to use based on query and tables

        Args:
            query: SQL query string
            tables: Optional list of table names involved

        Returns:
            DatabaseType indicating which database to use
        """
        # If tables are explicitly provided, check them
        if tables:
            for table in tables:
                if table.lower() in self.phi_tables:
                    return DatabaseType.PRIVATE

        # Parse query to find table names
        query_lower = query.lower()

        # Check for PHI tables in query
        for phi_table in self.phi_tables:
            if phi_table.lower() in query_lower:
                return DatabaseType.PRIVATE

        # Check for explicit public tables
        for public_table in self.public_tables:
            if public_table.lower() in query_lower:
                return DatabaseType.PUBLIC

        # Default to public for safety (no PHI access by default)
        return DatabaseType.PUBLIC

    def _classify_query(self, query: str) -> QueryType:
        """Classify the type of query for auditing"""
        query_upper = query.strip().upper()

        if query_upper.startswith("SELECT"):
            return QueryType.SELECT
        if query_upper.startswith("INSERT"):
            return QueryType.INSERT
        if query_upper.startswith("UPDATE"):
            return QueryType.UPDATE
        if query_upper.startswith("DELETE"):
            return QueryType.DELETE
        if any(query_upper.startswith(ddl) for ddl in ["CREATE", "ALTER", "DROP"]):
            return QueryType.DDL
        if query_upper.startswith(("BEGIN", "COMMIT", "ROLLBACK")):
            return QueryType.TRANSACTION
        return QueryType.SELECT  # Default

    async def _audit_query(
        self,
        database: DatabaseType,
        query: str,
        query_type: QueryType,
        user_id: str = None,
        session_id: str = None,
        success: bool = True,
        error: str = None,
        rows_affected: int = None,
    ):
        """Log query execution for audit purposes"""
        if not self.audit_enabled:
            return

        # Only audit PHI database queries or failed queries
        if database != DatabaseType.PRIVATE and success:
            return

        try:
            audit_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "database": database.value,
                "query_type": query_type.value,
                "user_id": user_id or "system",
                "session_id": session_id,
                "query_hash": hashlib.sha256(query.encode()).hexdigest(),
                "success": success,
                "error": error,
                "rows_affected": rows_affected,
            }

            # Log to audit system (could be database, file, or external service)
            if database == DatabaseType.PRIVATE:
                # Store in phi_access_audit table
                async with self.private_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO phi_access_audit
                        (user_id, session_id, access_type, query_hash,
                         success, error_message, rows_affected)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, user_id or "system", session_id, query_type.value,
                    audit_data["query_hash"], success, error, rows_affected)

            # Also log to application logs
            if success:
                self.logger.info(f"Database query audit: {audit_data}")
            else:
                self.logger.warning(f"Failed database query: {audit_data}")

        except Exception as e:
            self.logger.exception(f"Failed to audit query: {e}")

    def _sanitize_params(self, params: tuple[Any, ...]) -> tuple[Any, ...]:
        """
        Sanitize parameters to remove potential PHI before logging

        Args:
            params: Query parameters

        Returns:
            Sanitized parameters safe for logging
        """
        if not params:
            return params

        sanitized = []
        for param in params:
            if isinstance(param, str):
                # Check for PHI in string parameters
                if self.phi_detector.contains_phi(param):
                    sanitized.append("[REDACTED-PHI]")
                else:
                    sanitized.append(param)
            elif isinstance(param, dict | list):
                # Redact complex structures that might contain PHI
                sanitized.append("[REDACTED-STRUCTURE]")
            else:
                # Keep non-sensitive data types
                sanitized.append(param)

        return tuple(sanitized)

    @asynccontextmanager
    async def transaction(
        self,
        database: DatabaseType = DatabaseType.PUBLIC,
        user_id: str = None,
        session_id: str = None,
    ):
        """
        Create a database transaction context

        Args:
            database: Which database to use
            user_id: User ID for audit logging
            session_id: Session ID for audit logging

        Yields:
            Database connection with transaction
        """
        pool = self.private_pool if database == DatabaseType.PRIVATE else self.public_pool

        if not pool:
            msg = f"{database.value} database pool not initialized"
            raise RuntimeError(msg)

        async with pool.acquire() as conn, conn.transaction():
            # Log transaction start
            await self._audit_query(
                database, "BEGIN TRANSACTION", QueryType.TRANSACTION,
                user_id, session_id,
            )

            try:
                yield conn

                # Log successful transaction
                await self._audit_query(
                    database, "COMMIT TRANSACTION", QueryType.TRANSACTION,
                    user_id, session_id,
                )
            except Exception as e:
                # Log failed transaction
                await self._audit_query(
                    database, "ROLLBACK TRANSACTION", QueryType.TRANSACTION,
                    user_id, session_id, success=False, error=str(e),
                )
                raise

    async def execute(
        self,
        query: str,
        *params,
        database: DatabaseType = None,
        tables: list[str] = None,
        user_id: str = None,
        session_id: str = None,
        timeout: float = None,
    ) -> str:
        """
        Execute a query on the appropriate database

        Args:
            query: SQL query to execute
            params: Query parameters
            database: Optional database specification
            tables: Optional list of tables for routing
            user_id: User ID for audit logging
            session_id: Session ID for audit logging
            timeout: Query timeout in seconds

        Returns:
            Query result status
        """
        # Determine database if not specified
        if database is None:
            database = self._determine_database(query, tables)

        # Select appropriate pool
        pool = self.private_pool if database == DatabaseType.PRIVATE else self.public_pool

        if not pool:
            msg = f"{database.value} database pool not initialized"
            raise RuntimeError(msg)

        # Classify query type
        query_type = self._classify_query(query)

        # Sanitize parameters for logging
        safe_params = self._sanitize_params(params)

        try:
            async with pool.acquire() as conn:
                if timeout:
                    result = await asyncio.wait_for(
                        conn.execute(query, *params),
                        timeout=timeout,
                    )
                else:
                    result = await conn.execute(query, *params)

                # Extract rows affected
                rows_affected = int(result.split()[-1]) if result else None

                # Audit successful query
                await self._audit_query(
                    database, query, query_type, user_id, session_id,
                    rows_affected=rows_affected,
                )

                self.logger.debug(
                    f"Executed {query_type.value} on {database.value} database",
                    extra={"safe_params": safe_params, "rows_affected": rows_affected},
                )

                return result

        except TimeoutError:
            error = f"Query timeout after {timeout} seconds"
            await self._audit_query(
                database, query, query_type, user_id, session_id,
                success=False, error=error,
            )
            raise
        except Exception as e:
            await self._audit_query(
                database, query, query_type, user_id, session_id,
                success=False, error=str(e),
            )
            self.logger.exception(
                f"Query execution failed: {e}",
                extra={"query_type": query_type.value, "database": database.value},
            )
            raise

    async def fetch(
        self,
        query: str,
        *params,
        database: DatabaseType = None,
        tables: list[str] = None,
        user_id: str = None,
        session_id: str = None,
        timeout: float = None,
    ) -> list[asyncpg.Record]:
        """
        Fetch multiple rows from the appropriate database

        Args:
            query: SQL SELECT query
            params: Query parameters
            database: Optional database specification
            tables: Optional list of tables for routing
            user_id: User ID for audit logging
            session_id: Session ID for audit logging
            timeout: Query timeout in seconds

        Returns:
            List of records
        """
        # Determine database if not specified
        if database is None:
            database = self._determine_database(query, tables)

        # Select appropriate pool
        pool = self.private_pool if database == DatabaseType.PRIVATE else self.public_pool

        if not pool:
            msg = f"{database.value} database pool not initialized"
            raise RuntimeError(msg)

        # Sanitize parameters for logging
        safe_params = self._sanitize_params(params)

        try:
            async with pool.acquire() as conn:
                if timeout:
                    rows = await asyncio.wait_for(
                        conn.fetch(query, *params),
                        timeout=timeout,
                    )
                else:
                    rows = await conn.fetch(query, *params)

                # Audit successful query
                await self._audit_query(
                    database, query, QueryType.SELECT, user_id, session_id,
                    rows_affected=len(rows),
                )

                self.logger.debug(
                    f"Fetched {len(rows)} rows from {database.value} database",
                    extra={"safe_params": safe_params},
                )

                return rows

        except TimeoutError:
            error = f"Query timeout after {timeout} seconds"
            await self._audit_query(
                database, query, QueryType.SELECT, user_id, session_id,
                success=False, error=error,
            )
            raise
        except Exception as e:
            await self._audit_query(
                database, query, QueryType.SELECT, user_id, session_id,
                success=False, error=str(e),
            )
            self.logger.exception(
                f"Query fetch failed: {e}",
                extra={"database": database.value},
            )
            raise

    async def fetchrow(
        self,
        query: str,
        *params,
        database: DatabaseType = None,
        tables: list[str] = None,
        user_id: str = None,
        session_id: str = None,
        timeout: float = None,
    ) -> asyncpg.Record | None:
        """
        Fetch a single row from the appropriate database

        Args:
            query: SQL SELECT query
            params: Query parameters
            database: Optional database specification
            tables: Optional list of tables for routing
            user_id: User ID for audit logging
            session_id: Session ID for audit logging
            timeout: Query timeout in seconds

        Returns:
            Single record or None
        """
        # Determine database if not specified
        if database is None:
            database = self._determine_database(query, tables)

        # Select appropriate pool
        pool = self.private_pool if database == DatabaseType.PRIVATE else self.public_pool

        if not pool:
            msg = f"{database.value} database pool not initialized"
            raise RuntimeError(msg)

        # Sanitize parameters for logging
        safe_params = self._sanitize_params(params)

        try:
            async with pool.acquire() as conn:
                if timeout:
                    row = await asyncio.wait_for(
                        conn.fetchrow(query, *params),
                        timeout=timeout,
                    )
                else:
                    row = await conn.fetchrow(query, *params)

                # Audit successful query
                await self._audit_query(
                    database, query, QueryType.SELECT, user_id, session_id,
                    rows_affected=1 if row else 0,
                )

                self.logger.debug(
                    f"Fetched {'1 row' if row else 'no rows'} from {database.value} database",
                    extra={"safe_params": safe_params},
                )

                return row

        except TimeoutError:
            error = f"Query timeout after {timeout} seconds"
            await self._audit_query(
                database, query, QueryType.SELECT, user_id, session_id,
                success=False, error=error,
            )
            raise
        except Exception as e:
            await self._audit_query(
                database, query, QueryType.SELECT, user_id, session_id,
                success=False, error=str(e),
            )
            self.logger.exception(
                f"Query fetchrow failed: {e}",
                extra={"database": database.value},
            )
            raise

    async def fetchval(
        self,
        query: str,
        *params,
        column: int = 0,
        database: DatabaseType = None,
        tables: list[str] = None,
        user_id: str = None,
        session_id: str = None,
        timeout: float = None,
    ) -> Any:
        """
        Fetch a single value from the appropriate database

        Args:
            query: SQL SELECT query
            params: Query parameters
            column: Column index to fetch
            database: Optional database specification
            tables: Optional list of tables for routing
            user_id: User ID for audit logging
            session_id: Session ID for audit logging
            timeout: Query timeout in seconds

        Returns:
            Single value or None
        """
        # Determine database if not specified
        if database is None:
            database = self._determine_database(query, tables)

        # Select appropriate pool
        pool = self.private_pool if database == DatabaseType.PRIVATE else self.public_pool

        if not pool:
            msg = f"{database.value} database pool not initialized"
            raise RuntimeError(msg)

        # Sanitize parameters for logging
        safe_params = self._sanitize_params(params)

        try:
            async with pool.acquire() as conn:
                if timeout:
                    value = await asyncio.wait_for(
                        conn.fetchval(query, *params, column=column),
                        timeout=timeout,
                    )
                else:
                    value = await conn.fetchval(query, *params, column=column)

                # Audit successful query
                await self._audit_query(
                    database, query, QueryType.SELECT, user_id, session_id,
                    rows_affected=1 if value is not None else 0,
                )

                self.logger.debug(
                    f"Fetched value from {database.value} database",
                    extra={"safe_params": safe_params, "has_value": value is not None},
                )

                return value

        except TimeoutError:
            error = f"Query timeout after {timeout} seconds"
            await self._audit_query(
                database, query, QueryType.SELECT, user_id, session_id,
                success=False, error=error,
            )
            raise
        except Exception as e:
            await self._audit_query(
                database, query, QueryType.SELECT, user_id, session_id,
                success=False, error=str(e),
            )
            self.logger.exception(
                f"Query fetchval failed: {e}",
                extra={"database": database.value},
            )
            raise

    def encrypt_sensitive_data(self, data: str) -> bytes:
        """
        Encrypt sensitive data for storage

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data
        """
        return self.cipher_suite.encrypt(data.encode())

    def decrypt_sensitive_data(self, encrypted_data: bytes) -> str:
        """
        Decrypt sensitive data from storage

        Args:
            encrypted_data: Encrypted data

        Returns:
            Decrypted data
        """
        return self.cipher_suite.decrypt(encrypted_data).decode()

    async def check_table_exists(
        self,
        table_name: str,
        database: DatabaseType = DatabaseType.PUBLIC,
    ) -> bool:
        """
        Check if a table exists in the specified database

        Args:
            table_name: Name of the table
            database: Which database to check

        Returns:
            True if table exists, False otherwise
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = $1
            )
        """

        return await self.fetchval(
            query, table_name,
            database=database,
            user_id="system",
        )

    async def get_pool_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get connection pool statistics

        Returns:
            Dictionary with pool statistics for each database
        """
        stats = {}

        if self.public_pool:
            stats["public"] = {
                "size": self.public_pool.get_size(),
                "free": self.public_pool.get_idle_size(),
                "used": self.public_pool.get_size() - self.public_pool.get_idle_size(),
                "max_size": self.public_pool.get_max_size(),
                "min_size": self.public_pool.get_min_size(),
            }

        if self.private_pool:
            stats["private"] = {
                "size": self.private_pool.get_size(),
                "free": self.private_pool.get_idle_size(),
                "used": self.private_pool.get_size() - self.private_pool.get_idle_size(),
                "max_size": self.private_pool.get_max_size(),
                "min_size": self.private_pool.get_min_size(),
            }

        return stats


# Singleton instance
_db_manager: SecureDatabaseManager | None = None


async def get_db_manager() -> SecureDatabaseManager:
    """Get or create the database manager singleton"""
    global _db_manager

    if _db_manager is None:
        _db_manager = SecureDatabaseManager()
        await _db_manager.initialize()

    return _db_manager


async def close_db_manager():
    """Close the database manager singleton"""
    global _db_manager

    if _db_manager:
        await _db_manager.close()
        _db_manager = None
