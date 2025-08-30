import { DatabaseConnector } from '../DatabaseConnector';
import { Logger } from '../../utils/logger';

export interface DDInterDrugInteraction {
    id: string;
    drug_a: string;
    drug_b: string;
    interaction_type: string;
    severity: string;
    evidence_level: string;
    mechanism: string;
    description: string;
    clinical_significance?: string;
    risk_rating?: string;
    management?: string;
    onset?: string;
    documentation?: string;
    drug_a_synonyms?: string[];
    drug_b_synonyms?: string[];
    references?: string[];
    last_updated?: string;
}

export interface DDInterDrugProfile {
    drug_name: string;
    synonyms?: string[];
    total_interactions: number;
    major_interactions: number;
    moderate_interactions: number;
    minor_interactions: number;
    contraindicated_interactions: number;
    common_interaction_partners?: string[];
}

export interface DDInterSearchParams {
    drugA?: string;
    drugB?: string;
    severity?: string;
    interactionType?: string;
    evidenceLevel?: string;
    mechanism?: string;
    maxResults?: number;
    includeMinor?: boolean;
}

export class DDInterConnector extends DatabaseConnector {
    private readonly interactionsTable = 'ddinter_drug_interactions';
    private readonly drugsTable = 'ddinter_drugs';
    private readonly logger = (Logger as any).getInstance('DDInterConnector');

    constructor() {
        super('ddinter_drug_interactions', ['drug1', 'drug2', 'severity']);
    }

    async searchDrugInteractions(params: DDInterSearchParams): Promise<DDInterDrugInteraction[]> {
        this.logger.info('Searching DDInter drug interactions', { params });

        try {
            let query = `
                SELECT 
                    id, drug_a, drug_b, interaction_type, severity, evidence_level,
                    mechanism, description, clinical_significance, risk_rating,
                    management, onset, documentation, drug_a_synonyms, drug_b_synonyms,
                    references, last_updated
                FROM ${this.interactionsTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.drugA) {
                query += ` AND (drug_a ILIKE $${paramIndex} OR drug_a_synonyms::text ILIKE $${paramIndex})`;
                queryParams.push(`%${params.drugA}%`);
                paramIndex++;
            }

            if (params.drugB) {
                query += ` AND (drug_b ILIKE $${paramIndex} OR drug_b_synonyms::text ILIKE $${paramIndex})`;
                queryParams.push(`%${params.drugB}%`);
                paramIndex++;
            }

            if (params.severity) {
                query += ` AND severity = $${paramIndex}`;
                queryParams.push(params.severity);
                paramIndex++;
            }

            if (params.interactionType) {
                query += ` AND interaction_type ILIKE $${paramIndex}`;
                queryParams.push(`%${params.interactionType}%`);
                paramIndex++;
            }

            if (params.evidenceLevel) {
                query += ` AND evidence_level = $${paramIndex}`;
                queryParams.push(params.evidenceLevel);
                paramIndex++;
            }

            if (params.mechanism) {
                query += ` AND mechanism ILIKE $${paramIndex}`;
                queryParams.push(`%${params.mechanism}%`);
                paramIndex++;
            }

            if (!params.includeMinor) {
                query += ` AND severity NOT IN ('minor', 'minimal')`;
            }

            query += ` ORDER BY 
                CASE severity
                    WHEN 'contraindicated' THEN 1
                    WHEN 'major' THEN 2
                    WHEN 'moderate' THEN 3
                    WHEN 'minor' THEN 4
                    WHEN 'minimal' THEN 5
                    ELSE 6
                END,
                drug_a ASC, drug_b ASC
            `;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const interactions: DDInterDrugInteraction[] = result.rows.map(row => ({
                id: row.id,
                drug_a: row.drug_a,
                drug_b: row.drug_b,
                interaction_type: row.interaction_type,
                severity: row.severity,
                evidence_level: row.evidence_level,
                mechanism: row.mechanism,
                description: row.description,
                clinical_significance: row.clinical_significance,
                risk_rating: row.risk_rating,
                management: row.management,
                onset: row.onset,
                documentation: row.documentation,
                drug_a_synonyms: row.drug_a_synonyms || [],
                drug_b_synonyms: row.drug_b_synonyms || [],
                references: row.references || [],
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${interactions.length} drug interactions`);
            return interactions;

        } catch (error) {
            this.logger.error('Error searching drug interactions', { error, params });
            throw new Error(`Failed to search drug interactions: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugInteractionsByDrug(drugName: string, includeMinor: boolean = false, maxResults: number = 100): Promise<DDInterDrugInteraction[]> {
        this.logger.info('Getting drug interactions by drug name', { drugName, includeMinor, maxResults });

        try {
            let query = `
                SELECT 
                    id, drug_a, drug_b, interaction_type, severity, evidence_level,
                    mechanism, description, clinical_significance, risk_rating,
                    management, onset, documentation, drug_a_synonyms, drug_b_synonyms,
                    references, last_updated
                FROM ${this.interactionsTable}
                WHERE (
                    drug_a ILIKE $1 OR drug_a_synonyms::text ILIKE $1 OR
                    drug_b ILIKE $1 OR drug_b_synonyms::text ILIKE $1
                )
            `;

            const queryParams: any[] = [`%${drugName}%`];
            let paramIndex = 2;

            if (!includeMinor) {
                query += ` AND severity NOT IN ('minor', 'minimal')`;
            }

            query += ` ORDER BY 
                CASE severity
                    WHEN 'contraindicated' THEN 1
                    WHEN 'major' THEN 2
                    WHEN 'moderate' THEN 3
                    WHEN 'minor' THEN 4
                    WHEN 'minimal' THEN 5
                    ELSE 6
                END,
                drug_a ASC, drug_b ASC
                LIMIT $${paramIndex}
            `;
            queryParams.push(maxResults);

            const result = await this.executeQuery(query, queryParams);
            
            const interactions: DDInterDrugInteraction[] = result.rows.map(row => ({
                id: row.id,
                drug_a: row.drug_a,
                drug_b: row.drug_b,
                interaction_type: row.interaction_type,
                severity: row.severity,
                evidence_level: row.evidence_level,
                mechanism: row.mechanism,
                description: row.description,
                clinical_significance: row.clinical_significance,
                risk_rating: row.risk_rating,
                management: row.management,
                onset: row.onset,
                documentation: row.documentation,
                drug_a_synonyms: row.drug_a_synonyms || [],
                drug_b_synonyms: row.drug_b_synonyms || [],
                references: row.references || [],
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${interactions.length} interactions for drug`);
            return interactions;

        } catch (error) {
            this.logger.error('Error getting drug interactions by drug', { error, drugName });
            throw new Error(`Failed to get drug interactions by drug: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async checkSpecificInteraction(drugA: string, drugB: string): Promise<DDInterDrugInteraction[]> {
        this.logger.info('Checking specific drug interaction', { drugA, drugB });

        try {
            const query = `
                SELECT 
                    id, drug_a, drug_b, interaction_type, severity, evidence_level,
                    mechanism, description, clinical_significance, risk_rating,
                    management, onset, documentation, drug_a_synonyms, drug_b_synonyms,
                    references, last_updated
                FROM ${this.interactionsTable}
                WHERE (
                    (drug_a ILIKE $1 OR drug_a_synonyms::text ILIKE $1) AND
                    (drug_b ILIKE $2 OR drug_b_synonyms::text ILIKE $2)
                ) OR (
                    (drug_a ILIKE $2 OR drug_a_synonyms::text ILIKE $2) AND
                    (drug_b ILIKE $1 OR drug_b_synonyms::text ILIKE $1)
                )
                ORDER BY 
                    CASE severity
                        WHEN 'contraindicated' THEN 1
                        WHEN 'major' THEN 2
                        WHEN 'moderate' THEN 3
                        WHEN 'minor' THEN 4
                        WHEN 'minimal' THEN 5
                        ELSE 6
                    END
            `;

            const result = await this.executeQuery(query, [`%${drugA}%`, `%${drugB}%`]);
            
            const interactions: DDInterDrugInteraction[] = result.rows.map(row => ({
                id: row.id,
                drug_a: row.drug_a,
                drug_b: row.drug_b,
                interaction_type: row.interaction_type,
                severity: row.severity,
                evidence_level: row.evidence_level,
                mechanism: row.mechanism,
                description: row.description,
                clinical_significance: row.clinical_significance,
                risk_rating: row.risk_rating,
                management: row.management,
                onset: row.onset,
                documentation: row.documentation,
                drug_a_synonyms: row.drug_a_synonyms || [],
                drug_b_synonyms: row.drug_b_synonyms || [],
                references: row.references || [],
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${interactions.length} interactions between drugs`);
            return interactions;

        } catch (error) {
            this.logger.error('Error checking specific interaction', { error, drugA, drugB });
            throw new Error(`Failed to check specific interaction: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugProfile(drugName: string): Promise<DDInterDrugProfile | null> {
        this.logger.info('Getting drug interaction profile', { drugName });

        try {
            const query = `
                SELECT 
                    COALESCE(drug_a, drug_b) as drug_name,
                    COUNT(*) as total_interactions,
                    COUNT(CASE WHEN severity = 'major' THEN 1 END) as major_interactions,
                    COUNT(CASE WHEN severity = 'moderate' THEN 1 END) as moderate_interactions,
                    COUNT(CASE WHEN severity = 'minor' THEN 1 END) as minor_interactions,
                    COUNT(CASE WHEN severity = 'contraindicated' THEN 1 END) as contraindicated_interactions,
                    array_agg(DISTINCT 
                        CASE 
                            WHEN drug_a ILIKE $1 THEN drug_b 
                            ELSE drug_a 
                        END
                    ) FILTER (WHERE severity IN ('major', 'moderate', 'contraindicated')) as common_partners
                FROM ${this.interactionsTable}
                WHERE drug_a ILIKE $1 OR drug_a_synonyms::text ILIKE $1 OR
                      drug_b ILIKE $1 OR drug_b_synonyms::text ILIKE $1
                GROUP BY COALESCE(drug_a, drug_b)
                ORDER BY total_interactions DESC
                LIMIT 1
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);

            if (result.rows.length === 0) {
                this.logger.info('No drug profile found', { drugName });
                return null;
            }

            const row = result.rows[0];
            const profile: DDInterDrugProfile = {
                drug_name: drugName,
                total_interactions: parseInt(row.total_interactions),
                major_interactions: parseInt(row.major_interactions),
                moderate_interactions: parseInt(row.moderate_interactions),
                minor_interactions: parseInt(row.minor_interactions),
                contraindicated_interactions: parseInt(row.contraindicated_interactions),
                common_interaction_partners: row.common_partners?.slice(0, 10) || [],
            };

            this.logger.info('Found drug interaction profile');
            return profile;

        } catch (error) {
            this.logger.error('Error getting drug profile', { error, drugName });
            throw new Error(`Failed to get drug profile: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getInteractionsByMechanism(mechanism: string, maxResults: number = 50): Promise<DDInterDrugInteraction[]> {
        this.logger.info('Getting interactions by mechanism', { mechanism, maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_a, drug_b, interaction_type, severity, evidence_level,
                    mechanism, description, clinical_significance, risk_rating,
                    management, onset, documentation, drug_a_synonyms, drug_b_synonyms,
                    references, last_updated
                FROM ${this.interactionsTable}
                WHERE mechanism ILIKE $1
                ORDER BY 
                    CASE severity
                        WHEN 'contraindicated' THEN 1
                        WHEN 'major' THEN 2
                        WHEN 'moderate' THEN 3
                        WHEN 'minor' THEN 4
                        WHEN 'minimal' THEN 5
                        ELSE 6
                    END,
                    drug_a ASC, drug_b ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${mechanism}%`, maxResults]);
            
            const interactions: DDInterDrugInteraction[] = result.rows.map(row => ({
                id: row.id,
                drug_a: row.drug_a,
                drug_b: row.drug_b,
                interaction_type: row.interaction_type,
                severity: row.severity,
                evidence_level: row.evidence_level,
                mechanism: row.mechanism,
                description: row.description,
                clinical_significance: row.clinical_significance,
                risk_rating: row.risk_rating,
                management: row.management,
                onset: row.onset,
                documentation: row.documentation,
                drug_a_synonyms: row.drug_a_synonyms || [],
                drug_b_synonyms: row.drug_b_synonyms || [],
                references: row.references || [],
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${interactions.length} interactions by mechanism`);
            return interactions;

        } catch (error) {
            this.logger.error('Error getting interactions by mechanism', { error, mechanism });
            throw new Error(`Failed to get interactions by mechanism: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getHighRiskInteractions(maxResults: number = 100): Promise<DDInterDrugInteraction[]> {
        this.logger.info('Getting high-risk drug interactions', { maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_a, drug_b, interaction_type, severity, evidence_level,
                    mechanism, description, clinical_significance, risk_rating,
                    management, onset, documentation, drug_a_synonyms, drug_b_synonyms,
                    references, last_updated
                FROM ${this.interactionsTable}
                WHERE severity IN ('contraindicated', 'major')
                AND evidence_level IN ('established', 'probable')
                ORDER BY 
                    CASE severity
                        WHEN 'contraindicated' THEN 1
                        WHEN 'major' THEN 2
                        ELSE 3
                    END,
                    CASE evidence_level
                        WHEN 'established' THEN 1
                        WHEN 'probable' THEN 2
                        ELSE 3
                    END,
                    drug_a ASC, drug_b ASC
                LIMIT $1
            `;

            const result = await this.executeQuery(query, [maxResults]);
            
            const interactions: DDInterDrugInteraction[] = result.rows.map(row => ({
                id: row.id,
                drug_a: row.drug_a,
                drug_b: row.drug_b,
                interaction_type: row.interaction_type,
                severity: row.severity,
                evidence_level: row.evidence_level,
                mechanism: row.mechanism,
                description: row.description,
                clinical_significance: row.clinical_significance,
                risk_rating: row.risk_rating,
                management: row.management,
                onset: row.onset,
                documentation: row.documentation,
                drug_a_synonyms: row.drug_a_synonyms || [],
                drug_b_synonyms: row.drug_b_synonyms || [],
                references: row.references || [],
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${interactions.length} high-risk interactions`);
            return interactions;

        } catch (error) {
            this.logger.error('Error getting high-risk interactions', { error });
            throw new Error(`Failed to get high-risk interactions: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getInteractionStatistics(): Promise<any> {
        this.logger.info('Getting interaction statistics');

        try {
            const query = `
                SELECT 
                    COUNT(*) as total_interactions,
                    COUNT(CASE WHEN severity = 'contraindicated' THEN 1 END) as contraindicated_count,
                    COUNT(CASE WHEN severity = 'major' THEN 1 END) as major_count,
                    COUNT(CASE WHEN severity = 'moderate' THEN 1 END) as moderate_count,
                    COUNT(CASE WHEN severity = 'minor' THEN 1 END) as minor_count,
                    COUNT(DISTINCT drug_a) + COUNT(DISTINCT drug_b) as unique_drugs,
                    COUNT(DISTINCT mechanism) as unique_mechanisms,
                    COUNT(CASE WHEN evidence_level = 'established' THEN 1 END) as established_evidence,
                    COUNT(CASE WHEN evidence_level = 'probable' THEN 1 END) as probable_evidence
                FROM ${this.interactionsTable}
            `;

            const result = await this.executeQuery(query, []);
            
            if (result.rows.length === 0) {
                return null;
            }

            const row = result.rows[0];
            const stats = {
                total_interactions: parseInt(row.total_interactions),
                severity_breakdown: {
                    contraindicated: parseInt(row.contraindicated_count),
                    major: parseInt(row.major_count),
                    moderate: parseInt(row.moderate_count),
                    minor: parseInt(row.minor_count),
                },
                unique_drugs: parseInt(row.unique_drugs),
                unique_mechanisms: parseInt(row.unique_mechanisms),
                evidence_breakdown: {
                    established: parseInt(row.established_evidence),
                    probable: parseInt(row.probable_evidence),
                },
            };

            this.logger.info('Generated interaction statistics');
            return stats;

        } catch (error) {
            this.logger.error('Error getting interaction statistics', { error });
            throw new Error(`Failed to get interaction statistics: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async searchPolypharmacyInteractions(drugList: string[], includeMinor: boolean = false): Promise<any> {
        this.logger.info('Searching polypharmacy interactions', { drugCount: drugList.length, includeMinor });

        try {
            if (drugList.length < 2) {
                throw new Error('At least 2 drugs required for polypharmacy analysis');
            }

            const interactions: DDInterDrugInteraction[] = [];
            const drugPairs: Array<[string, string]> = [];

            // Generate all possible drug pairs
            for (let i = 0; i < drugList.length; i++) {
                for (let j = i + 1; j < drugList.length; j++) {
                    drugPairs.push([drugList[i], drugList[j]]);
                }
            }

            // Check interactions for each pair
            for (const [drugA, drugB] of drugPairs) {
                const pairInteractions = await this.checkSpecificInteraction(drugA, drugB);
                
                if (!includeMinor) {
                    const filteredInteractions = pairInteractions.filter(
                        interaction => !['minor', 'minimal'].includes(interaction.severity)
                    );
                    interactions.push(...filteredInteractions);
                } else {
                    interactions.push(...pairInteractions);
                }
            }

            // Analyze results
            const analysis = {
                total_drugs: drugList.length,
                total_interactions: interactions.length,
                high_risk_interactions: interactions.filter(i => ['contraindicated', 'major'].includes(i.severity)).length,
                moderate_risk_interactions: interactions.filter(i => i.severity === 'moderate').length,
                unique_mechanisms: [...new Set(interactions.map(i => i.mechanism))].length,
                interactions_by_severity: {
                    contraindicated: interactions.filter(i => i.severity === 'contraindicated').length,
                    major: interactions.filter(i => i.severity === 'major').length,
                    moderate: interactions.filter(i => i.severity === 'moderate').length,
                    minor: interactions.filter(i => i.severity === 'minor').length,
                },
                detailed_interactions: interactions.sort((a, b) => {
                    const severityOrder: Record<string, number> = { contraindicated: 1, major: 2, moderate: 3, minor: 4, minimal: 5 };
                    return (severityOrder[a.severity] || 999) - (severityOrder[b.severity] || 999);
                }),
            };

            this.logger.info(`Completed polypharmacy analysis: ${interactions.length} interactions found`);
            return analysis;

        } catch (error) {
            this.logger.error('Error searching polypharmacy interactions', { error, drugCount: drugList.length });
            throw new Error(`Failed to search polypharmacy interactions: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}