import fetch from 'node-fetch';
import { DatabaseManager } from '../../utils/DatabaseManager.js';
import { CacheManager } from '../../utils/Cache.js';

export interface ICD10Code {
    code: string;
    description: string;
    category?: string;
    chapter?: string;
    inclusion_notes?: string[];
    exclusion_notes?: string[];
    source: 'database' | 'external';
}

export interface ICD10SearchResponse {
    codes: ICD10Code[];
    total_results: number;
    search_query: string;
    source_used: 'database' | 'external' | 'mixed';
}

interface NLMResponse {
    [0]: number;
    [1]: string[][];
    [2]: any;
    [3]: string[];
}

export class ICD10Connector {
    private readonly nlmBaseUrl = 'https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search';
    private dbManager: DatabaseManager;

    constructor(dbManager: DatabaseManager) {
        this.dbManager = dbManager;
    }

    async searchCodes(args: any, cache?: CacheManager): Promise<any> {
        const { query, max_results = 10, exact_match = false } = args;
        
        if (!query || typeof query !== 'string' || query.trim().length === 0) {
            throw new Error('Query is required and must be a non-empty string');
        }

        const maxResults = Math.max(1, Math.min(100, Number(max_results)));
        const cacheKey = cache?.createKey('icd10', { query, maxResults, exact_match });

        try {
            console.log('ICD-10 search called with:', { query, maxResults, exact_match });

            const searchResults = await (cache && cacheKey
                ? cache.getOrFetch(cacheKey, () => this.performSearch(query, maxResults, exact_match))
                : this.performSearch(query, maxResults, exact_match)
            );

            console.log('ICD-10 search results:', searchResults.codes.length, 'codes found');

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        codes: searchResults.codes.map(code => ({
                            code: code.code,
                            description: code.description,
                            category: code.category,
                            chapter: code.chapter,
                            inclusion_notes: code.inclusion_notes || [],
                            exclusion_notes: code.exclusion_notes || [],
                            source: code.source
                        })),
                        total_results: searchResults.total_results,
                        search_query: searchResults.search_query,
                        source_used: searchResults.source_used
                    }, null, 2)
                }]
            };
        } catch (error) {
            console.error('ICD-10 search error:', error);
            return {
                content: [{
                    type: 'text',
                    text: `Error executing ICD-10 search: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    async lookupCodeDetails(code: string): Promise<ICD10Code | null> {
        if (!code || typeof code !== 'string' || code.trim().length === 0) {
            throw new Error('Code is required and must be a non-empty string');
        }

        try {
            // Try database first
            if (this.dbManager.isAvailable()) {
                console.log(`Looking up ICD-10 code "${code}" in database`);
                
                const result = await this.dbManager.query(
                    `SELECT code, description, category, chapter, inclusion_notes, exclusion_notes 
                     FROM icd10_codes 
                     WHERE UPPER(code) = UPPER($1)`,
                    [code.trim()]
                );

                if (result.rows.length > 0) {
                    const row = result.rows[0];
                    console.log(`Database returned details for code: ${code}`);
                    return {
                        code: row.code,
                        description: row.description,
                        category: row.category,
                        chapter: row.chapter,
                        inclusion_notes: row.inclusion_notes || [],
                        exclusion_notes: row.exclusion_notes || [],
                        source: 'database'
                    };
                }
            }

            // Fallback to external API
            if (this.dbManager.canFallback()) {
                console.log(`Database lookup failed for code "${code}", trying external API`);
                return await this.lookupExternalAPI(code);
            }

            console.log(`No data found for ICD-10 code: ${code}`);
            return null;

        } catch (error) {
            console.error(`ICD-10 lookup error for code "${code}":`, error);
            throw error;
        }
    }

    private async performSearch(query: string, maxResults: number, exactMatch: boolean): Promise<ICD10SearchResponse> {
        try {
            // DATABASE-FIRST: Try database search immediately
            if (this.dbManager.isAvailable()) {
                console.log('Searching ICD-10 codes in PostgreSQL database');
                
                const dbResults = await this.searchDatabase(query, maxResults, exactMatch);
                
                // Start background validation of external API (don't await)
                this.validateExternalSources(query, maxResults).catch(error => {
                    console.warn('Background external API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.codes.length} ICD-10 codes, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to external NLM API');
                return await this.searchExternalAPI(query, maxResults, exactMatch);
            }

            throw new Error('Neither database nor external API available for ICD-10 search');

        } catch (error) {
            console.error('ICD-10 search failed:', error);
            throw error;
        }
    }

    private async searchDatabase(query: string, maxResults: number, exactMatch: boolean): Promise<ICD10SearchResponse> {
        try {
            let searchQuery: string;
            let searchParams: any[];

            if (exactMatch) {
                // Exact code match
                searchQuery = `
                    SELECT code, description, category, chapter, inclusion_notes, exclusion_notes
                    FROM icd10_codes
                    WHERE UPPER(code) = UPPER($1)
                    ORDER BY code
                    LIMIT $2
                `;
                searchParams = [query.trim(), maxResults];
            } else {
                // Full-text search using tsvector
                searchQuery = `
                    SELECT code, description, category, chapter, inclusion_notes, exclusion_notes,
                           ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                    FROM icd10_codes
                    WHERE search_vector @@ plainto_tsquery('english', $1)
                       OR code ILIKE $2
                       OR description ILIKE $2
                    ORDER BY rank DESC, code
                    LIMIT $3
                `;
                const searchTerm = `%${query}%`;
                searchParams = [query, searchTerm, maxResults];
            }

            const result = await this.dbManager.query(searchQuery, searchParams);
            
            console.log(`Database search returned ${result.rows.length} ICD-10 codes`);

            const codes: ICD10Code[] = result.rows.map((row: any) => ({
                code: row.code || '',
                description: row.description || '',
                category: row.category || null,
                chapter: row.chapter || null,
                inclusion_notes: row.inclusion_notes || [],
                exclusion_notes: row.exclusion_notes || [],
                source: 'database' as const
            }));

            return {
                codes,
                total_results: codes.length,
                search_query: query,
                source_used: 'database'
            };

        } catch (error) {
            console.error('Database search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async searchExternalAPI(query: string, maxResults: number, exactMatch: boolean): Promise<ICD10SearchResponse> {
        try {
            const url = new URL(this.nlmBaseUrl);
            url.searchParams.append('sf', 'code,name');
            url.searchParams.append('df', 'code,name');
            url.searchParams.append('maxList', maxResults.toString());
            
            if (exactMatch) {
                // For exact matches, search by code
                url.searchParams.append('terms', query);
                url.searchParams.append('ef', 'code');
            } else {
                // For partial matches, search in both code and description
                url.searchParams.append('terms', query);
            }

            console.log('NLM ICD-10 search URL:', url.toString());

            const response = await fetch(url.toString(), {
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Intelluxe-Healthcare-MCP/1.0'
                }
            });

            if (!response.ok) {
                throw new Error(`NLM API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json() as NLMResponse;
            
            // NLM API returns: [count, [code_results], {}, [name_results]]
            if (!Array.isArray(data) || data.length < 4) {
                throw new Error('Invalid response format from NLM API');
            }

            const [count, codeData, , nameData] = data;
            const codes: ICD10Code[] = [];

            if (Array.isArray(codeData) && Array.isArray(nameData)) {
                const maxItems = Math.min(codeData.length, nameData.length, maxResults);
                
                for (let i = 0; i < maxItems; i++) {
                    const codeInfo = codeData[i];
                    const name = nameData[i];
                    
                    if (Array.isArray(codeInfo) && codeInfo.length >= 2) {
                        codes.push({
                            code: codeInfo[0] || '',
                            description: name || codeInfo[1] || '',
                            source: 'external'
                        });
                    }
                }
            }

            console.log(`External API returned ${codes.length} ICD-10 codes`);

            return {
                codes,
                total_results: count || codes.length,
                search_query: query,
                source_used: 'external'
            };

        } catch (error) {
            console.error('External NLM API search error:', error);
            throw new Error(`External API search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async lookupExternalAPI(code: string): Promise<ICD10Code | null> {
        try {
            const searchResult = await this.searchExternalAPI(code, 1, true);
            
            if (searchResult.codes.length > 0) {
                const foundCode = searchResult.codes[0];
                if (foundCode.code.toUpperCase() === code.toUpperCase()) {
                    return foundCode;
                }
            }
            
            return null;
        } catch (error) {
            console.error(`External API lookup error for code "${code}":`, error);
            return null;
        }
    }

    private async validateExternalSources(query: string, maxResults: number): Promise<void> {
        const timeout = 10000; // 10 second timeout for background checks

        try {
            console.log('[BACKGROUND] Testing external NLM ICD-10 API connectivity...');

            const externalPromise = Promise.race([
                this.searchExternalAPI(query, Math.min(maxResults, 5), false),
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('External API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ External NLM ICD-10 API healthy - returned ${externalResults.codes.length} codes`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  External NLM ICD-10 API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
        }
    }
}