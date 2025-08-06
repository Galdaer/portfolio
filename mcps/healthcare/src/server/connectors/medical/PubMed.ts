import fetch from 'node-fetch';
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

    constructor(apiKey?: string) {
        // Only set apiKey if it's a real key
        this.apiKey = apiKey && apiKey !== 'optional_for_higher_rate_limits' ? apiKey : undefined;
    }

    async getArticles(args: any, cache: CacheManager) {
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