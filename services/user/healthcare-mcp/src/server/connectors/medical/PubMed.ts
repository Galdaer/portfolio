import fetch from 'node-fetch';
import { Client } from 'pg';
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
    private readonly localMirrorUrl = 'http://172.20.0.20:8080/pubmed';
    private readonly apiKey?: string;
    private useLocalMirror: boolean = true;

    constructor(apiKey?: string) {
        // Only set apiKey if it's a real key
        this.apiKey = apiKey && apiKey !== 'optional_for_higher_rate_limits' ? apiKey : undefined;
        // Check environment for local mirror preference
        this.useLocalMirror = process.env.USE_LOCAL_MEDICAL_MIRRORS !== 'false';
    } async getArticles(args: any, cache: CacheManager) {
        const { query, maxResults = 10 } = args;
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
                    text: JSON.stringify(articles, null, 2)
                }]
            };

            console.log('PubMed response prepared, content length:', response.content[0].text.length);
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

    async search(query: string, maxResults: number = 10): Promise<PubMedArticle[]> {
        return this.searchArticles(query, maxResults);
    }

    async searchArticles(query: string, maxResults: number = 10): Promise<PubMedArticle[]> {
        try {
            if (!query || typeof query !== 'string' || query.trim().length === 0) {
                throw new Error('PubMed search failed: Query string is empty or invalid.');
            }

            // Use database search first (since user has local PubMed data)
            try {
                console.log('Searching local PostgreSQL database for PubMed articles');
                return await this.searchDatabase(query, maxResults);
            } catch (dbError) {
                console.warn('Database search failed, trying mirror/external:', dbError);

                // Try local mirror second
                if (this.useLocalMirror) {
                    try {
                        console.log('Attempting to use local PubMed mirror');
                        return await this.searchLocalMirror(query, maxResults);
                    } catch (localError) {
                        console.warn('Local PubMed mirror failed, falling back to external API:', localError);
                        // Fall through to external API
                    }
                }

                console.log('Using external PubMed API');
                return await this.searchExternalAPI(query, maxResults);
            }
        } catch (error) {
            console.error('PubMed search failed:', error);
            throw error;
        }
    }

    private async searchLocalMirror(query: string, maxResults: number): Promise<PubMedArticle[]> {
        const response = await fetch(`${this.localMirrorUrl}/search?query=${encodeURIComponent(query)}&max_results=${maxResults}`);

        if (!response.ok) {
            throw new Error(`Local mirror responded with ${response.status}`);
        }

        const data = await response.json() as { content: Array<{ text: string }> };
        const articles = JSON.parse(data.content[0].text);

        return articles.map((article: any) => ({
            title: article.title || '',
            authors: article.authors || [],
            journal: article.journal || '',
            pubDate: article.pubDate || '',
            doi: article.doi || '',
            abstract: article.abstract || '',
            pmid: article.pmid || ''
        }));
    }

    private async searchDatabase(query: string, maxResults: number): Promise<PubMedArticle[]> {
        try {
            // Create a new connection for each query (simple approach)
            const client = new Client({
                host: process.env.POSTGRES_HOST || '172.20.0.13',
                port: parseInt(process.env.POSTGRES_PORT || '5432'),
                user: process.env.POSTGRES_USER || 'intelluxe',
                password: process.env.POSTGRES_PASSWORD || 'secure_password',
                database: process.env.DATABASE_NAME || 'intelluxe'
            });

            await client.connect();

            // Search the pubmed_articles table
            const searchQuery = `
                SELECT pmid, title, journal, pub_date, abstract, authors
                FROM pubmed_articles 
                WHERE title ILIKE $1 
                   OR abstract ILIKE $1 
                   OR journal ILIKE $1
                ORDER BY pub_date DESC
                LIMIT $2
            `;

            const searchTerm = `%${query}%`;
            console.log(`Executing database search for: "${query}" (limit: ${maxResults})`);

            const result = await client.query(searchQuery, [searchTerm, maxResults]);

            console.log(`Database search returned ${result.rows.length} articles`);

            const articles = result.rows.map((row: any) => ({
                pmid: row.pmid?.toString() || '',
                title: row.title || '',
                journal: row.journal || '',
                pubDate: row.pub_date || '',
                abstract: row.abstract || '',
                authors: row.authors ? (Array.isArray(row.authors) ? row.authors : [row.authors]) : [],
                doi: '' // Not stored in this table structure
            }));

            await client.end();
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