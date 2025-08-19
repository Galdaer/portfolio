import fetch from 'node-fetch';
import { Client } from 'pg';
import { CacheManager } from "../../utils/Cache.js";

export interface ClinicalTrial {
    nctId: string;
    title: string;
    status: string;
    phase: string;
    conditions: string[];
    locations: string[];
    lastUpdated: string;
}

interface ClinicalTrialsResponse {
    studies: ClinicalTrial[];
}

export class ClinicalTrials {
    private readonly baseUrl = 'https://clinicaltrials.gov/api/v2/studies';
    private readonly apiKey?: string;

    constructor(apiKey?: string) {
        this.apiKey = apiKey;
    }

    async getTrials(args: any, cache: CacheManager) {
        const { condition, location } = args;
        const maxResults = Math.max(1, Math.min(100, Number(args?.maxResults ?? 25)));
        const cacheKey = cache.createKey('trials', { condition, location });

        const trials = await cache.getOrFetch(
            cacheKey,
            () => this.searchTrials(condition, location, maxResults)
        );

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({ results: trials })
            }]
        };
    }

    // Add search method for direct calls
    async search(params: any): Promise<ClinicalTrial[]> {
        const maxResults = Math.max(1, Math.min(100, Number(params?.maxResults ?? 25)));
        return this.searchTrials(params.condition, params.location, maxResults);
    }

    async searchTrials(condition: string, location?: string, maxResults: number = 25): Promise<ClinicalTrial[]> {
        try {
            // DATABASE-FIRST: Prefer local Postgres mirror
            try {
                console.log('Searching local PostgreSQL database for ClinicalTrials studies');
                const dbResults = await this.searchDatabase(condition, location, maxResults);
                // Optionally kick off background external validation
                this.validateExternalAPI(condition, location).catch(err => console.warn('Background ClinicalTrials external API validation failed:', err));
                console.log(`Database returned ${dbResults.length} trials, background external validation started`);
                return dbResults;
            } catch (dbError) {
                console.warn('ClinicalTrials DB search failed, falling back to external API:', dbError);
                // As a conservative fallback, use external API
                return await this.searchExternalAPI(condition, location);
            }
        } catch (error) {
            console.error('ClinicalTrials search failed:', error);
            throw error;
        }
    }

    /**
     * Background validation of external ClinicalTrials API connectivity
     */
    private async validateExternalAPI(condition: string, location?: string): Promise<void> {
        const timeout = 10000; // 10 second timeout for background checks

        try {
            console.log('[BACKGROUND] Testing external ClinicalTrials API connectivity...');

            const externalPromise = Promise.race([
                this.searchExternalAPI(condition, location),
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('External ClinicalTrials API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ External ClinicalTrials API healthy - returned ${externalResults.length} trials`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  External ClinicalTrials API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
        }
    }

    private async searchDatabase(condition: string, location?: string, maxResults: number = 25): Promise<ClinicalTrial[]> {
        // Prefer single DATABASE_URL; fall back to discrete vars WITHOUT secrets defaults.
        const databaseUrl = process.env.DATABASE_URL?.trim();

        let client: Client;
        if (databaseUrl && databaseUrl.length > 0) {
            client = new Client({ connectionString: databaseUrl });
        } else {
            const host = process.env.POSTGRES_HOST;
            const portVal = process.env.POSTGRES_PORT;
            const user = process.env.POSTGRES_USER;
            const password = process.env.POSTGRES_PASSWORD;
            const database = process.env.DATABASE_NAME;

            if (!host || !user || !password || !database) {
                throw new Error("Database configuration missing. Provide DATABASE_URL or POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_NAME in environment.");
            }

            const port = portVal ? parseInt(portVal, 10) : 5432;
            client = new Client({ host, port, user, password, database });
        }

        const table = process.env.CLINICAL_TRIALS_TABLE || 'clinical_trials';

        await client.connect();

        // Build flexible search across common fields; location filter optional
        const params: any[] = [];
        let idx = 1;
        const likeCond = `%${condition}%`;
        params.push(likeCond);

        let where = `(title ILIKE $${idx} OR COALESCE(conditions::text,'') ILIKE $${idx})`;

        if (location && location.trim()) {
            idx += 1;
            params.push(`%${location}%`);
            where += ` AND (COALESCE(locations::text,'') ILIKE $${idx})`;
        }

        idx += 1;
        params.push(maxResults);

        const query = `
            SELECT 
                COALESCE(nct_id, nctid) AS nct_id,
                title,
                COALESCE(status, overall_status) AS status,
                phase,
                conditions,
                locations,
                COALESCE(last_updated, last_update_post_date) AS last_updated
            FROM ${table}
            WHERE ${where}
            ORDER BY COALESCE(last_updated, last_update_post_date) DESC NULLS LAST
            LIMIT $${idx}
        `;

        const result = await client.query(query, params);

        await client.end();

        return result.rows.map((row: any) => ({
            nctId: row.nct_id || '',
            title: row.title || '',
            status: row.status || '',
            phase: row.phase || '',
            conditions: Array.isArray(row.conditions) ? row.conditions : (row.conditions ? [row.conditions] : []),
            locations: Array.isArray(row.locations) ? row.locations : (row.locations ? [row.locations] : []),
            lastUpdated: row.last_updated || ''
        }));
    }

    private async searchExternalAPI(condition: string, location?: string): Promise<ClinicalTrial[]> {
        const url = new URL(this.baseUrl);
        url.searchParams.append('query.cond', condition);
        // url.searchParams.append('fields', 'NCTId,BriefTitle,OverallStatus,Phase,Condition,LocationFacility,LastUpdatePostDate');

        const response = await fetch(url);
        const data = await response.json() as ClinicalTrialsResponse;

        return data.studies;
    }
}