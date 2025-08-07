import fetch from 'node-fetch';
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
    private readonly localMirrorUrl = 'http://172.20.0.20:8080/trials';
    private readonly apiKey?: string;
    private useLocalMirror: boolean = true;

    constructor(apiKey?: string) {
        this.apiKey = apiKey;
        // Check environment for local mirror preference
        this.useLocalMirror = process.env.USE_LOCAL_MEDICAL_MIRRORS !== 'false';
    }

    async getTrials(args: any, cache: CacheManager) {
        const { condition, location } = args;
        const cacheKey = cache.createKey('trials', { condition, location });

        const trials = await cache.getOrFetch(
            cacheKey,
            () => this.searchTrials(condition, location)
        );

        return {
            content: [{
                type: 'text',
                text: JSON.stringify(trials, null, 2)
            }]
        };
    }

    // Add search method for direct calls
    async search(params: any): Promise<ClinicalTrial[]> {
        return this.searchTrials(params.condition, params.location);
    }

    async searchTrials(condition: string, location?: string): Promise<ClinicalTrial[]> {
        try {
            // Try local mirror first
            if (this.useLocalMirror) {
                try {
                    console.log('Attempting to use local ClinicalTrials mirror');
                    return await this.searchLocalMirror(condition, location);
                } catch (localError) {
                    console.warn('Local ClinicalTrials mirror failed, falling back to external API:', localError);
                    // Fall through to external API
                }
            }

            console.log('Using external ClinicalTrials API');
            return await this.searchExternalAPI(condition, location);
        } catch (error) {
            console.error('ClinicalTrials search failed:', error);
            throw error;
        }
    }

    private async searchLocalMirror(condition: string, location?: string): Promise<ClinicalTrial[]> {
        const params = new URLSearchParams();
        if (condition) params.append('condition', condition);
        if (location) params.append('location', location);
        params.append('max_results', '10');

        const response = await fetch(`${this.localMirrorUrl}/search?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`Local mirror responded with ${response.status}`);
        }

        const data = await response.json();
        const trials = JSON.parse(data.content[0].text);

        return trials.map((trial: any) => ({
            nctId: trial.nctId || '',
            title: trial.title || '',
            status: trial.status || '',
            phase: trial.phase || '',
            conditions: trial.conditions || [],
            locations: trial.locations || [],
            lastUpdated: trial.startDate || ''
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