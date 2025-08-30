import { DatabaseConnector } from '../DatabaseConnector';
import { Logger } from '../../utils/logger';

export interface FAERSAdverseEvent {
    id: string;
    report_id: string;
    drug_name: string;
    generic_name?: string;
    brand_name?: string;
    ndc?: string;
    indication?: string;
    dosage?: string;
    route?: string;
    therapy_duration?: string;
    patient_age?: number;
    patient_age_group?: string;
    patient_gender?: string;
    patient_weight?: number;
    adverse_reaction?: string;
    serious?: boolean;
    outcome?: string;
    report_date?: string;
    event_date?: string;
    reporter_type?: string;
    reporter_country?: string;
    manufacturer?: string;
    concomitant_drugs?: string[];
    medical_history?: string;
    reaction_terms?: string[];
    seriousness_criteria?: string[];
    rechallenge?: string;
    dechallenge?: string;
    last_updated?: string;
}

export interface FAERSSafetySignal {
    drug_name: string;
    adverse_reaction: string;
    total_reports: number;
    serious_reports: number;
    death_reports: number;
    hospitalization_reports: number;
    disability_reports: number;
    signal_strength: 'low' | 'moderate' | 'high';
    age_groups_affected: string[];
    gender_distribution: any;
    common_outcomes: string[];
    reporting_trend: 'increasing' | 'stable' | 'decreasing';
}

export interface FAERSSearchParams {
    drugName?: string;
    genericName?: string;
    brandName?: string;
    adverseReaction?: string;
    indication?: string;
    ageGroup?: string;
    gender?: string;
    outcome?: string;
    reporterCountry?: string;
    seriousOnly?: boolean;
    dateFrom?: string;
    dateTo?: string;
    maxResults?: number;
}

export class OpenFDAFAERSConnector extends DatabaseConnector {
    private readonly eventsTable = 'openfda_faers_events';
    private readonly signalsTable = 'openfda_faers_signals';
    private readonly logger = (Logger as any).getInstance('OpenFDAFAERSConnector');

    constructor() {
        super('openfda_faers_events', ['drug_name', 'event_term', 'reaction']);
    }

    async searchAdverseEvents(params: FAERSSearchParams): Promise<FAERSAdverseEvent[]> {
        this.logger.info('Searching OpenFDA FAERS adverse events', { params });

        try {
            let query = `
                SELECT 
                    id, report_id, drug_name, generic_name, brand_name, ndc,
                    indication, dosage, route, therapy_duration, patient_age,
                    patient_age_group, patient_gender, patient_weight, adverse_reaction,
                    serious, outcome, report_date, event_date, reporter_type,
                    reporter_country, manufacturer, concomitant_drugs, medical_history,
                    reaction_terms, seriousness_criteria, rechallenge, dechallenge, last_updated
                FROM ${this.eventsTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.drugName) {
                query += ` AND (drug_name ILIKE $${paramIndex} OR generic_name ILIKE $${paramIndex} OR brand_name ILIKE $${paramIndex})`;
                queryParams.push(`%${params.drugName}%`);
                paramIndex++;
            }

            if (params.genericName) {
                query += ` AND generic_name ILIKE $${paramIndex}`;
                queryParams.push(`%${params.genericName}%`);
                paramIndex++;
            }

            if (params.brandName) {
                query += ` AND brand_name ILIKE $${paramIndex}`;
                queryParams.push(`%${params.brandName}%`);
                paramIndex++;
            }

            if (params.adverseReaction) {
                query += ` AND (adverse_reaction ILIKE $${paramIndex} OR reaction_terms::text ILIKE $${paramIndex})`;
                queryParams.push(`%${params.adverseReaction}%`);
                paramIndex++;
            }

            if (params.indication) {
                query += ` AND indication ILIKE $${paramIndex}`;
                queryParams.push(`%${params.indication}%`);
                paramIndex++;
            }

            if (params.ageGroup) {
                query += ` AND patient_age_group = $${paramIndex}`;
                queryParams.push(params.ageGroup);
                paramIndex++;
            }

            if (params.gender) {
                query += ` AND patient_gender = $${paramIndex}`;
                queryParams.push(params.gender);
                paramIndex++;
            }

            if (params.outcome) {
                query += ` AND outcome ILIKE $${paramIndex}`;
                queryParams.push(`%${params.outcome}%`);
                paramIndex++;
            }

            if (params.reporterCountry) {
                query += ` AND reporter_country = $${paramIndex}`;
                queryParams.push(params.reporterCountry);
                paramIndex++;
            }

            if (params.seriousOnly) {
                query += ` AND serious = true`;
            }

            if (params.dateFrom) {
                query += ` AND report_date >= $${paramIndex}`;
                queryParams.push(params.dateFrom);
                paramIndex++;
            }

            if (params.dateTo) {
                query += ` AND report_date <= $${paramIndex}`;
                queryParams.push(params.dateTo);
                paramIndex++;
            }

            query += ` ORDER BY 
                CASE WHEN serious = true THEN 1 ELSE 2 END,
                report_date DESC,
                drug_name ASC
            `;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const events: FAERSAdverseEvent[] = result.rows.map(row => ({
                id: row.id,
                report_id: row.report_id,
                drug_name: row.drug_name,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                ndc: row.ndc,
                indication: row.indication,
                dosage: row.dosage,
                route: row.route,
                therapy_duration: row.therapy_duration,
                patient_age: row.patient_age,
                patient_age_group: row.patient_age_group,
                patient_gender: row.patient_gender,
                patient_weight: row.patient_weight,
                adverse_reaction: row.adverse_reaction,
                serious: row.serious,
                outcome: row.outcome,
                report_date: row.report_date,
                event_date: row.event_date,
                reporter_type: row.reporter_type,
                reporter_country: row.reporter_country,
                manufacturer: row.manufacturer,
                concomitant_drugs: row.concomitant_drugs || [],
                medical_history: row.medical_history,
                reaction_terms: row.reaction_terms || [],
                seriousness_criteria: row.seriousness_criteria || [],
                rechallenge: row.rechallenge,
                dechallenge: row.dechallenge,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${events.length} adverse events`);
            return events;

        } catch (error) {
            this.logger.error('Error searching adverse events', { error, params });
            throw new Error(`Failed to search adverse events: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugSafetyProfile(drugName: string): Promise<any> {
        this.logger.info('Getting drug safety profile from FAERS', { drugName });

        try {
            const query = `
                SELECT 
                    COUNT(*) as total_reports,
                    COUNT(CASE WHEN serious = true THEN 1 END) as serious_reports,
                    COUNT(CASE WHEN outcome ILIKE '%death%' THEN 1 END) as death_reports,
                    COUNT(CASE WHEN outcome ILIKE '%hospitalization%' OR outcome ILIKE '%hospital%' THEN 1 END) as hospitalization_reports,
                    COUNT(CASE WHEN outcome ILIKE '%disability%' THEN 1 END) as disability_reports,
                    COUNT(CASE WHEN patient_gender = 'male' THEN 1 END) as male_reports,
                    COUNT(CASE WHEN patient_gender = 'female' THEN 1 END) as female_reports,
                    AVG(patient_age) FILTER (WHERE patient_age IS NOT NULL) as avg_age,
                    array_agg(DISTINCT adverse_reaction) FILTER (WHERE adverse_reaction IS NOT NULL) as top_reactions,
                    array_agg(DISTINCT outcome) FILTER (WHERE outcome IS NOT NULL) as outcomes,
                    array_agg(DISTINCT patient_age_group) FILTER (WHERE patient_age_group IS NOT NULL) as age_groups,
                    MIN(report_date) as earliest_report,
                    MAX(report_date) as latest_report
                FROM ${this.eventsTable}
                WHERE drug_name ILIKE $1 OR generic_name ILIKE $1 OR brand_name ILIKE $1
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            if (result.rows.length === 0 || parseInt(result.rows[0].total_reports) === 0) {
                return null;
            }

            const row = result.rows[0];
            const totalReports = parseInt(row.total_reports);
            
            const profile = {
                drug_name: drugName,
                total_reports: totalReports,
                serious_reports: parseInt(row.serious_reports),
                serious_percentage: totalReports > 0 ? ((parseInt(row.serious_reports) / totalReports) * 100).toFixed(1) : '0',
                death_reports: parseInt(row.death_reports),
                hospitalization_reports: parseInt(row.hospitalization_reports),
                disability_reports: parseInt(row.disability_reports),
                gender_distribution: {
                    male: parseInt(row.male_reports),
                    female: parseInt(row.female_reports),
                    unknown: totalReports - parseInt(row.male_reports) - parseInt(row.female_reports),
                },
                average_age: row.avg_age ? parseFloat(row.avg_age).toFixed(1) : null,
                top_reactions: (row.top_reactions || []).slice(0, 10),
                common_outcomes: row.outcomes || [],
                affected_age_groups: row.age_groups || [],
                reporting_period: {
                    earliest: row.earliest_report,
                    latest: row.latest_report,
                },
            };

            this.logger.info('Generated drug safety profile');
            return profile;

        } catch (error) {
            this.logger.error('Error getting drug safety profile', { error, drugName });
            throw new Error(`Failed to get drug safety profile: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getSeriousAdverseEvents(drugName: string, maxResults: number = 100): Promise<FAERSAdverseEvent[]> {
        this.logger.info('Getting serious adverse events', { drugName, maxResults });

        try {
            const query = `
                SELECT 
                    id, report_id, drug_name, generic_name, brand_name, indication,
                    dosage, route, patient_age, patient_age_group, patient_gender,
                    adverse_reaction, outcome, report_date, event_date, 
                    reporter_country, reaction_terms, seriousness_criteria
                FROM ${this.eventsTable}
                WHERE (drug_name ILIKE $1 OR generic_name ILIKE $1 OR brand_name ILIKE $1)
                AND serious = true
                ORDER BY 
                    CASE 
                        WHEN outcome ILIKE '%death%' THEN 1
                        WHEN outcome ILIKE '%disability%' THEN 2
                        WHEN outcome ILIKE '%hospitalization%' THEN 3
                        WHEN outcome ILIKE '%life threatening%' THEN 4
                        ELSE 5
                    END,
                    report_date DESC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`, maxResults]);
            
            const seriousEvents: FAERSAdverseEvent[] = result.rows.map(row => ({
                id: row.id,
                report_id: row.report_id,
                drug_name: row.drug_name,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                indication: row.indication,
                dosage: row.dosage,
                route: row.route,
                patient_age: row.patient_age,
                patient_age_group: row.patient_age_group,
                patient_gender: row.patient_gender,
                adverse_reaction: row.adverse_reaction,
                serious: true,
                outcome: row.outcome,
                report_date: row.report_date,
                event_date: row.event_date,
                reporter_country: row.reporter_country,
                reaction_terms: row.reaction_terms || [],
                seriousness_criteria: row.seriousness_criteria || [],
            }));

            this.logger.info(`Found ${seriousEvents.length} serious adverse events`);
            return seriousEvents;

        } catch (error) {
            this.logger.error('Error getting serious adverse events', { error, drugName });
            throw new Error(`Failed to get serious adverse events: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getAdverseEventsByReaction(reactionTerm: string, maxResults: number = 100): Promise<FAERSAdverseEvent[]> {
        this.logger.info('Getting adverse events by reaction', { reactionTerm, maxResults });

        try {
            const query = `
                SELECT 
                    id, report_id, drug_name, generic_name, brand_name, indication,
                    dosage, patient_age, patient_age_group, patient_gender,
                    adverse_reaction, serious, outcome, report_date, manufacturer
                FROM ${this.eventsTable}
                WHERE adverse_reaction ILIKE $1 OR reaction_terms::text ILIKE $1
                ORDER BY 
                    CASE WHEN serious = true THEN 1 ELSE 2 END,
                    report_date DESC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${reactionTerm}%`, maxResults]);
            
            const events: FAERSAdverseEvent[] = result.rows.map(row => ({
                id: row.id,
                report_id: row.report_id,
                drug_name: row.drug_name,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                indication: row.indication,
                dosage: row.dosage,
                patient_age: row.patient_age,
                patient_age_group: row.patient_age_group,
                patient_gender: row.patient_gender,
                adverse_reaction: row.adverse_reaction,
                serious: row.serious,
                outcome: row.outcome,
                report_date: row.report_date,
                manufacturer: row.manufacturer,
            }));

            this.logger.info(`Found ${events.length} adverse events for reaction`);
            return events;

        } catch (error) {
            this.logger.error('Error getting adverse events by reaction', { error, reactionTerm });
            throw new Error(`Failed to get adverse events by reaction: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsByAdverseOutcome(outcome: string, maxResults: number = 50): Promise<any[]> {
        this.logger.info('Getting drugs by adverse outcome', { outcome, maxResults });

        try {
            const query = `
                SELECT 
                    drug_name,
                    generic_name,
                    COUNT(*) as total_reports,
                    COUNT(CASE WHEN serious = true THEN 1 END) as serious_reports,
                    array_agg(DISTINCT adverse_reaction) FILTER (WHERE adverse_reaction IS NOT NULL) as reactions,
                    array_agg(DISTINCT manufacturer) FILTER (WHERE manufacturer IS NOT NULL) as manufacturers
                FROM ${this.eventsTable}
                WHERE outcome ILIKE $1
                GROUP BY drug_name, generic_name
                HAVING COUNT(*) >= 5  -- Only include drugs with at least 5 reports
                ORDER BY serious_reports DESC, total_reports DESC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${outcome}%`, maxResults]);
            
            const drugs = result.rows.map(row => ({
                drug_name: row.drug_name,
                generic_name: row.generic_name,
                total_reports: parseInt(row.total_reports),
                serious_reports: parseInt(row.serious_reports),
                serious_percentage: ((parseInt(row.serious_reports) / parseInt(row.total_reports)) * 100).toFixed(1),
                associated_reactions: (row.reactions || []).slice(0, 10),
                manufacturers: row.manufacturers || [],
            }));

            this.logger.info(`Found ${drugs.length} drugs with adverse outcome`);
            return drugs;

        } catch (error) {
            this.logger.error('Error getting drugs by adverse outcome', { error, outcome });
            throw new Error(`Failed to get drugs by adverse outcome: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getAgeGroupAnalysis(drugName: string): Promise<any> {
        this.logger.info('Getting age group analysis for drug', { drugName });

        try {
            const query = `
                SELECT 
                    patient_age_group,
                    COUNT(*) as total_reports,
                    COUNT(CASE WHEN serious = true THEN 1 END) as serious_reports,
                    COUNT(CASE WHEN outcome ILIKE '%death%' THEN 1 END) as death_reports,
                    AVG(patient_age) FILTER (WHERE patient_age IS NOT NULL) as avg_age,
                    array_agg(DISTINCT adverse_reaction) FILTER (WHERE adverse_reaction IS NOT NULL) as top_reactions
                FROM ${this.eventsTable}
                WHERE (drug_name ILIKE $1 OR generic_name ILIKE $1 OR brand_name ILIKE $1)
                AND patient_age_group IS NOT NULL
                GROUP BY patient_age_group
                ORDER BY total_reports DESC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const ageAnalysis = result.rows.map(row => ({
                age_group: row.patient_age_group,
                total_reports: parseInt(row.total_reports),
                serious_reports: parseInt(row.serious_reports),
                death_reports: parseInt(row.death_reports),
                serious_percentage: ((parseInt(row.serious_reports) / parseInt(row.total_reports)) * 100).toFixed(1),
                death_percentage: ((parseInt(row.death_reports) / parseInt(row.total_reports)) * 100).toFixed(1),
                average_age: row.avg_age ? parseFloat(row.avg_age).toFixed(1) : null,
                top_reactions: (row.top_reactions || []).slice(0, 5),
            }));

            this.logger.info(`Generated age group analysis for ${ageAnalysis.length} age groups`);
            return {
                drug_name: drugName,
                age_groups: ageAnalysis,
                total_reports: ageAnalysis.reduce((sum, group) => sum + group.total_reports, 0),
            };

        } catch (error) {
            this.logger.error('Error getting age group analysis', { error, drugName });
            throw new Error(`Failed to get age group analysis: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getConcomitantDrugsAnalysis(drugName: string, maxResults: number = 20): Promise<any[]> {
        this.logger.info('Getting concomitant drugs analysis', { drugName, maxResults });

        try {
            const query = `
                SELECT 
                    unnest(concomitant_drugs) as concomitant_drug,
                    COUNT(*) as co_occurrence_count,
                    COUNT(CASE WHEN serious = true THEN 1 END) as serious_co_reports,
                    array_agg(DISTINCT adverse_reaction) FILTER (WHERE adverse_reaction IS NOT NULL) as reactions_with_combo
                FROM ${this.eventsTable}
                WHERE (drug_name ILIKE $1 OR generic_name ILIKE $1 OR brand_name ILIKE $1)
                AND concomitant_drugs IS NOT NULL 
                AND array_length(concomitant_drugs, 1) > 0
                GROUP BY unnest(concomitant_drugs)
                HAVING COUNT(*) >= 3  -- At least 3 co-occurrence reports
                ORDER BY co_occurrence_count DESC, serious_co_reports DESC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`, maxResults]);
            
            const concomitantAnalysis = result.rows.map(row => ({
                concomitant_drug: row.concomitant_drug,
                co_occurrence_count: parseInt(row.co_occurrence_count),
                serious_co_reports: parseInt(row.serious_co_reports),
                serious_percentage: ((parseInt(row.serious_co_reports) / parseInt(row.co_occurrence_count)) * 100).toFixed(1),
                reactions_with_combination: (row.reactions_with_combo || []).slice(0, 5),
            }));

            this.logger.info(`Found ${concomitantAnalysis.length} concomitant drug patterns`);
            return concomitantAnalysis;

        } catch (error) {
            this.logger.error('Error getting concomitant drugs analysis', { error, drugName });
            throw new Error(`Failed to get concomitant drugs analysis: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getReportingTrends(drugName: string, timeframe: 'month' | 'quarter' | 'year' = 'quarter'): Promise<any[]> {
        this.logger.info('Getting reporting trends', { drugName, timeframe });

        try {
            let dateGrouping: string;
            switch (timeframe) {
                case 'month':
                    dateGrouping = "DATE_TRUNC('month', report_date::date)";
                    break;
                case 'year':
                    dateGrouping = "DATE_TRUNC('year', report_date::date)";
                    break;
                default:
                    dateGrouping = "DATE_TRUNC('quarter', report_date::date)";
            }

            const query = `
                SELECT 
                    ${dateGrouping} as period,
                    COUNT(*) as total_reports,
                    COUNT(CASE WHEN serious = true THEN 1 END) as serious_reports,
                    COUNT(DISTINCT adverse_reaction) as unique_reactions
                FROM ${this.eventsTable}
                WHERE (drug_name ILIKE $1 OR generic_name ILIKE $1 OR brand_name ILIKE $1)
                AND report_date IS NOT NULL
                AND report_date >= CURRENT_DATE - INTERVAL '3 years'  -- Last 3 years
                GROUP BY ${dateGrouping}
                ORDER BY period ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const trends = result.rows.map(row => ({
                period: row.period,
                total_reports: parseInt(row.total_reports),
                serious_reports: parseInt(row.serious_reports),
                unique_reactions: parseInt(row.unique_reactions),
                serious_percentage: ((parseInt(row.serious_reports) / parseInt(row.total_reports)) * 100).toFixed(1),
            }));

            this.logger.info(`Generated ${trends.length} reporting trend periods`);
            return trends;

        } catch (error) {
            this.logger.error('Error getting reporting trends', { error, drugName, timeframe });
            throw new Error(`Failed to get reporting trends: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getManufacturerSafetyComparison(drugName: string): Promise<any[]> {
        this.logger.info('Getting manufacturer safety comparison', { drugName });

        try {
            const query = `
                SELECT 
                    manufacturer,
                    COUNT(*) as total_reports,
                    COUNT(CASE WHEN serious = true THEN 1 END) as serious_reports,
                    COUNT(CASE WHEN outcome ILIKE '%death%' THEN 1 END) as death_reports,
                    array_agg(DISTINCT adverse_reaction) FILTER (WHERE adverse_reaction IS NOT NULL) as top_reactions
                FROM ${this.eventsTable}
                WHERE (drug_name ILIKE $1 OR generic_name ILIKE $1 OR brand_name ILIKE $1)
                AND manufacturer IS NOT NULL
                AND manufacturer != ''
                GROUP BY manufacturer
                HAVING COUNT(*) >= 5  -- At least 5 reports per manufacturer
                ORDER BY serious_reports DESC, total_reports DESC
                LIMIT 10
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const manufacturerComparison = result.rows.map(row => ({
                manufacturer: row.manufacturer,
                total_reports: parseInt(row.total_reports),
                serious_reports: parseInt(row.serious_reports),
                death_reports: parseInt(row.death_reports),
                serious_percentage: ((parseInt(row.serious_reports) / parseInt(row.total_reports)) * 100).toFixed(1),
                death_percentage: ((parseInt(row.death_reports) / parseInt(row.total_reports)) * 100).toFixed(1),
                top_reactions: (row.top_reactions || []).slice(0, 5),
            }));

            this.logger.info(`Generated manufacturer comparison for ${manufacturerComparison.length} manufacturers`);
            return manufacturerComparison;

        } catch (error) {
            this.logger.error('Error getting manufacturer safety comparison', { error, drugName });
            throw new Error(`Failed to get manufacturer safety comparison: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}