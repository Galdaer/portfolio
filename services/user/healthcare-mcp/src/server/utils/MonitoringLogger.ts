export interface DataSourceMetrics {
    source_type: 'database' | 'external' | 'mixed';
    connector_name: string;
    query_type: string;
    response_time_ms: number;
    results_count: number;
    success: boolean;
    error_message?: string;
    timestamp: Date;
}

export interface PerformanceMetrics {
    database_queries: number;
    external_api_calls: number;
    cache_hits: number;
    cache_misses: number;
    average_db_response_time: number;
    average_api_response_time: number;
    total_requests: number;
    error_count: number;
}

export class MonitoringLogger {
    private metrics: DataSourceMetrics[] = [];
    private performanceCounters: PerformanceMetrics = {
        database_queries: 0,
        external_api_calls: 0,
        cache_hits: 0,
        cache_misses: 0,
        average_db_response_time: 0,
        average_api_response_time: 0,
        total_requests: 0,
        error_count: 0
    };
    private isEnabled: boolean;

    constructor() {
        this.isEnabled = process.env.ENABLE_PERFORMANCE_MONITORING !== 'false';
        
        if (this.isEnabled) {
            console.log('[MonitoringLogger] Performance monitoring enabled');
            // Log summary every 5 minutes
            setInterval(() => this.logPerformanceSummary(), 300000);
        }
    }

    logDataSourceUsage(metrics: DataSourceMetrics): void {
        if (!this.isEnabled) return;

        // Store individual metrics
        this.metrics.push(metrics);
        
        // Update performance counters
        this.performanceCounters.total_requests++;
        
        if (metrics.source_type === 'database') {
            this.performanceCounters.database_queries++;
            this.updateAverageResponseTime('database', metrics.response_time_ms);
        } else if (metrics.source_type === 'external') {
            this.performanceCounters.external_api_calls++;
            this.updateAverageResponseTime('external', metrics.response_time_ms);
        }
        
        if (!metrics.success) {
            this.performanceCounters.error_count++;
        }

        // Log significant events
        if (metrics.response_time_ms > 5000) {
            console.warn(`[MonitoringLogger] Slow query detected: ${metrics.connector_name} took ${metrics.response_time_ms}ms`);
        }

        if (!metrics.success && metrics.error_message) {
            console.error(`[MonitoringLogger] ${metrics.connector_name} error: ${metrics.error_message}`);
        }

        if (process.env.LOG_LEVEL === 'debug') {
            console.debug(`[MonitoringLogger] ${metrics.connector_name}(${metrics.query_type}): ${metrics.source_type} source, ${metrics.response_time_ms}ms, ${metrics.results_count} results`);
        }

        // Keep only last 1000 metrics to prevent memory bloat
        if (this.metrics.length > 1000) {
            this.metrics = this.metrics.slice(-500);
        }
    }

    logCacheUsage(hit: boolean): void {
        if (!this.isEnabled) return;

        if (hit) {
            this.performanceCounters.cache_hits++;
        } else {
            this.performanceCounters.cache_misses++;
        }
    }

    logHealthCheck(service: string, success: boolean, responseTime: number, details?: string): void {
        if (!this.isEnabled) return;

        const status = success ? 'HEALTHY' : 'UNHEALTHY';
        const message = details ? ` - ${details}` : '';
        
        console.log(`[MonitoringLogger] Health Check: ${service} is ${status} (${responseTime}ms)${message}`);
        
        if (!success) {
            this.performanceCounters.error_count++;
        }
    }

    logConnectionPoolStats(stats: any): void {
        if (!this.isEnabled) return;

        console.log(`[MonitoringLogger] DB Pool Stats: Active: ${stats.activeConnections}, Total: ${stats.totalConnections}, Errors: ${stats.errorCount}`);
    }

    private updateAverageResponseTime(type: 'database' | 'external', responseTime: number): void {
        if (type === 'database') {
            const oldAvg = this.performanceCounters.average_db_response_time;
            const count = this.performanceCounters.database_queries;
            this.performanceCounters.average_db_response_time = ((oldAvg * (count - 1)) + responseTime) / count;
        } else {
            const oldAvg = this.performanceCounters.average_api_response_time;
            const count = this.performanceCounters.external_api_calls;
            this.performanceCounters.average_api_response_time = ((oldAvg * (count - 1)) + responseTime) / count;
        }
    }

    private logPerformanceSummary(): void {
        const summary = {
            ...this.performanceCounters,
            cache_hit_rate: this.getCacheHitRate(),
            database_preference_rate: this.getDatabasePreferenceRate(),
            error_rate: this.getErrorRate()
        };

        console.log('[MonitoringLogger] Performance Summary:', JSON.stringify(summary, null, 2));
    }

    private getCacheHitRate(): number {
        const total = this.performanceCounters.cache_hits + this.performanceCounters.cache_misses;
        return total > 0 ? (this.performanceCounters.cache_hits / total) * 100 : 0;
    }

    private getDatabasePreferenceRate(): number {
        const total = this.performanceCounters.database_queries + this.performanceCounters.external_api_calls;
        return total > 0 ? (this.performanceCounters.database_queries / total) * 100 : 0;
    }

    private getErrorRate(): number {
        return this.performanceCounters.total_requests > 0 
            ? (this.performanceCounters.error_count / this.performanceCounters.total_requests) * 100 
            : 0;
    }

    getMetrics(): DataSourceMetrics[] {
        return [...this.metrics];
    }

    getPerformanceCounters(): PerformanceMetrics & { cache_hit_rate: number; database_preference_rate: number; error_rate: number } {
        return {
            ...this.performanceCounters,
            cache_hit_rate: this.getCacheHitRate(),
            database_preference_rate: this.getDatabasePreferenceRate(),
            error_rate: this.getErrorRate()
        };
    }

    reset(): void {
        this.metrics = [];
        this.performanceCounters = {
            database_queries: 0,
            external_api_calls: 0,
            cache_hits: 0,
            cache_misses: 0,
            average_db_response_time: 0,
            average_api_response_time: 0,
            total_requests: 0,
            error_count: 0
        };
        console.log('[MonitoringLogger] Metrics reset');
    }
}

// Singleton instance
export const monitoringLogger = new MonitoringLogger();