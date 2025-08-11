import fetch from 'node-fetch';
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
    private readonly localMirrorUrl = 'http://172.20.0.20:8080/fda';
    private readonly apiKey?: string;
    private useLocalMirror: boolean = true;

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
        // Check environment for local mirror preference
        this.useLocalMirror = process.env.USE_LOCAL_MEDICAL_MIRRORS !== 'false';
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
                text: JSON.stringify(drug, null, 2)
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
            // Try local mirror first
            if (this.useLocalMirror) {
                try {
                    console.log('Attempting to use local FDA mirror');
                    return await this.searchLocalMirror(genericName);
                } catch (localError) {
                    console.warn('Local FDA mirror failed, falling back to external API:', localError);
                    // Fall through to external API
                }
            }

            console.log('Using external FDA API');
            return await this.searchExternalAPI(genericName);
        } catch (error) {
            console.error('FDA search failed:', error);
            throw error;
        }
    }

    private async searchLocalMirror(genericName: string): Promise<Generics[]> {
        const params = new URLSearchParams();
        if (genericName) params.append('generic_name', genericName);
        params.append('max_results', '10');

        const response = await fetch(`${this.localMirrorUrl}/search?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`Local mirror responded with ${response.status}`);
        }

        const data = await response.json() as { content: Array<{ text: string }> };
        const drugs = JSON.parse(data.content[0].text);

        return drugs.map((drug: any) => ({
            ndc: drug.ndc || '',
            name: drug.name || '',
            label: drug.brandName || drug.name || '',
            brand: drug.brandName || '',
            ingredients: drug.ingredients || []
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