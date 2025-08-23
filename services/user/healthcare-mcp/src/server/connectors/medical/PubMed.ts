import fetch from 'node-fetch';
import { DatabaseManager } from '../../utils/DatabaseManager.js';
import { CacheManager } from "../../utils/Cache.js";

export interface PubMedArticle {
    title: string;
    authors: string[];
    journal: string;
    pubDate: string;
    doi: string;
    abstract: string;
    pmid: string;
}

interface PubMedSearchResponse {
    esearchresult: {
        idlist: string[];
        count: string;
        retmax: string;
        retstart: string;
    }
}

interface PubMedSummaryResponse {
    result: {
        [pmid: string]: {
            title: string;
            authors: Array<{ name: string }>;
            fulljournalname: string;
            pubdate: string;
            elocationid: string;
            abstract?: string;
            uid: string;
        }
    }
}

export class PubMed {
    private readonly baseUrl = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils';
    private readonly apiKey?: string;
    private dbManager: DatabaseManager;

    constructor(apiKey?: string, dbManager?: DatabaseManager) {
        // Only set apiKey if it's a real key
        this.apiKey = apiKey && apiKey !== 'optional_for_higher_rate_limits' ? apiKey : undefined;
        this.dbManager = dbManager || DatabaseManager.fromEnvironment();
    } async getArticles(args: any, cache: CacheManager) {
        const { query } = args;
        const maxResults = Math.max(1, Math.min(100, Number(args?.maxResults ?? 25)));
        const cacheKey = cache.createKey('pubmed', { query, maxResults });

        try {
            console.log('PubMed getArticles called with:', { query, maxResults });

            const articles = await cache.getOrFetch(
                cacheKey,
                () => this.searchArticles(query, maxResults)
            );

            console.log('PubMed articles retrieved:', articles.length, 'articles');

            const response = {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        articles: articles.map(a => ({
                            title: a.title,
                            authors: a.authors,
                            journal: a.journal,
                            publication_date: a.pubDate,
                            doi: a.doi,
                            abstract: a.abstract,
                            pmid: a.pmid
                        }))
                    })
                }]
            };

            // Log the number of articles prepared in the text content
            const parsedContent = JSON.parse((response.content[0] as any).text);
            console.log('PubMed response prepared, articles:', parsedContent.articles.length);
            return response;
        } catch (error) {
            console.error('PubMed API error:', error);
            return {
                content: [{
                    type: 'text',
                    text: `Error executing search-pubmed: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    async search(query: string, maxResults: number = 25): Promise<PubMedArticle[]> {
        return this.searchArticles(query, maxResults);
    }

    async searchArticles(query: string, maxResults: number = 25): Promise<PubMedArticle[]> {
        try {
            if (!query || typeof query !== 'string' || query.trim().length === 0) {
                throw new Error('PubMed search failed: Query string is empty or invalid.');
            }

            // DATABASE-FIRST: Return database results immediately, test external APIs in background
            if (this.dbManager.isAvailable()) {
                console.log('Searching PubMed articles in PostgreSQL database');
                const dbResults = await this.searchDatabase(query, maxResults);

                // Start background validation of external API (don't await)
                this.validateExternalSources(query, maxResults).catch(error => {
                    console.warn('Background external API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.length} articles, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to external PubMed API');
                return await this.searchExternalAPI(query, maxResults);
            }

            throw new Error('Neither database nor external API available for PubMed search');
        } catch (error) {
            console.error('PubMed search failed:', error);
            throw error;
        }
    }

    /**
     * Background validation of external API connectivity
     * Tests external sources without blocking the main search response
     */
    private async validateExternalSources(query: string, maxResults: number): Promise<void> {
        const timeout = 10000; // 10 second timeout for background checks

        try {
            console.log('[BACKGROUND] Testing external PubMed API connectivity...');

            // Test external API with timeout
            const externalPromise = Promise.race([
                this.searchExternalAPI(query, Math.min(maxResults, 5)), // Test with fewer results
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('External API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ External PubMed API healthy - returned ${externalResults.length} articles`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  External PubMed API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
        }

        // No local mirror HTTP; database is the mirror
    }

    private async searchDatabase(query: string, maxResults: number): Promise<PubMedArticle[]> {
        try {

            // Parse query for boolean OR logic
            const orTerms = query.split(/\s+OR\s+/i).map(term => term.trim()).filter(term => term.length > 0);

            let searchQuery: string;
            let searchParams: any[];

            if (orTerms.length > 1) {
                // Handle OR logic: search for any of the terms
                console.log(`Executing OR search for terms: ${orTerms.join(', ')}`);

                const conditions = orTerms.map((_, index) => {
                    const paramIndex = index * 3;
                    return `(title ILIKE $${paramIndex + 1} OR abstract ILIKE $${paramIndex + 2} OR journal ILIKE $${paramIndex + 3})`;
                }).join(' OR ');

                searchQuery = `
                    SELECT DISTINCT pmid, title, journal, pub_date, abstract, authors, doi
                    FROM pubmed_articles 
                    WHERE ${conditions}
                    ORDER BY pub_date DESC
                    LIMIT $${orTerms.length * 3 + 1}
                `;

                searchParams = [];
                orTerms.forEach(term => {
                    const searchTerm = `%${term}%`;
                    searchParams.push(searchTerm, searchTerm, searchTerm);
                });
                searchParams.push(maxResults);

            } else {
                // Standard single-term search with full-text search if available
                console.log(`Executing single-term search for: "${query}"`);

                searchQuery = `
                    SELECT pmid, title, journal, pub_date, abstract, authors, doi,
                           COALESCE(ts_rank_cd(search_vector, plainto_tsquery('english', $1)), 0) as rank
                    FROM pubmed_articles 
                    WHERE search_vector @@ plainto_tsquery('english', $1)
                       OR title ILIKE $2 
                       OR abstract ILIKE $2 
                       OR journal ILIKE $2
                    ORDER BY rank DESC, pub_date DESC
                    LIMIT $3
                `;

                const searchTerm = `%${query}%`;
                searchParams = [query, searchTerm, maxResults];
            }

            const result = await this.dbManager.query(searchQuery, searchParams);

            console.log(`Database search returned ${result.rows.length} articles`);

            const articles = result.rows.map((row: any) => ({
                pmid: row.pmid?.toString() || '',
                title: row.title || '',
                journal: row.journal || '',
                pubDate: row.pub_date || '',
                abstract: row.abstract || '',
                authors: row.authors ? (Array.isArray(row.authors) ? row.authors : [row.authors]) : [],
                doi: row.doi || ''
            }));

            return articles;

        } catch (error) {
            console.error('Database search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    } private async searchExternalAPI(query: string, maxResults: number): Promise<PubMedArticle[]> {
        try {
            // Step 1: Search for article IDs
            const searchUrl = new URL(`${this.baseUrl}/esearch.fcgi`);
            searchUrl.searchParams.append('db', 'pubmed');
            searchUrl.searchParams.append('term', query);
            searchUrl.searchParams.append('retmax', maxResults.toString());
            searchUrl.searchParams.append('retmode', 'json');
            if (this.apiKey) {
                searchUrl.searchParams.append('api_key', this.apiKey);
            }
            const sanitizedSearchUrl = new URL(searchUrl.toString());
            sanitizedSearchUrl.searchParams.delete('api_key');
            console.log('PubMed search URL:', sanitizedSearchUrl.toString());

            const searchResponse = await fetch(searchUrl.toString());
            const rawSearchBody = await searchResponse.text();

            if (!searchResponse.ok) {
                console.error('PubMed search response body:', rawSearchBody);
                throw new Error(`PubMed search failed: ${searchResponse.status} ${searchResponse.statusText}`);
            }

            let searchData: PubMedSearchResponse;
            try {
                searchData = JSON.parse(rawSearchBody) as PubMedSearchResponse;
            } catch (parseErr) {
                console.error('Failed to parse PubMed search response:', rawSearchBody);
                throw new Error('Invalid JSON response from PubMed API');
            }

            if (!searchData.esearchresult) {
                console.error('Unexpected PubMed search response:', searchData);
                throw new Error('Invalid response structure from PubMed API');
            }

            const pmids = searchData.esearchresult.idlist || [];
            if (!pmids.length) {
                console.log('No articles found for query:', query);
                return [];
            }
            console.log(`Found ${pmids.length} articles for query: ${query}`);

            // Step 2: Get article details
            const summaryUrl = new URL(`${this.baseUrl}/esummary.fcgi`);
            summaryUrl.searchParams.append('db', 'pubmed');
            summaryUrl.searchParams.append('id', pmids.join(','));
            summaryUrl.searchParams.append('retmode', 'json');
            if (this.apiKey) {
                summaryUrl.searchParams.append('api_key', this.apiKey);
            }

            const summaryResponse = await fetch(summaryUrl.toString());
            const rawSummaryBody = await summaryResponse.text();

            if (!summaryResponse.ok) {
                console.error('PubMed summary response body:', rawSummaryBody);
                throw new Error(`PubMed summary failed: ${summaryResponse.status} ${summaryResponse.statusText}`);
            }

            let summaryData: PubMedSummaryResponse;
            try {
                summaryData = JSON.parse(rawSummaryBody) as PubMedSummaryResponse;
            } catch (parseErr) {
                console.error('Failed to parse PubMed summary response:', rawSummaryBody);
                throw new Error('Invalid JSON response from PubMed API');
            }

            if (!summaryData.result) {
                console.error('Unexpected PubMed summary response:', summaryData);
                throw new Error('Invalid summary response structure from PubMed API');
            }

            // Step 3: Format results
            const results = pmids.map((pmid: string) => {
                const article = summaryData.result[pmid];
                if (!article) {
                    console.warn(`No data found for PMID: ${pmid}`);
                    return null;
                }
                return {
                    title: article.title || 'No title available',
                    authors: Array.isArray(article.authors)
                        ? article.authors.map((a: any) => a.name || 'Unknown author')
                        : ['No authors listed'],
                    journal: article.fulljournalname || 'Unknown journal',
                    pubDate: article.pubdate || 'Unknown date',
                    doi: article.elocationid || 'No DOI',
                    abstract: article.abstract || 'No abstract available',
                    pmid: pmid
                };
            }).filter(Boolean) as PubMedArticle[];

            console.log('Returning detailed results:', results.length, 'articles');
            return results;
        } catch (error) {
            console.error('PubMed search error:', error);
            throw new Error(`PubMed search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}