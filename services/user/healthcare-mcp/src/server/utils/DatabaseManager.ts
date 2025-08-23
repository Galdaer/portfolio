import { Pool, Client, PoolClient } from 'pg';
import { promisify } from 'util';

export interface DatabaseConfig {
    postgresUrl: string;
    poolSize: number;
    timeoutMs: number;
    useDatabaseMirror: boolean;
    fallbackToExternalApi: boolean;
}

export interface DatabaseStats {
    connectionStatus: 'connected' | 'disconnected' | 'error';
    activeConnections: number;
    totalConnections: number;
    lastHealthCheck: Date;
    tableStats: Record<string, number>;
    errorCount: number;
    lastError?: string;
}

/**
 * DatabaseManager handles PostgreSQL connection pooling and health management
 * for the healthcare MCP service with fallback support
 */
export class DatabaseManager {
    private pool: Pool | null = null;
    private config: DatabaseConfig;
    private stats: DatabaseStats;
    private healthCheckInterval: NodeJS.Timeout | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    constructor(config: DatabaseConfig) {
        this.config = config;
        this.stats = {
            connectionStatus: 'disconnected',
            activeConnections: 0,
            totalConnections: 0,
            lastHealthCheck: new Date(),
            tableStats: {},
            errorCount: 0
        };
        
        if (this.config.useDatabaseMirror) {
            this.initializePool();
            this.startHealthCheck();
        }
    }

    /**
     * Initialize PostgreSQL connection pool
     */
    private initializePool(): void {
        try {
            this.pool = new Pool({
                connectionString: this.config.postgresUrl,
                max: this.config.poolSize,
                idleTimeoutMillis: 30000,
                connectionTimeoutMillis: this.config.timeoutMs,
                statement_timeout: this.config.timeoutMs,
                query_timeout: this.config.timeoutMs
            });

            this.pool.on('connect', (client: PoolClient) => {
                this.stats.totalConnections++;
                this.stats.activeConnections++;
                console.log(`[DatabaseManager] New client connected. Total: ${this.stats.totalConnections}`);
            });

            this.pool.on('remove', (client: PoolClient) => {
                this.stats.activeConnections--;
                console.log(`[DatabaseManager] Client removed. Active: ${this.stats.activeConnections}`);
            });

            this.pool.on('error', (err: Error) => {
                console.error('[DatabaseManager] Pool error:', err.message);
                this.stats.errorCount++;
                this.stats.lastError = err.message;
                this.stats.connectionStatus = 'error';
            });

            console.log('[DatabaseManager] Connection pool initialized');
        } catch (error) {
            console.error('[DatabaseManager] Failed to initialize pool:', error);
            this.stats.connectionStatus = 'error';
            this.stats.lastError = error instanceof Error ? error.message : 'Unknown error';
        }
    }

    /**
     * Get a database client from the pool
     */
    async getClient(): Promise<PoolClient> {
        if (!this.pool || !this.config.useDatabaseMirror) {
            throw new Error('Database pool not initialized or database mirror disabled');
        }

        try {
            const client = await this.pool.connect();
            this.stats.connectionStatus = 'connected';
            return client;
        } catch (error) {
            this.stats.errorCount++;
            this.stats.lastError = error instanceof Error ? error.message : 'Connection failed';
            this.stats.connectionStatus = 'error';
            console.error('[DatabaseManager] Failed to get client:', error);
            throw error;
        }
    }

    /**
     * Execute a query with automatic connection management
     */
    async query<T = any>(text: string, params?: any[]): Promise<{ rows: T[]; rowCount: number }> {
        if (!this.isAvailable()) {
            throw new Error('Database not available');
        }

        const client = await this.getClient();
        try {
            const result = await client.query(text, params);
            return {
                rows: result.rows as T[],
                rowCount: result.rowCount || 0
            };
        } finally {
            client.release();
        }
    }

    /**
     * Check if database is available
     */
    isAvailable(): boolean {
        return this.config.useDatabaseMirror && 
               this.pool !== null && 
               this.stats.connectionStatus === 'connected';
    }

    /**
     * Check if fallback to external APIs is enabled
     */
    canFallback(): boolean {
        return this.config.fallbackToExternalApi;
    }

    /**
     * Perform health check on the database
     */
    async healthCheck(): Promise<boolean> {
        if (!this.pool || !this.config.useDatabaseMirror) {
            return false;
        }

        try {
            const client = await this.getClient();
            try {
                // Simple health check query
                await client.query('SELECT 1');
                
                // Get table statistics
                await this.updateTableStats(client);
                
                this.stats.connectionStatus = 'connected';
                this.stats.lastHealthCheck = new Date();
                this.reconnectAttempts = 0;
                
                console.log('[DatabaseManager] Health check passed');
                return true;
            } finally {
                client.release();
            }
        } catch (error) {
            console.error('[DatabaseManager] Health check failed:', error);
            this.stats.connectionStatus = 'error';
            this.stats.errorCount++;
            this.stats.lastError = error instanceof Error ? error.message : 'Health check failed';
            this.stats.lastHealthCheck = new Date();
            
            // Try to reconnect if we haven't exceeded max attempts
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`[DatabaseManager] Attempting reconnection (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                setTimeout(() => this.initializePool(), 5000 * this.reconnectAttempts);
            }
            
            return false;
        }
    }

    /**
     * Update table statistics for monitoring
     */
    private async updateTableStats(client: PoolClient): Promise<void> {
        try {
            const tables = [
                'pubmed_articles',
                'clinical_trials', 
                'fda_drugs',
                'icd10_codes',
                'billing_codes',
                'health_topics',
                'exercises',
                'food_items'
            ];

            for (const table of tables) {
                try {
                    const result = await client.query(
                        `SELECT COUNT(*) as count FROM ${table}`
                    );
                    this.stats.tableStats[table] = parseInt(result.rows[0].count);
                } catch (tableError) {
                    // Table might not exist yet, that's okay
                    this.stats.tableStats[table] = 0;
                }
            }
        } catch (error) {
            console.error('[DatabaseManager] Failed to update table stats:', error);
        }
    }

    /**
     * Start periodic health checks
     */
    private startHealthCheck(): void {
        // Initial health check
        this.healthCheck();
        
        // Periodic health checks every 60 seconds
        this.healthCheckInterval = setInterval(async () => {
            await this.healthCheck();
        }, 60000);
        
        console.log('[DatabaseManager] Health check monitoring started');
    }

    /**
     * Get current database statistics
     */
    getStats(): DatabaseStats {
        return { ...this.stats };
    }

    /**
     * Check if a specific table has data
     */
    async hasData(tableName: string): Promise<boolean> {
        if (!this.isAvailable()) {
            return false;
        }

        try {
            const result = await this.query(
                `SELECT COUNT(*) as count FROM ${tableName} LIMIT 1`
            );
            return parseInt(result.rows[0].count) > 0;
        } catch (error) {
            console.error(`[DatabaseManager] Error checking data in ${tableName}:`, error);
            return false;
        }
    }

    /**
     * Clean shutdown
     */
    async close(): Promise<void> {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }

        if (this.pool) {
            try {
                await this.pool.end();
                this.pool = null;
                this.stats.connectionStatus = 'disconnected';
                console.log('[DatabaseManager] Connection pool closed');
            } catch (error) {
                console.error('[DatabaseManager] Error closing pool:', error);
            }
        }
    }

    /**
     * Create a database manager instance from environment variables
     */
    static fromEnvironment(): DatabaseManager {
        const config: DatabaseConfig = {
            postgresUrl: process.env.POSTGRES_URL || 
                        'postgresql://intelluxe:secure_password@172.20.0.13:5432/intelluxe',
            poolSize: parseInt(process.env.DB_POOL_SIZE || '10'),
            timeoutMs: parseInt(process.env.DB_TIMEOUT_MS || '5000'),
            useDatabaseMirror: process.env.USE_DATABASE_MIRROR !== 'false',
            fallbackToExternalApi: process.env.FALLBACK_TO_EXTERNAL_API !== 'false'
        };

        console.log('[DatabaseManager] Initializing with config:', {
            ...config,
            postgresUrl: config.postgresUrl.replace(/\/\/[^:]+:[^@]+@/, '//***:***@') // Hide credentials in logs
        });

        return new DatabaseManager(config);
    }
}