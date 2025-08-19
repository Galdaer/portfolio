import fetch from 'node-fetch';
import { Client } from 'pg';
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
    // No mirror HTTP. Database is the mirror.

    private isRateLimited(): boolean {
        const now = Date.now();
        if (now - this.lastRequestTime > this.rateLimitWindow) {
            this.requestCount = 0;
            this.lastRequestTime = now;
        }
        this.requestCount++;
        return this.requestCount > this.maxRequestsPerMinute;
    }

    constructor(apiKey?: string) {
        this.apiKey = apiKey;
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
            // DATABASE-FIRST: Try local Postgres mirror first, then external API; background test external only
            try {
                const dbResults = await this.searchDatabase(genericName, 25);
                this.validateExternalAPI(genericName).catch(err => console.warn('Background FDA external API validation failed:', err));
                return dbResults;
            } catch (dbError) {
                console.warn('FDA DB search failed, falling back to external API:', dbError);
                return await this.searchExternalAPI(genericName);
            }
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

        const table = process.env.FDA_DRUGS_TABLE || 'fda_drugs';

        await client.connect();

        const params: any[] = [`%${genericName}%`, maxResults];
        const query = `
            SELECT 
                COALESCE(ndc, product_ndc) AS ndc,
                COALESCE(generic_name, generic) AS name,
                COALESCE(brand_name, labeler_name) AS label,
                COALESCE(brand_name, labeler_name) AS brand,
                COALESCE(active_ingredients, substances) AS ingredients
            FROM ${table}
            WHERE COALESCE(generic_name, generic) ILIKE $1
            ORDER BY ndc ASC
            LIMIT $2
        `;

        const result = await client.query(query, params);
        await client.end();

        return result.rows.map((row: any) => ({
            ndc: row.ndc || '',
            name: row.name || '',
            label: row.label || '',
            brand: row.brand || '',
            ingredients: Array.isArray(row.ingredients) ? row.ingredients : (row.ingredients ? [row.ingredients] : [])
        }));
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