import fetch from 'node-fetch';
import { DatabaseManager } from '../../utils/DatabaseManager.js';
import { CacheManager } from "../../utils/Cache.js";

export interface Generics {
    ndc: string;
    name: string;
    label: string;
    brand: string;
    ingredients: string[];
}

interface FDAResponse {
    results: Generics[];
}

export class FDA {
    private lastRequestTime = 0;
    private requestCount = 0;
    private readonly rateLimitWindow = 60000; // 1 minute
    private readonly maxRequestsPerMinute = 240;
    private readonly baseUrl = 'https://api.fda.gov/drug/ndc.json';
    private readonly apiKey?: string;
    private dbManager: DatabaseManager;

    private isRateLimited(): boolean {
        const now = Date.now();
        if (now - this.lastRequestTime > this.rateLimitWindow) {
            this.requestCount = 0;
            this.lastRequestTime = now;
        }
        this.requestCount++;
        return this.requestCount > this.maxRequestsPerMinute;
    }

    constructor(apiKey?: string, dbManager?: DatabaseManager) {
        this.apiKey = apiKey;
        this.dbManager = dbManager || DatabaseManager.fromEnvironment();
    }

    async getDrug(args: any, cache: CacheManager) {
        const { genericName } = args
        const cacheKey = cache.createKey('interactions', { genericName: genericName });

        const drug = await cache.getOrFetch(
            cacheKey,
            () => this.searchGenericName(genericName)
        );

        return {
            content: [{
                type: 'text',
                text: JSON.stringify({ results: drug })
            }]
        };
    }

    // Add searchDrugs method for direct calls
    async searchDrugs(params: any): Promise<Generics[]> {
        if (params.drug_name) {
            return this.searchGenericName(params.drug_name);
        } else if (params.active_ingredient) {
            return this.searchGenericName(params.active_ingredient);
        }
        return [];
    }

    async searchGenericName(genericName: string): Promise<Generics[]> {
        try {
            // DATABASE-FIRST: Return database results immediately, test external APIs in background
            if (this.dbManager.isAvailable()) {
                console.log('Searching FDA drugs in PostgreSQL database');
                const dbResults = await this.searchDatabase(genericName, 25);

                // Start background validation of external API (don't await)
                this.validateExternalAPI(genericName).catch(error => {
                    console.warn('Background external API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.length} drugs, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to external FDA API');
                return await this.searchExternalAPI(genericName);
            }

            throw new Error('Neither database nor external API available for FDA drug search');
        } catch (error) {
            console.error('FDA search failed:', error);
            throw error;
        }
    }

    /**
     * Background validation of external FDA API connectivity
     */
    private async validateExternalAPI(genericName: string): Promise<void> {
        const timeout = 10000; // 10 second timeout for background checks

        try {
            console.log('[BACKGROUND] Testing external FDA API connectivity...');

            const externalPromise = Promise.race([
                this.searchExternalAPI(genericName),
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('External FDA API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ External FDA API healthy - returned ${externalResults.length} drugs`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  External FDA API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
        }
    }

    private async searchDatabase(genericName: string, maxResults: number): Promise<Generics[]> {
        try {
            const params: any[] = [`%${genericName}%`, genericName, maxResults];
            
            // Use full-text search if available, otherwise fall back to ILIKE
            const query = `
                SELECT 
                    COALESCE(ndc, product_ndc) AS ndc,
                    COALESCE(generic_name, generic) AS name,
                    COALESCE(brand_name, labeler_name) AS label,
                    COALESCE(brand_name, labeler_name) AS brand,
                    COALESCE(active_ingredients, substances) AS ingredients,
                    COALESCE(ts_rank_cd(search_vector, plainto_tsquery('english', $2)), 0) as rank
                FROM fda_drugs
                WHERE search_vector @@ plainto_tsquery('english', $2)
                   OR COALESCE(generic_name, generic) ILIKE $1
                   OR COALESCE(brand_name, labeler_name) ILIKE $1
                ORDER BY rank DESC, ndc ASC
                LIMIT $3
            `;

            const result = await this.dbManager.query(query, params);

            console.log(`Database search returned ${result.rows.length} FDA drugs`);

            return result.rows.map((row: any) => ({
                ndc: row.ndc || '',
                name: row.name || '',
                label: row.label || '',
                brand: row.brand || '',
                ingredients: Array.isArray(row.ingredients) ? row.ingredients : (row.ingredients ? [row.ingredients] : [])
            }));

        } catch (error) {
            console.error('Database search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async searchExternalAPI(genericName: string): Promise<Generics[]> {
        const url = new URL(this.baseUrl);
        url.searchParams.append('search', `generic_name:"${genericName}"`)


        // Rate limiting: 240 requests/minute without API key
        if (!this.apiKey && this.isRateLimited()) {
            throw new Error('FDA API rate limit reached. Consider getting free API key at https://open.fda.gov/apis/authentication/');
        }
        const response = await fetch(url);
        const data = await response.json() as FDAResponse;

        return data.results;
    }
}