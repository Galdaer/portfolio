import fetch from 'node-fetch';
import { DatabaseManager } from '../../utils/DatabaseManager.js';
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
    private dbManager: DatabaseManager;

    constructor(apiKey?: string, dbManager?: DatabaseManager) {
        this.apiKey = apiKey;
        this.dbManager = dbManager || DatabaseManager.fromEnvironment();
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
            // DATABASE-FIRST: Return database results immediately, test external APIs in background
            if (this.dbManager.isAvailable()) {
                console.log('Searching clinical trials in PostgreSQL database');
                const dbResults = await this.searchDatabase(condition, location, maxResults);

                // Start background validation of external API (don't await)
                this.validateExternalAPI(condition, location).catch(error => {
                    console.warn('Background external API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.length} trials, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to external ClinicalTrials API');
                return await this.searchExternalAPI(condition, location);
            }

            throw new Error('Neither database nor external API available for clinical trials search');
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
        try {

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

            // Use full-text search if available, otherwise fall back to ILIKE
            const query = `
                SELECT 
                    COALESCE(nct_id, nctid) AS nct_id,
                    title,
                    COALESCE(status, overall_status) AS status,
                    phase,
                    conditions,
                    locations,
                    COALESCE(last_updated, last_update_post_date) AS last_updated,
                    COALESCE(ts_rank_cd(search_vector, plainto_tsquery('english', $1)), 0) as rank
                FROM clinical_trials
                WHERE (search_vector @@ plainto_tsquery('english', $1) OR ${where})
                ORDER BY rank DESC, COALESCE(last_updated, last_update_post_date) DESC NULLS LAST
                LIMIT $${idx}
            `;

            const result = await this.dbManager.query(query, params);

            console.log(`Database search returned ${result.rows.length} clinical trials`);

            return result.rows.map((row: any) => ({
                nctId: row.nct_id || '',
                title: row.title || '',
                status: row.status || '',
                phase: row.phase || '',
                conditions: Array.isArray(row.conditions) ? row.conditions : (row.conditions ? [row.conditions] : []),
                locations: Array.isArray(row.locations) ? row.locations : (row.locations ? [row.locations] : []),
                lastUpdated: row.last_updated || ''
            }));

        } catch (error) {
            console.error('Database search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
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