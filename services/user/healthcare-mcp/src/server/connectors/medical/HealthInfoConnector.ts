import fetch from 'node-fetch';
import { DatabaseManager } from '../../utils/DatabaseManager.js';
import { CacheManager } from '../../utils/Cache.js';

export interface HealthTopic {
    id: string;
    title: string;
    summary: string;
    category: string;
    url?: string;
    source: 'database' | 'external';
}

export interface Exercise {
    id: string;
    name: string;
    description: string;
    category: string;
    muscle_groups: string[];
    difficulty_level?: string;
    instructions?: string[];
    source: 'database' | 'external';
}

export interface FoodItem {
    id: string;
    name: string;
    category: string;
    nutrients: {
        calories?: number;
        protein?: number;
        carbs?: number;
        fat?: number;
        fiber?: number;
        [key: string]: any;
    };
    serving_size?: string;
    source: 'database' | 'external';
}

export interface HealthSearchResponse {
    health_topics?: HealthTopic[];
    exercises?: Exercise[];
    food_items?: FoodItem[];
    total_results: number;
    search_query: string;
    source_used: 'database' | 'external' | 'mixed';
}

export class HealthInfoConnector {
    private readonly healthFinderUrl = 'https://healthfinder.gov/api/v2/topicsearch.json';
    private readonly exerciseDbUrl = 'https://exercisedb.p.rapidapi.com';
    private readonly usdaFoodUrl = 'https://api.nal.usda.gov/fdc/v1/foods/search';
    private dbManager: DatabaseManager;

    constructor(dbManager: DatabaseManager) {
        this.dbManager = dbManager;
    }

    async searchHealthTopics(args: any, cache?: CacheManager): Promise<any> {
        const { query, max_results = 10 } = args;
        
        if (!query || typeof query !== 'string' || query.trim().length === 0) {
            throw new Error('Query is required and must be a non-empty string');
        }

        const maxResults = Math.max(1, Math.min(100, Number(max_results)));
        const cacheKey = cache?.createKey('health_topics', { query, maxResults });

        try {
            console.log('Health topics search called with:', { query, maxResults });

            const searchResults = await (cache && cacheKey
                ? cache.getOrFetch(cacheKey, () => this.performHealthTopicsSearch(query, maxResults))
                : this.performHealthTopicsSearch(query, maxResults)
            );

            console.log('Health topics search results:', searchResults.health_topics?.length || 0, 'topics found');

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        health_topics: searchResults.health_topics || [],
                        total_results: searchResults.total_results,
                        search_query: searchResults.search_query,
                        source_used: searchResults.source_used
                    }, null, 2)
                }]
            };
        } catch (error) {
            console.error('Health topics search error:', error);
            return {
                content: [{
                    type: 'text',
                    text: `Error executing health topics search: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    async searchExercises(args: any, cache?: CacheManager): Promise<any> {
        const { query, muscle_group, max_results = 10 } = args;
        
        if (!query || typeof query !== 'string' || query.trim().length === 0) {
            throw new Error('Query is required and must be a non-empty string');
        }

        const maxResults = Math.max(1, Math.min(100, Number(max_results)));
        const cacheKey = cache?.createKey('exercises', { query, muscle_group, maxResults });

        try {
            console.log('Exercise search called with:', { query, muscle_group, maxResults });

            const searchResults = await (cache && cacheKey
                ? cache.getOrFetch(cacheKey, () => this.performExerciseSearch(query, maxResults, muscle_group))
                : this.performExerciseSearch(query, maxResults, muscle_group)
            );

            console.log('Exercise search results:', searchResults.exercises?.length || 0, 'exercises found');

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        exercises: searchResults.exercises || [],
                        total_results: searchResults.total_results,
                        search_query: searchResults.search_query,
                        source_used: searchResults.source_used
                    }, null, 2)
                }]
            };
        } catch (error) {
            console.error('Exercise search error:', error);
            return {
                content: [{
                    type: 'text',
                    text: `Error executing exercise search: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    async searchFoodItems(args: any, cache?: CacheManager): Promise<any> {
        const { query, max_results = 10 } = args;
        
        if (!query || typeof query !== 'string' || query.trim().length === 0) {
            throw new Error('Query is required and must be a non-empty string');
        }

        const maxResults = Math.max(1, Math.min(100, Number(max_results)));
        const cacheKey = cache?.createKey('food_items', { query, maxResults });

        try {
            console.log('Food items search called with:', { query, maxResults });

            const searchResults = await (cache && cacheKey
                ? cache.getOrFetch(cacheKey, () => this.performFoodSearch(query, maxResults))
                : this.performFoodSearch(query, maxResults)
            );

            console.log('Food search results:', searchResults.food_items?.length || 0, 'food items found');

            return {
                content: [{
                    type: 'text',
                    text: JSON.stringify({
                        food_items: searchResults.food_items || [],
                        total_results: searchResults.total_results,
                        search_query: searchResults.search_query,
                        source_used: searchResults.source_used
                    }, null, 2)
                }]
            };
        } catch (error) {
            console.error('Food search error:', error);
            return {
                content: [{
                    type: 'text',
                    text: `Error executing food search: ${error instanceof Error ? error.message : 'Unknown error'}`
                }],
                isError: true
            };
        }
    }

    private async performHealthTopicsSearch(query: string, maxResults: number): Promise<HealthSearchResponse> {
        try {
            // DATABASE-FIRST: Try database search immediately
            if (this.dbManager.isAvailable()) {
                console.log('Searching health topics in PostgreSQL database');
                
                const dbResults = await this.searchHealthTopicsDatabase(query, maxResults);
                
                // Start background validation of external API (don't await)
                this.validateHealthFinderAPI(query, maxResults).catch(error => {
                    console.warn('Background HealthFinder API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.health_topics?.length || 0} health topics, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, falling back to HealthFinder API');
                return await this.searchHealthTopicsExternal(query, maxResults);
            }

            throw new Error('Neither database nor external API available for health topics search');

        } catch (error) {
            console.error('Health topics search failed:', error);
            throw error;
        }
    }

    private async performExerciseSearch(query: string, maxResults: number, muscleGroup?: string): Promise<HealthSearchResponse> {
        try {
            // DATABASE-FIRST: Try database search immediately
            if (this.dbManager.isAvailable()) {
                console.log('Searching exercises in PostgreSQL database');
                
                const dbResults = await this.searchExercisesDatabase(query, maxResults, muscleGroup);
                
                // Start background validation (mock for now, as ExerciseDB requires API key)
                this.validateExerciseAPI().catch(error => {
                    console.warn('Background Exercise API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.exercises?.length || 0} exercises, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable (limited without API key)
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, exercise external API requires configuration');
                return {
                    exercises: [],
                    total_results: 0,
                    search_query: query,
                    source_used: 'external'
                };
            }

            throw new Error('Neither database nor external API available for exercise search');

        } catch (error) {
            console.error('Exercise search failed:', error);
            throw error;
        }
    }

    private async performFoodSearch(query: string, maxResults: number): Promise<HealthSearchResponse> {
        try {
            // DATABASE-FIRST: Try database search immediately
            if (this.dbManager.isAvailable()) {
                console.log('Searching food items in PostgreSQL database');
                
                const dbResults = await this.searchFoodDatabase(query, maxResults);
                
                // Start background validation (would require USDA API key)
                this.validateFoodAPI().catch(error => {
                    console.warn('Background Food API validation failed:', error);
                });

                console.log(`Database returned ${dbResults.food_items?.length || 0} food items, background external validation started`);
                return dbResults;
            }

            // FALLBACK: Use external API if database unavailable (requires API key)
            if (this.dbManager.canFallback()) {
                console.warn('Database unavailable, food external API requires configuration');
                return {
                    food_items: [],
                    total_results: 0,
                    search_query: query,
                    source_used: 'external'
                };
            }

            throw new Error('Neither database nor external API available for food search');

        } catch (error) {
            console.error('Food search failed:', error);
            throw error;
        }
    }

    private async searchHealthTopicsDatabase(query: string, maxResults: number): Promise<HealthSearchResponse> {
        try {
            const searchQuery = `
                SELECT id, title, summary, category, url,
                       ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                FROM health_topics
                WHERE search_vector @@ plainto_tsquery('english', $1)
                   OR title ILIKE $2
                   OR summary ILIKE $2
                ORDER BY rank DESC, title
                LIMIT $3
            `;
            const searchTerm = `%${query}%`;
            const searchParams = [query, searchTerm, maxResults];

            const result = await this.dbManager.query(searchQuery, searchParams);
            
            console.log(`Database search returned ${result.rows.length} health topics`);

            const health_topics: HealthTopic[] = result.rows.map((row: any) => ({
                id: row.id || '',
                title: row.title || '',
                summary: row.summary || '',
                category: row.category || '',
                url: row.url || null,
                source: 'database' as const
            }));

            return {
                health_topics,
                total_results: health_topics.length,
                search_query: query,
                source_used: 'database'
            };

        } catch (error) {
            console.error('Database health topics search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async searchExercisesDatabase(query: string, maxResults: number, muscleGroup?: string): Promise<HealthSearchResponse> {
        try {
            let searchQuery: string;
            let searchParams: any[];

            if (muscleGroup) {
                searchQuery = `
                    SELECT id, name, description, category, muscle_groups, difficulty_level, instructions,
                           ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                    FROM exercises
                    WHERE (search_vector @@ plainto_tsquery('english', $1)
                           OR name ILIKE $2
                           OR description ILIKE $2)
                      AND $3 = ANY(muscle_groups)
                    ORDER BY rank DESC, name
                    LIMIT $4
                `;
                const searchTerm = `%${query}%`;
                searchParams = [query, searchTerm, muscleGroup, maxResults];
            } else {
                searchQuery = `
                    SELECT id, name, description, category, muscle_groups, difficulty_level, instructions,
                           ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                    FROM exercises
                    WHERE search_vector @@ plainto_tsquery('english', $1)
                       OR name ILIKE $2
                       OR description ILIKE $2
                    ORDER BY rank DESC, name
                    LIMIT $3
                `;
                const searchTerm = `%${query}%`;
                searchParams = [query, searchTerm, maxResults];
            }

            const result = await this.dbManager.query(searchQuery, searchParams);
            
            console.log(`Database search returned ${result.rows.length} exercises`);

            const exercises: Exercise[] = result.rows.map((row: any) => ({
                id: row.id || '',
                name: row.name || '',
                description: row.description || '',
                category: row.category || '',
                muscle_groups: row.muscle_groups || [],
                difficulty_level: row.difficulty_level || null,
                instructions: row.instructions || [],
                source: 'database' as const
            }));

            return {
                exercises,
                total_results: exercises.length,
                search_query: query,
                source_used: 'database'
            };

        } catch (error) {
            console.error('Database exercises search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async searchFoodDatabase(query: string, maxResults: number): Promise<HealthSearchResponse> {
        try {
            const searchQuery = `
                SELECT id, name, category, nutrients, serving_size,
                       ts_rank_cd(search_vector, plainto_tsquery('english', $1)) as rank
                FROM food_items
                WHERE search_vector @@ plainto_tsquery('english', $1)
                   OR name ILIKE $2
                   OR category ILIKE $2
                ORDER BY rank DESC, name
                LIMIT $3
            `;
            const searchTerm = `%${query}%`;
            const searchParams = [query, searchTerm, maxResults];

            const result = await this.dbManager.query(searchQuery, searchParams);
            
            console.log(`Database search returned ${result.rows.length} food items`);

            const food_items: FoodItem[] = result.rows.map((row: any) => ({
                id: row.id || '',
                name: row.name || '',
                category: row.category || '',
                nutrients: row.nutrients || {},
                serving_size: row.serving_size || null,
                source: 'database' as const
            }));

            return {
                food_items,
                total_results: food_items.length,
                search_query: query,
                source_used: 'database'
            };

        } catch (error) {
            console.error('Database food search error:', error);
            throw new Error(`Database search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async searchHealthTopicsExternal(query: string, maxResults: number): Promise<HealthSearchResponse> {
        try {
            const url = new URL(this.healthFinderUrl);
            url.searchParams.append('keyword', query);
            url.searchParams.append('limit', maxResults.toString());

            console.log('HealthFinder API search URL:', url.toString());

            const response = await fetch(url.toString(), {
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Intelluxe-Healthcare-MCP/1.0'
                }
            });

            if (!response.ok) {
                throw new Error(`HealthFinder API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json() as any;
            
            const health_topics: HealthTopic[] = [];
            
            if (data.Result && data.Result.Resources && Array.isArray(data.Result.Resources)) {
                for (const resource of data.Result.Resources.slice(0, maxResults)) {
                    health_topics.push({
                        id: resource.Id || '',
                        title: resource.Title || '',
                        summary: resource.Abstract || '',
                        category: resource.Categories?.[0]?.Name || 'General',
                        url: resource.AccessibleVersion || '',
                        source: 'external'
                    });
                }
            }

            console.log(`External HealthFinder API returned ${health_topics.length} health topics`);

            return {
                health_topics,
                total_results: health_topics.length,
                search_query: query,
                source_used: 'external'
            };

        } catch (error) {
            console.error('External HealthFinder API search error:', error);
            throw new Error(`External API search failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    // Background validation methods
    private async validateHealthFinderAPI(query: string, maxResults: number): Promise<void> {
        const timeout = 10000;

        try {
            console.log('[BACKGROUND] Testing external HealthFinder API connectivity...');

            const externalPromise = Promise.race([
                this.searchHealthTopicsExternal(query, Math.min(maxResults, 5)),
                new Promise<never>((_, reject) =>
                    setTimeout(() => reject(new Error('External API timeout')), timeout)
                )
            ]);

            const externalResults = await externalPromise;
            console.log(`[BACKGROUND] ✅ External HealthFinder API healthy - returned ${externalResults.health_topics?.length || 0} topics`);

        } catch (externalError) {
            console.warn(`[BACKGROUND] ⚠️  External HealthFinder API failed: ${externalError instanceof Error ? externalError.message : 'Unknown error'}`);
        }
    }

    private async validateExerciseAPI(): Promise<void> {
        try {
            console.log('[BACKGROUND] Exercise API validation - would require API key configuration');
            console.log(`[BACKGROUND] ⚠️  Exercise API requires RAPIDAPI_KEY environment variable`);
        } catch (error) {
            console.warn(`[BACKGROUND] ⚠️  Exercise API validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private async validateFoodAPI(): Promise<void> {
        try {
            console.log('[BACKGROUND] Food API validation - would require USDA API key configuration');
            console.log(`[BACKGROUND] ⚠️  USDA Food API requires USDA_API_KEY environment variable`);
        } catch (error) {
            console.warn(`[BACKGROUND] ⚠️  Food API validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}