import { DatabaseConnector } from '../DatabaseConnector';
import { Logger } from '../../utils/logger';

export interface LactMedDrugRecord {
    id: string;
    drug_name: string;
    cas_number?: string;
    generic_names?: string[];
    brand_names?: string[];
    drug_class?: string;
    lactation_summary?: string;
    lactation_risk_category?: string;
    effects_on_breastfed_infants?: string;
    effects_on_lactation?: string;
    alternate_drugs?: string[];
    pregnancy_category?: string;
    clinical_considerations?: string;
    dosage_information?: string;
    monitoring_recommendations?: string;
    contraindications?: string;
    drug_interactions?: string[];
    references?: string[];
    last_updated?: string;
    review_date?: string;
}

export interface LactMedRiskAssessment {
    drug_name: string;
    risk_category: string;
    risk_level: 'low' | 'moderate' | 'high' | 'contraindicated' | 'unknown';
    safety_summary: string;
    infant_effects?: string;
    lactation_effects?: string;
    recommendations: string[];
    alternatives?: string[];
    monitoring_required: boolean;
}

export interface LactMedSearchParams {
    drugName?: string;
    genericName?: string;
    brandName?: string;
    drugClass?: string;
    riskCategory?: string;
    riskLevel?: string;
    maxResults?: number;
    includeAlternatives?: boolean;
}

export class LactMedConnector extends DatabaseConnector {
    private readonly drugsTable = 'lactmed_drugs';
    private readonly interactionsTable = 'lactmed_drug_interactions';
    private readonly logger = (Logger as any).getInstance('LactMedConnector');

    constructor() {
        super('lactmed_drugs', ['drug_name', 'active_ingredient', 'therapeutic_class']);
    }

    async searchLactationDrugs(params: LactMedSearchParams): Promise<LactMedDrugRecord[]> {
        this.logger.info('Searching LactMed lactation drugs', { params });

        try {
            let query = `
                SELECT 
                    id, drug_name, cas_number, generic_names, brand_names, drug_class,
                    lactation_summary, lactation_risk_category, effects_on_breastfed_infants,
                    effects_on_lactation, alternate_drugs, pregnancy_category,
                    clinical_considerations, dosage_information, monitoring_recommendations,
                    contraindications, drug_interactions, references, last_updated, review_date
                FROM ${this.drugsTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.drugName) {
                query += ` AND (
                    drug_name ILIKE $${paramIndex} OR 
                    generic_names::text ILIKE $${paramIndex} OR 
                    brand_names::text ILIKE $${paramIndex}
                )`;
                queryParams.push(`%${params.drugName}%`);
                paramIndex++;
            }

            if (params.genericName) {
                query += ` AND (drug_name ILIKE $${paramIndex} OR generic_names::text ILIKE $${paramIndex})`;
                queryParams.push(`%${params.genericName}%`);
                paramIndex++;
            }

            if (params.brandName) {
                query += ` AND brand_names::text ILIKE $${paramIndex}`;
                queryParams.push(`%${params.brandName}%`);
                paramIndex++;
            }

            if (params.drugClass) {
                query += ` AND drug_class ILIKE $${paramIndex}`;
                queryParams.push(`%${params.drugClass}%`);
                paramIndex++;
            }

            if (params.riskCategory) {
                query += ` AND lactation_risk_category = $${paramIndex}`;
                queryParams.push(params.riskCategory);
                paramIndex++;
            }

            query += ` ORDER BY 
                CASE 
                    WHEN drug_name ILIKE $${paramIndex} THEN 1
                    WHEN generic_names::text ILIKE $${paramIndex} THEN 2
                    WHEN brand_names::text ILIKE $${paramIndex} THEN 3
                    ELSE 4
                END,
                CASE lactation_risk_category
                    WHEN 'contraindicated' THEN 1
                    WHEN 'high risk' THEN 2
                    WHEN 'moderate risk' THEN 3
                    WHEN 'low risk' THEN 4
                    WHEN 'compatible' THEN 5
                    ELSE 6
                END,
                drug_name ASC
            `;
            queryParams.push(`%${params.drugName || params.genericName || params.brandName || ''}%`);
            paramIndex++;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const drugs: LactMedDrugRecord[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                cas_number: row.cas_number,
                generic_names: row.generic_names || [],
                brand_names: row.brand_names || [],
                drug_class: row.drug_class,
                lactation_summary: row.lactation_summary,
                lactation_risk_category: row.lactation_risk_category,
                effects_on_breastfed_infants: row.effects_on_breastfed_infants,
                effects_on_lactation: row.effects_on_lactation,
                alternate_drugs: row.alternate_drugs || [],
                pregnancy_category: row.pregnancy_category,
                clinical_considerations: row.clinical_considerations,
                dosage_information: row.dosage_information,
                monitoring_recommendations: row.monitoring_recommendations,
                contraindications: row.contraindications,
                drug_interactions: row.drug_interactions || [],
                references: row.references || [],
                last_updated: row.last_updated,
                review_date: row.review_date,
            }));

            this.logger.info(`Found ${drugs.length} LactMed drugs`);
            return drugs;

        } catch (error) {
            this.logger.error('Error searching LactMed drugs', { error, params });
            throw new Error(`Failed to search LactMed drugs: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getLactationRiskAssessment(drugName: string): Promise<LactMedRiskAssessment | null> {
        this.logger.info('Getting lactation risk assessment', { drugName });

        try {
            const query = `
                SELECT 
                    drug_name, lactation_risk_category, lactation_summary,
                    effects_on_breastfed_infants, effects_on_lactation,
                    clinical_considerations, monitoring_recommendations,
                    alternate_drugs, contraindications
                FROM ${this.drugsTable}
                WHERE drug_name ILIKE $1 OR generic_names::text ILIKE $1 OR brand_names::text ILIKE $1
                ORDER BY 
                    CASE 
                        WHEN drug_name ILIKE $1 THEN 1
                        WHEN generic_names::text ILIKE $1 THEN 2
                        ELSE 3
                    END
                LIMIT 1
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);

            if (result.rows.length === 0) {
                this.logger.info('No lactation data found for drug', { drugName });
                return null;
            }

            const row = result.rows[0];
            
            // Determine risk level from category
            const riskLevel = this.categorizeRiskLevel(row.lactation_risk_category);
            
            // Generate recommendations
            const recommendations = this.generateRecommendations(row);

            const assessment: LactMedRiskAssessment = {
                drug_name: drugName,
                risk_category: row.lactation_risk_category || 'unknown',
                risk_level: riskLevel,
                safety_summary: row.lactation_summary || 'No summary available',
                infant_effects: row.effects_on_breastfed_infants,
                lactation_effects: row.effects_on_lactation,
                recommendations: recommendations,
                alternatives: row.alternate_drugs || [],
                monitoring_required: this.requiresMonitoring(row.monitoring_recommendations, row.clinical_considerations),
            };

            this.logger.info('Generated lactation risk assessment');
            return assessment;

        } catch (error) {
            this.logger.error('Error getting lactation risk assessment', { error, drugName });
            throw new Error(`Failed to get lactation risk assessment: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsByRiskLevel(riskLevel: string, maxResults: number = 50): Promise<LactMedDrugRecord[]> {
        this.logger.info('Getting drugs by risk level', { riskLevel, maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_name, generic_names, brand_names, drug_class,
                    lactation_summary, lactation_risk_category, effects_on_breastfed_infants,
                    effects_on_lactation, alternate_drugs
                FROM ${this.drugsTable}
                WHERE lactation_risk_category ILIKE $1
                ORDER BY drug_name ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${riskLevel}%`, maxResults]);
            
            const drugs: LactMedDrugRecord[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                generic_names: row.generic_names || [],
                brand_names: row.brand_names || [],
                drug_class: row.drug_class,
                lactation_summary: row.lactation_summary,
                lactation_risk_category: row.lactation_risk_category,
                effects_on_breastfed_infants: row.effects_on_breastfed_infants,
                effects_on_lactation: row.effects_on_lactation,
                alternate_drugs: row.alternate_drugs || [],
            }));

            this.logger.info(`Found ${drugs.length} drugs with risk level`);
            return drugs;

        } catch (error) {
            this.logger.error('Error getting drugs by risk level', { error, riskLevel });
            throw new Error(`Failed to get drugs by risk level: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getBreastfeedingSafeDrugs(drugClass?: string, maxResults: number = 100): Promise<LactMedDrugRecord[]> {
        this.logger.info('Getting breastfeeding-safe drugs', { drugClass, maxResults });

        try {
            let query = `
                SELECT 
                    id, drug_name, generic_names, brand_names, drug_class,
                    lactation_summary, lactation_risk_category, effects_on_breastfed_infants,
                    effects_on_lactation, clinical_considerations
                FROM ${this.drugsTable}
                WHERE lactation_risk_category IN ('compatible', 'low risk', 'probably compatible')
                OR lactation_summary ILIKE '%safe%'
                OR lactation_summary ILIKE '%compatible%'
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (drugClass) {
                query += ` AND drug_class ILIKE $${paramIndex}`;
                queryParams.push(`%${drugClass}%`);
                paramIndex++;
            }

            query += ` ORDER BY 
                CASE lactation_risk_category
                    WHEN 'compatible' THEN 1
                    WHEN 'probably compatible' THEN 2
                    WHEN 'low risk' THEN 3
                    ELSE 4
                END,
                drug_name ASC
                LIMIT $${paramIndex}
            `;
            queryParams.push(maxResults);

            const result = await this.executeQuery(query, queryParams);
            
            const safeDrugs: LactMedDrugRecord[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                generic_names: row.generic_names || [],
                brand_names: row.brand_names || [],
                drug_class: row.drug_class,
                lactation_summary: row.lactation_summary,
                lactation_risk_category: row.lactation_risk_category,
                effects_on_breastfed_infants: row.effects_on_breastfed_infants,
                effects_on_lactation: row.effects_on_lactation,
                clinical_considerations: row.clinical_considerations,
            }));

            this.logger.info(`Found ${safeDrugs.length} breastfeeding-safe drugs`);
            return safeDrugs;

        } catch (error) {
            this.logger.error('Error getting breastfeeding-safe drugs', { error, drugClass });
            throw new Error(`Failed to get breastfeeding-safe drugs: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsToAvoid(maxResults: number = 100): Promise<LactMedDrugRecord[]> {
        this.logger.info('Getting drugs to avoid during breastfeeding', { maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_name, generic_names, brand_names, drug_class,
                    lactation_summary, lactation_risk_category, effects_on_breastfed_infants,
                    effects_on_lactation, contraindications, alternate_drugs
                FROM ${this.drugsTable}
                WHERE lactation_risk_category IN ('contraindicated', 'high risk', 'avoid')
                OR contraindications ILIKE '%breastfeed%'
                OR contraindications ILIKE '%lactation%'
                OR effects_on_breastfed_infants ILIKE '%serious%'
                OR effects_on_breastfed_infants ILIKE '%toxic%'
                ORDER BY 
                    CASE lactation_risk_category
                        WHEN 'contraindicated' THEN 1
                        WHEN 'avoid' THEN 2
                        WHEN 'high risk' THEN 3
                        ELSE 4
                    END,
                    drug_name ASC
                LIMIT $1
            `;

            const result = await this.executeQuery(query, [maxResults]);
            
            const drugsToAvoid: LactMedDrugRecord[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                generic_names: row.generic_names || [],
                brand_names: row.brand_names || [],
                drug_class: row.drug_class,
                lactation_summary: row.lactation_summary,
                lactation_risk_category: row.lactation_risk_category,
                effects_on_breastfed_infants: row.effects_on_breastfed_infants,
                effects_on_lactation: row.effects_on_lactation,
                contraindications: row.contraindications,
                alternate_drugs: row.alternate_drugs || [],
            }));

            this.logger.info(`Found ${drugsToAvoid.length} drugs to avoid`);
            return drugsToAvoid;

        } catch (error) {
            this.logger.error('Error getting drugs to avoid', { error });
            throw new Error(`Failed to get drugs to avoid: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getSaferAlternatives(drugName: string): Promise<LactMedDrugRecord[]> {
        this.logger.info('Getting safer alternatives for drug', { drugName });

        try {
            // First get the original drug to find its class and alternatives
            const originalDrugQuery = `
                SELECT drug_class, alternate_drugs
                FROM ${this.drugsTable}
                WHERE drug_name ILIKE $1 OR generic_names::text ILIKE $1 OR brand_names::text ILIKE $1
                LIMIT 1
            `;

            const originalResult = await this.executeQuery(originalDrugQuery, [`%${drugName}%`]);
            
            if (originalResult.rows.length === 0) {
                return [];
            }

            const originalDrug = originalResult.rows[0];
            const alternativeDrugs = originalDrug.alternate_drugs || [];
            const drugClass = originalDrug.drug_class;

            let alternatives: LactMedDrugRecord[] = [];

            // Get explicitly mentioned alternatives
            if (alternativeDrugs.length > 0) {
                for (const altDrug of alternativeDrugs) {
                    const altResult = await this.searchLactationDrugs({ drugName: altDrug, maxResults: 1 });
                    alternatives.push(...altResult);
                }
            }

            // Get other drugs in same class that are safer
            if (drugClass && alternatives.length < 5) {
                const classQuery = `
                    SELECT 
                        id, drug_name, generic_names, brand_names, drug_class,
                        lactation_summary, lactation_risk_category, effects_on_breastfed_infants,
                        effects_on_lactation, clinical_considerations
                    FROM ${this.drugsTable}
                    WHERE drug_class = $1
                    AND lactation_risk_category IN ('compatible', 'low risk', 'probably compatible')
                    AND drug_name NOT ILIKE $2
                    ORDER BY 
                        CASE lactation_risk_category
                            WHEN 'compatible' THEN 1
                            WHEN 'probably compatible' THEN 2
                            WHEN 'low risk' THEN 3
                            ELSE 4
                        END,
                        drug_name ASC
                    LIMIT 10
                `;

                const classResult = await this.executeQuery(classQuery, [drugClass, `%${drugName}%`]);
                
                const classAlternatives: LactMedDrugRecord[] = classResult.rows.map(row => ({
                    id: row.id,
                    drug_name: row.drug_name,
                    generic_names: row.generic_names || [],
                    brand_names: row.brand_names || [],
                    drug_class: row.drug_class,
                    lactation_summary: row.lactation_summary,
                    lactation_risk_category: row.lactation_risk_category,
                    effects_on_breastfed_infants: row.effects_on_breastfed_infants,
                    effects_on_lactation: row.effects_on_lactation,
                    clinical_considerations: row.clinical_considerations,
                }));

                alternatives.push(...classAlternatives);
            }

            // Remove duplicates
            const uniqueAlternatives = alternatives.filter((drug, index, self) => 
                index === self.findIndex(d => d.drug_name === drug.drug_name)
            );

            this.logger.info(`Found ${uniqueAlternatives.length} safer alternatives`);
            return uniqueAlternatives.slice(0, 10);

        } catch (error) {
            this.logger.error('Error getting safer alternatives', { error, drugName });
            throw new Error(`Failed to get safer alternatives: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsByClass(drugClass: string, maxResults: number = 50): Promise<LactMedDrugRecord[]> {
        this.logger.info('Getting drugs by therapeutic class', { drugClass, maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_name, generic_names, brand_names, drug_class,
                    lactation_summary, lactation_risk_category, effects_on_breastfed_infants,
                    effects_on_lactation
                FROM ${this.drugsTable}
                WHERE drug_class ILIKE $1
                ORDER BY 
                    CASE lactation_risk_category
                        WHEN 'compatible' THEN 1
                        WHEN 'probably compatible' THEN 2
                        WHEN 'low risk' THEN 3
                        WHEN 'moderate risk' THEN 4
                        WHEN 'high risk' THEN 5
                        WHEN 'contraindicated' THEN 6
                        ELSE 7
                    END,
                    drug_name ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${drugClass}%`, maxResults]);
            
            const drugs: LactMedDrugRecord[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                generic_names: row.generic_names || [],
                brand_names: row.brand_names || [],
                drug_class: row.drug_class,
                lactation_summary: row.lactation_summary,
                lactation_risk_category: row.lactation_risk_category,
                effects_on_breastfed_infants: row.effects_on_breastfed_infants,
                effects_on_lactation: row.effects_on_lactation,
            }));

            this.logger.info(`Found ${drugs.length} drugs in therapeutic class`);
            return drugs;

        } catch (error) {
            this.logger.error('Error getting drugs by class', { error, drugClass });
            throw new Error(`Failed to get drugs by class: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private categorizeRiskLevel(category: string): 'low' | 'moderate' | 'high' | 'contraindicated' | 'unknown' {
        if (!category) return 'unknown';
        
        const cat = category.toLowerCase();
        if (cat.includes('compatible') || cat.includes('low risk')) return 'low';
        if (cat.includes('moderate') || cat.includes('caution')) return 'moderate';
        if (cat.includes('high risk') || cat.includes('avoid')) return 'high';
        if (cat.includes('contraindicated') || cat.includes('prohibited')) return 'contraindicated';
        
        return 'unknown';
    }

    private generateRecommendations(drugData: any): string[] {
        const recommendations: string[] = [];
        
        if (drugData.clinical_considerations) {
            recommendations.push(drugData.clinical_considerations);
        }
        
        if (drugData.monitoring_recommendations) {
            recommendations.push(`Monitor: ${drugData.monitoring_recommendations}`);
        }
        
        if (drugData.alternate_drugs && drugData.alternate_drugs.length > 0) {
            recommendations.push(`Consider alternatives: ${drugData.alternate_drugs.slice(0, 3).join(', ')}`);
        }
        
        if (drugData.dosage_information) {
            recommendations.push(`Dosage: ${drugData.dosage_information}`);
        }
        
        return recommendations.filter(rec => rec && rec.trim().length > 0);
    }

    private requiresMonitoring(monitoring: string, considerations: string): boolean {
        if (!monitoring && !considerations) return false;
        
        const text = `${monitoring || ''} ${considerations || ''}`.toLowerCase();
        return text.includes('monitor') || 
               text.includes('watch') || 
               text.includes('observe') || 
               text.includes('check');
    }
}