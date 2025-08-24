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

interface DrugInfoResponse {
    results: Generics[];
}

export class DrugInfo {
    private lastRequestTime = 0;
    private requestCount = 0;
    private readonly rateLimitWindow = 60000; // 1 minute
    private readonly maxRequestsPerMinute = 240;
    private readonly baseUrl = 'http://172.20.0.20:8081/drugs/search';
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
                console.log('Searching drug information in PostgreSQL database');
                const dbResults = await this.searchDatabase(genericName, 25);

                // Start background validation of external API (don't await)
                this.validateExternalAPI(genericName).catch(error => {
                    console.warn('Background external API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.length} drugs, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use medical-mirrors API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to medical-mirrors drug API');
                return await this.searchMedicalMirrorsAPI(genericName);
            }

            throw new Error('Neither database nor medical-mirrors API available for drug search');
        } catch (error) {
            console.error('Drug search failed:', error);
            throw error;
        }
    }

    /**
     * Background validation of medical-mirrors API connectivity
     */
    private async validateExternalAPI(genericName: string): Promise<void> {
        const timeout = 10000; // 10 second timeout for background checks

        try {
            console.log('[BACKGROUND] Testing medical-mirrors API connectivity...');

            const externalPromise = Promise.race([
                this.searchMedicalMirrorsAPI(genericName),
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('Medical-mirrors API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ Medical-mirrors API healthy - returned ${externalResults.length} drugs`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  Medical-mirrors API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
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
                FROM drug_information
                WHERE search_vector @@ plainto_tsquery('english', $2)
                   OR COALESCE(generic_name, generic) ILIKE $1
                   OR COALESCE(brand_name, labeler_name) ILIKE $1
                ORDER BY rank DESC, ndc ASC
                LIMIT $3
            `;

            const result = await this.dbManager.query(query, params);

            console.log(`Database search returned ${result.rows.length} drugs`);

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

    private async searchMedicalMirrorsAPI(genericName: string): Promise<Generics[]> {
        const url = new URL(this.baseUrl);
        url.searchParams.append('generic_name', genericName);
        url.searchParams.append('max_results', '25');

        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Medical-mirrors API error: ${response.status}`);
        }
        
        const data = await response.json() as any;
        
        // Medical-mirrors returns {status: "success", data: [...]} format
        if (data.status === 'success' && Array.isArray(data.data)) {
            return data.data.map((drug: any) => ({
                ndc: drug.ndc || '',
                name: drug.generic_name || drug.name || '',
                label: drug.brand_name || drug.manufacturer || '',
                brand: drug.brand_name || '',
                ingredients: drug.ingredients || []
            }));
        }
        
        return [];
    }
}