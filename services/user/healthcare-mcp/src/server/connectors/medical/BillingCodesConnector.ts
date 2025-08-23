import fetch from 'node-fetch';
import { DatabaseManager } from '../../utils/DatabaseManager.js';
import { CacheManager } from '../../utils/Cache.js';

export interface BillingCode {
    code: string;
    description: string;
    code_type: 'HCPCS' | 'CPT';
    category?: string;
    coverage_notes?: string;
    effective_date?: string;
    source: 'database' | 'external';
}

export interface BillingCodeSearchResponse {
    codes: BillingCode[];
    total_results: number;
    search_query: string;
    source_used: 'database' | 'external' | 'mixed';
}

interface NLMHCPCSResponse {
    [0]: number;
    [1]: string[][];
    [2]: any;
    [3]: string[];
}

export class BillingCodesConnector {
    private readonly nlmHcpcsUrl = 'https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search';
    private dbManager: DatabaseManager;

    constructor(dbManager: DatabaseManager) {
        this.dbManager = dbManager;
    }

    async searchCodes(args: any, cache?: CacheManager): Promise<any> {
        const { query, code_type = 'all', max_results = 10 } = args;
        
        if (!query || typeof query !== 'string' || query.trim().length === 0) {
            throw new Error('Query is required and must be a non-empty string');
        }

        const maxResults = Math.max(1, Math.min(100, Number(max_results)));
        const codeType = code_type.toLowerCase();
        
        if (!['hcpcs', 'cpt', 'all'].includes(codeType)) {
            throw new Error('code_type must be "hcpcs", "cpt", or "all"');
        }

        const cacheKey = cache?.createKey('billing_codes', { query, maxResults, code_type: codeType });

        try {
            console.log('Billing codes search called with:', { query, maxResults, code_type: codeType });

            const searchResults = await (cache && cacheKey
                ? cache.getOrFetch(cacheKey, () => this.performSearch(query, maxResults, codeType))
                : this.performSearch(query, maxResults, codeType)
            );

            console.log('Billing codes search results:', searchResults.codes.length, 'codes found');

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        codes: searchResults.codes.map(code => ({
                            code: code.code,
                            description: code.description,
                            code_type: code.code_type,
                            category: code.category,
                            coverage_notes: code.coverage_notes,
                            effective_date: code.effective_date,
                            source: code.source
                        })),
                        total_results: searchResults.total_results,
                        search_query: searchResults.search_query,
                        source_used: searchResults.source_used
                    }, null, 2)
                }]
            };
        } catch (error) {
            console.error('Billing codes search error:', error);
            return {
                content: [{
                    type: 'text',
                    text: `Error executing billing codes search: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    async lookupCodeDetails(code: string): Promise<BillingCode | null> {
        if (!code || typeof code !== 'string' || code.trim().length === 0) {
            throw new Error('Code is required and must be a non-empty string');
        }

        try {
            // Try database first
            if (this.dbManager.isAvailable()) {
                console.log(`Looking up billing code "${code}" in database`);
                
                const result = await this.dbManager.query(
                    `SELECT code, description, code_type, category, coverage_notes, effective_date 
                     FROM billing_codes 
                     WHERE UPPER(code) = UPPER($1)`,
                    [code.trim()]
                );

                if (result.rows.length > 0) {
                    const row = result.rows[0];
                    console.log(`Database returned details for code: ${code}`);
                    return {
                        code: row.code,
                        description: row.description,
                        code_type: row.code_type,
                        category: row.category,
                        coverage_notes: row.coverage_notes,
                        effective_date: row.effective_date,
                        source: 'database'
                    };
                }
            }

            // Fallback to external API
            if (this.dbManager.canFallback()) {
                console.log(`Database lookup failed for code "${code}", trying external API`);
                return await this.lookupExternalAPI(code);
            }

            console.log(`No data found for billing code: ${code}`);
            return null;

        } catch (error) {
            console.error(`Billing code lookup error for code "${code}":`, error);
            throw error;
        }
    }

    private async performSearch(query: string, maxResults: number, codeType: string): Promise<BillingCodeSearchResponse> {
        try {
            // DATABASE-FIRST: Try database search immediately
            if (this.dbManager.isAvailable()) {
                console.log('Searching billing codes in PostgreSQL database');
                
                const dbResults = await this.searchDatabase(query, maxResults, codeType);
                
                // Start background validation of external API (don't await)
                this.validateExternalSources(query, maxResults).catch(error => {
                    console.warn('Background external API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.codes.length} billing codes, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to external NLM API');
                return await this.searchExternalAPI(query, maxResults);
            }

            throw new Error('Neither database nor external API available for billing codes search');

        } catch (error) {
            console.error('Billing codes search failed:', error);
            throw error;
        }
    }

    private async searchDatabase(query: string, maxResults: number, codeType: string): Promise<BillingCodeSearchResponse> {
        try {
            let searchQuery: string;
            let searchParams: any[];

            // Build WHERE clause based on code type filter
            let codeTypeFilter = '';
            if (codeType === 'hcpcs') {
                codeTypeFilter = " AND code_type = 'HCPCS'";
            } else if (codeType === 'cpt') {
                codeTypeFilter = " AND code_type = 'CPT'";
            }
            // For 'all', no additional filter

            // Full-text search using tsvector
            searchQuery = `
                SELECT code, description, code_type, category, coverage_notes, effective_date,
                       ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                FROM billing_codes
                WHERE (search_vector @@ plainto_tsquery('english', $1)
                       OR code ILIKE $2
                       OR description ILIKE $2)
                ${codeTypeFilter}
                ORDER BY rank DESC, code
                LIMIT $3
            `;
            const searchTerm = `%${query}%`;
            searchParams = [query, searchTerm, maxResults];

            const result = await this.dbManager.query(searchQuery, searchParams);
            
            console.log(`Database search returned ${result.rows.length} billing codes`);

            const codes: BillingCode[] = result.rows.map((row: any) => ({
                code: row.code || '',
                description: row.description || '',
                code_type: row.code_type || 'HCPCS',
                category: row.category || null,
                coverage_notes: row.coverage_notes || null,
                effective_date: row.effective_date || null,
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

    private async searchExternalAPI(query: string, maxResults: number): Promise<BillingCodeSearchResponse> {
        try {
            const url = new URL(this.nlmHcpcsUrl);
            url.searchParams.append('sf', 'code,name');
            url.searchParams.append('df', 'code,name');
            url.searchParams.append('maxList', maxResults.toString());
            url.searchParams.append('terms', query);

            console.log('NLM HCPCS search URL:', url.toString());

            const response = await fetch(url.toString(), {
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Intelluxe-Healthcare-MCP/1.0'
                }
            });

            if (!response.ok) {
                throw new Error(`NLM API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json() as NLMHCPCSResponse;
            
            // NLM API returns: [count, [code_results], {}, [name_results]]
            if (!Array.isArray(data) || data.length < 4) {
                throw new Error('Invalid response format from NLM HCPCS API');
            }

            const [count, codeData, , nameData] = data;
            const codes: BillingCode[] = [];

            if (Array.isArray(codeData) && Array.isArray(nameData)) {
                const maxItems = Math.min(codeData.length, nameData.length, maxResults);
                
                for (let i = 0; i < maxItems; i++) {
                    const codeInfo = codeData[i];
                    const name = nameData[i];
                    
                    if (Array.isArray(codeInfo) && codeInfo.length >= 2) {
                        codes.push({
                            code: codeInfo[0] || '',
                            description: name || codeInfo[1] || '',
                            code_type: 'HCPCS', // NLM API only provides HCPCS codes
                            source: 'external'
                        });
                    }
                }
            }

            console.log(`External API returned ${codes.length} HCPCS codes`);

            return {
                codes,
                total_results: count || codes.length,
                search_query: query,
                source_used: 'external'
            };

        } catch (error) {
            console.error('External NLM HCPCS API search error:', error);
            throw new Error(`External API search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async lookupExternalAPI(code: string): Promise<BillingCode | null> {
        try {
            const searchResult = await this.searchExternalAPI(code, 1);
            
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
            console.log('[BACKGROUND] Testing external NLM HCPCS API connectivity...');

            const externalPromise = Promise.race([
                this.searchExternalAPI(query, Math.min(maxResults, 5)),
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('External API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ External NLM HCPCS API healthy - returned ${externalResults.codes.length} codes`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  External NLM HCPCS API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
        }
    }
}