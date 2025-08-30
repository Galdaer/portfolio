/**
 * Healthcare MCP Logger Utility
 * Provides consistent logging with PHI protection
 */

export enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3,
    FATAL = 4
}

export class Logger {
    private name: string;
    private level: LogLevel;
    private enablePHIProtection: boolean;

    constructor(name: string) {
        this.name = name;
        this.level = this.getLogLevelFromEnv();
        this.enablePHIProtection = process.env.PHI_PROTECTION !== 'false';
    }

    private getLogLevelFromEnv(): LogLevel {
        const envLevel = process.env.LOG_LEVEL?.toUpperCase();
        switch (envLevel) {
            case 'DEBUG': return LogLevel.DEBUG;
            case 'INFO': return LogLevel.INFO;
            case 'WARN': return LogLevel.WARN;
            case 'ERROR': return LogLevel.ERROR;
            case 'FATAL': return LogLevel.FATAL;
            default: return LogLevel.INFO;
        }
    }

    private sanitizePHI(message: string): string {
        if (!this.enablePHIProtection) return message;
        
        // Redact potential PHI patterns
        let sanitized = message;
        
        // SSN pattern
        sanitized = sanitized.replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[SSN-REDACTED]');
        
        // MRN pattern (assuming 6-10 digits)
        sanitized = sanitized.replace(/\bMRN[:\s]*\d{6,10}\b/gi, '[MRN-REDACTED]');
        
        // Date of birth patterns
        sanitized = sanitized.replace(/\b(DOB|DateOfBirth)[:\s]*[\d\-\/]+\b/gi, '[DOB-REDACTED]');
        
        // Phone numbers
        sanitized = sanitized.replace(/\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b/g, '[PHONE-REDACTED]');
        
        // Email addresses
        sanitized = sanitized.replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL-REDACTED]');
        
        return sanitized;
    }

    private formatMessage(level: string, message: string, data?: any): string {
        const timestamp = new Date().toISOString();
        const sanitizedMessage = this.sanitizePHI(message);
        
        let formattedMessage = `[${timestamp}] [${level}] [${this.name}] ${sanitizedMessage}`;
        
        if (data) {
            const sanitizedData = this.enablePHIProtection ? 
                JSON.stringify(data, null, 2).replace(/["']?\b\w+["']?\s*:\s*["']?[^"',}\]]+/g, (match) => {
                    if (match.toLowerCase().includes('name') || 
                        match.toLowerCase().includes('patient') ||
                        match.toLowerCase().includes('address')) {
                        return match.replace(/:\s*["']?[^"',}\]]+/, ': "[REDACTED]"');
                    }
                    return match;
                }) : 
                JSON.stringify(data, null, 2);
            formattedMessage += `\n${sanitizedData}`;
        }
        
        return formattedMessage;
    }

    debug(message: string, data?: any): void {
        if (this.level <= LogLevel.DEBUG) {
            console.debug(this.formatMessage('DEBUG', message, data));
        }
    }

    info(message: string, data?: any): void {
        if (this.level <= LogLevel.INFO) {
            console.info(this.formatMessage('INFO', message, data));
        }
    }

    warn(message: string, data?: any): void {
        if (this.level <= LogLevel.WARN) {
            console.warn(this.formatMessage('WARN', message, data));
        }
    }

    error(message: string, error?: Error | any, data?: any): void {
        if (this.level <= LogLevel.ERROR) {
            const errorData = error instanceof Error ? {
                message: error.message,
                stack: this.enablePHIProtection ? '[STACK-REDACTED]' : error.stack,
                ...data
            } : { error, ...data };
            
            console.error(this.formatMessage('ERROR', message, errorData));
        }
    }

    fatal(message: string, error?: Error | any, data?: any): void {
        if (this.level <= LogLevel.FATAL) {
            const errorData = error instanceof Error ? {
                message: error.message,
                stack: this.enablePHIProtection ? '[STACK-REDACTED]' : error.stack,
                ...data
            } : { error, ...data };
            
            console.error(this.formatMessage('FATAL', message, errorData));
            
            // In production, you might want to trigger alerts or shutdown
            if (process.env.NODE_ENV === 'production') {
                // Trigger alert system
                // process.exit(1);
            }
        }
    }

    /**
     * Create a child logger with a sub-context
     */
    child(context: string): Logger {
        return new Logger(`${this.name}:${context}`);
    }
}

// Default logger instance
export const logger = new Logger('healthcare-mcp');

// Export factory function
export function createLogger(name: string): Logger {
    return new Logger(name);
}

// Static getInstance method for compatibility
export class LoggerFactory {
    private static instances = new Map<string, Logger>();
    
    static getInstance(name: string): Logger {
        if (!this.instances.has(name)) {
            this.instances.set(name, new Logger(name));
        }
        return this.instances.get(name)!;
    }
}

// Add getInstance to Logger class for compatibility
(Logger as any).getInstance = (name: string) => LoggerFactory.getInstance(name);

export default logger;