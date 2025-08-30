/**
 * Base Database Connector for Medical Data Sources
 * Provides common database operations for all medical connectors
 */

import { Pool } from 'pg';

export interface QueryResult {
    rows: any[];
    rowCount: number;
}

export abstract class DatabaseConnector {
    protected pool: Pool | null = null;
    protected readonly tableName: string;
    protected readonly searchableColumns: string[];

    constructor(tableName: string, searchableColumns: string[] = []) {
        this.tableName = tableName;
        this.searchableColumns = searchableColumns;
        this.initializePool();
    }

    /**
     * Initialize PostgreSQL connection pool
     */
    protected initializePool(): void {
        const config = {
            host: process.env.POSTGRES_HOST || 'localhost',
            port: parseInt(process.env.POSTGRES_PORT || '5432'),
            database: process.env.POSTGRES_DB || 'intelluxe_public',
            user: process.env.POSTGRES_USER || 'intelluxe',
            password: process.env.POSTGRES_PASSWORD || 'secure_password',
            max: 20,
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 2000,
        };

        this.pool = new Pool(config);
    }

    /**
     * Execute a database query with parameters
     */
    protected async executeQuery(query: string, params: any[] = []): Promise<QueryResult> {
        if (!this.pool) {
            throw new Error('Database pool not initialized');
        }

        try {
            const result = await this.pool.query(query, params);
            return {
                rows: result.rows,
                rowCount: result.rowCount || 0
            };
        } catch (error) {
            console.error('Database query error:', error);
            throw new Error(`Database query failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    /**
     * Search for records in the database
     */
    async search(searchTerm: string, limit: number = 10): Promise<any[]> {
        if (!searchTerm || searchTerm.trim().length === 0) {
            return [];
        }

        const searchPattern = `%${searchTerm}%`;
        const conditions = this.searchableColumns.map(
            (col, index) => `${col} ILIKE $${index + 2}`
        ).join(' OR ');

        const query = `
            SELECT * FROM ${this.tableName}
            WHERE ${conditions}
            LIMIT $1
        `;

        const params = [limit, ...this.searchableColumns.map(() => searchPattern)];
        const result = await this.executeQuery(query, params);
        return result.rows;
    }

    /**
     * Get a record by ID
     */
    async getById(id: string | number, idColumn: string = 'id'): Promise<any | null> {
        const query = `SELECT * FROM ${this.tableName} WHERE ${idColumn} = $1 LIMIT 1`;
        const result = await this.executeQuery(query, [id]);
        return result.rows.length > 0 ? result.rows[0] : null;
    }

    /**
     * Get multiple records with pagination
     */
    async getMany(offset: number = 0, limit: number = 10): Promise<any[]> {
        const query = `SELECT * FROM ${this.tableName} LIMIT $1 OFFSET $2`;
        const result = await this.executeQuery(query, [limit, offset]);
        return result.rows;
    }

    /**
     * Count total records
     */
    async count(): Promise<number> {
        const query = `SELECT COUNT(*) as total FROM ${this.tableName}`;
        const result = await this.executeQuery(query);
        return parseInt(result.rows[0]?.total || '0');
    }

    /**
     * Check if database is connected
     */
    async isConnected(): Promise<boolean> {
        try {
            if (!this.pool) return false;
            const result = await this.pool.query('SELECT 1');
            return (result.rowCount ?? 0) > 0;
        } catch {
            return false;
        }
    }

    /**
     * Close database connection
     */
    async close(): Promise<void> {
        if (this.pool) {
            await this.pool.end();
            this.pool = null;
        }
    }
}

export default DatabaseConnector;