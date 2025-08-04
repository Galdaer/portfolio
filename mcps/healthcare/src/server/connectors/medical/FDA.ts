import { CacheManager } from "../../utils/Cache.js"
import fetch from 'node-fetch';

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

    private readonly baseUrl = 'https://api.fda.gov/drug/ndc.json';
    private readonly apiKey: string;

    constructor(apiKey: string) {
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
        const url = new URL(this.baseUrl);
        url.searchParams.append('search', `generic_name:"${genericName}"`)

        const response = await fetch(url);
        const data = await response.json() as FDAResponse;

        return data.results;
    }
}