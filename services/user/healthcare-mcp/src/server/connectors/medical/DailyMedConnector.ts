import { DatabaseConnector } from '../DatabaseConnector';
import { Logger } from '../../utils/logger';

export interface DailyMedDrugLabel {
    id: string;
    generic_name: string;
    brand_name?: string;
    manufacturer?: string;
    ndc?: string;
    dosage_form?: string;
    route?: string;
    strength?: string;
    active_ingredients?: string[];
    inactive_ingredients?: string[];
    indications?: string;
    contraindications?: string;
    warnings?: string;
    adverse_reactions?: string;
    dosage_administration?: string;
    clinical_pharmacology?: string;
    how_supplied?: string;
    storage_handling?: string;
    label_url?: string;
    approval_date?: string;
    revision_date?: string;
    application_number?: string;
    product_type?: string;
    therapeutic_equivalence?: string;
    pregnancy_category?: string;
    controlled_substance?: string;
    dea_schedule?: string;
    data_sources?: string[];
}

export interface DailyMedSearchParams {
    genericName?: string;
    brandName?: string;
    manufacturer?: string;
    ndc?: string;
    activeIngredient?: string;
    therapeuticClass?: string;
    dosageForm?: string;
    maxResults?: number;
    includeDiscontinued?: boolean;
}

export class DailyMedConnector extends DatabaseConnector {
    private readonly tableName = 'dailymed_drug_labels';
    private readonly logger = Logger.getInstance();

    async searchDrugLabels(params: DailyMedSearchParams): Promise<DailyMedDrugLabel[]> {
        this.logger.info('Searching DailyMed drug labels', { params });

        try {
            let query = `
                SELECT 
                    id, generic_name, brand_name, manufacturer, ndc, dosage_form,
                    route, strength, active_ingredients, inactive_ingredients,
                    indications, contraindications, warnings, adverse_reactions,
                    dosage_administration, clinical_pharmacology, how_supplied,
                    storage_handling, label_url, approval_date, revision_date,
                    application_number, product_type, therapeutic_equivalence,
                    pregnancy_category, controlled_substance, dea_schedule, data_sources
                FROM ${this.tableName}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

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

            if (params.manufacturer) {
                query += ` AND manufacturer ILIKE $${paramIndex}`;
                queryParams.push(`%${params.manufacturer}%`);
                paramIndex++;
            }

            if (params.ndc) {
                query += ` AND ndc = $${paramIndex}`;
                queryParams.push(params.ndc);
                paramIndex++;
            }

            if (params.activeIngredient) {
                query += ` AND active_ingredients::text ILIKE $${paramIndex}`;
                queryParams.push(`%${params.activeIngredient}%`);
                paramIndex++;
            }

            if (params.dosageForm) {
                query += ` AND dosage_form ILIKE $${paramIndex}`;
                queryParams.push(`%${params.dosageForm}%`);
                paramIndex++;
            }

            // Add text search capability
            query += ` ORDER BY 
                CASE 
                    WHEN generic_name ILIKE $${paramIndex} THEN 1
                    WHEN brand_name ILIKE $${paramIndex} THEN 2
                    ELSE 3
                END,
                generic_name ASC
            `;
            queryParams.push(`%${params.genericName || params.brandName || ''}%`);
            paramIndex++;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const labels: DailyMedDrugLabel[] = result.rows.map(row => ({
                id: row.id,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                manufacturer: row.manufacturer,
                ndc: row.ndc,
                dosage_form: row.dosage_form,
                route: row.route,
                strength: row.strength,
                active_ingredients: row.active_ingredients,
                inactive_ingredients: row.inactive_ingredients,
                indications: row.indications,
                contraindications: row.contraindications,
                warnings: row.warnings,
                adverse_reactions: row.adverse_reactions,
                dosage_administration: row.dosage_administration,
                clinical_pharmacology: row.clinical_pharmacology,
                how_supplied: row.how_supplied,
                storage_handling: row.storage_handling,
                label_url: row.label_url,
                approval_date: row.approval_date,
                revision_date: row.revision_date,
                application_number: row.application_number,
                product_type: row.product_type,
                therapeutic_equivalence: row.therapeutic_equivalence,
                pregnancy_category: row.pregnancy_category,
                controlled_substance: row.controlled_substance,
                dea_schedule: row.dea_schedule,
                data_sources: row.data_sources,
            }));

            this.logger.info(`Found ${labels.length} DailyMed drug labels`);
            return labels;

        } catch (error) {
            this.logger.error('Error searching DailyMed drug labels', { error, params });
            throw new Error(`Failed to search DailyMed drug labels: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugLabelById(id: string): Promise<DailyMedDrugLabel | null> {
        this.logger.info('Getting DailyMed drug label by ID', { id });

        try {
            const query = `
                SELECT 
                    id, generic_name, brand_name, manufacturer, ndc, dosage_form,
                    route, strength, active_ingredients, inactive_ingredients,
                    indications, contraindications, warnings, adverse_reactions,
                    dosage_administration, clinical_pharmacology, how_supplied,
                    storage_handling, label_url, approval_date, revision_date,
                    application_number, product_type, therapeutic_equivalence,
                    pregnancy_category, controlled_substance, dea_schedule, data_sources
                FROM ${this.tableName}
                WHERE id = $1
            `;

            const result = await this.executeQuery(query, [id]);

            if (result.rows.length === 0) {
                this.logger.info('DailyMed drug label not found', { id });
                return null;
            }

            const row = result.rows[0];
            const label: DailyMedDrugLabel = {
                id: row.id,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                manufacturer: row.manufacturer,
                ndc: row.ndc,
                dosage_form: row.dosage_form,
                route: row.route,
                strength: row.strength,
                active_ingredients: row.active_ingredients,
                inactive_ingredients: row.inactive_ingredients,
                indications: row.indications,
                contraindications: row.contraindications,
                warnings: row.warnings,
                adverse_reactions: row.adverse_reactions,
                dosage_administration: row.dosage_administration,
                clinical_pharmacology: row.clinical_pharmacology,
                how_supplied: row.how_supplied,
                storage_handling: row.storage_handling,
                label_url: row.label_url,
                approval_date: row.approval_date,
                revision_date: row.revision_date,
                application_number: row.application_number,
                product_type: row.product_type,
                therapeutic_equivalence: row.therapeutic_equivalence,
                pregnancy_category: row.pregnancy_category,
                controlled_substance: row.controlled_substance,
                dea_schedule: row.dea_schedule,
                data_sources: row.data_sources,
            };

            this.logger.info('Found DailyMed drug label', { id });
            return label;

        } catch (error) {
            this.logger.error('Error getting DailyMed drug label by ID', { error, id });
            throw new Error(`Failed to get DailyMed drug label: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugLabelsByNDC(ndc: string): Promise<DailyMedDrugLabel[]> {
        this.logger.info('Getting DailyMed drug labels by NDC', { ndc });

        try {
            const query = `
                SELECT 
                    id, generic_name, brand_name, manufacturer, ndc, dosage_form,
                    route, strength, active_ingredients, inactive_ingredients,
                    indications, contraindications, warnings, adverse_reactions,
                    dosage_administration, clinical_pharmacology, how_supplied,
                    storage_handling, label_url, approval_date, revision_date,
                    application_number, product_type, therapeutic_equivalence,
                    pregnancy_category, controlled_substance, dea_schedule, data_sources
                FROM ${this.tableName}
                WHERE ndc = $1 OR ndc LIKE $2
                ORDER BY revision_date DESC
            `;

            const result = await this.executeQuery(query, [ndc, `%${ndc}%`]);
            
            const labels: DailyMedDrugLabel[] = result.rows.map(row => ({
                id: row.id,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                manufacturer: row.manufacturer,
                ndc: row.ndc,
                dosage_form: row.dosage_form,
                route: row.route,
                strength: row.strength,
                active_ingredients: row.active_ingredients,
                inactive_ingredients: row.inactive_ingredients,
                indications: row.indications,
                contraindications: row.contraindications,
                warnings: row.warnings,
                adverse_reactions: row.adverse_reactions,
                dosage_administration: row.dosage_administration,
                clinical_pharmacology: row.clinical_pharmacology,
                how_supplied: row.how_supplied,
                storage_handling: row.storage_handling,
                label_url: row.label_url,
                approval_date: row.approval_date,
                revision_date: row.revision_date,
                application_number: row.application_number,
                product_type: row.product_type,
                therapeutic_equivalence: row.therapeutic_equivalence,
                pregnancy_category: row.pregnancy_category,
                controlled_substance: row.controlled_substance,
                dea_schedule: row.dea_schedule,
                data_sources: row.data_sources,
            }));

            this.logger.info(`Found ${labels.length} DailyMed drug labels for NDC`);
            return labels;

        } catch (error) {
            this.logger.error('Error getting DailyMed drug labels by NDC', { error, ndc });
            throw new Error(`Failed to get DailyMed drug labels by NDC: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugInteractions(genericName: string): Promise<any[]> {
        this.logger.info('Getting drug interactions from DailyMed', { genericName });

        try {
            const query = `
                SELECT 
                    id, generic_name, brand_name, contraindications, warnings, adverse_reactions
                FROM ${this.tableName}
                WHERE generic_name ILIKE $1 
                AND (contraindications IS NOT NULL OR warnings IS NOT NULL OR adverse_reactions IS NOT NULL)
                ORDER BY revision_date DESC
                LIMIT 10
            `;

            const result = await this.executeQuery(query, [`%${genericName}%`]);
            
            const interactions = result.rows.map(row => ({
                drug_id: row.id,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                contraindications: row.contraindications,
                warnings: row.warnings,
                adverse_reactions: row.adverse_reactions,
            }));

            this.logger.info(`Found ${interactions.length} drug interaction records`);
            return interactions;

        } catch (error) {
            this.logger.error('Error getting drug interactions', { error, genericName });
            throw new Error(`Failed to get drug interactions: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getPregnancyInformation(genericName: string): Promise<any[]> {
        this.logger.info('Getting pregnancy information from DailyMed', { genericName });

        try {
            const query = `
                SELECT 
                    id, generic_name, brand_name, pregnancy_category, contraindications, warnings
                FROM ${this.tableName}
                WHERE generic_name ILIKE $1 
                AND (pregnancy_category IS NOT NULL OR contraindications ILIKE '%pregnan%' OR warnings ILIKE '%pregnan%')
                ORDER BY revision_date DESC
                LIMIT 5
            `;

            const result = await this.executeQuery(query, [`%${genericName}%`]);
            
            const pregnancyInfo = result.rows.map(row => ({
                drug_id: row.id,
                generic_name: row.generic_name,
                brand_name: row.brand_name,
                pregnancy_category: row.pregnancy_category,
                pregnancy_contraindications: this.extractPregnancyText(row.contraindications),
                pregnancy_warnings: this.extractPregnancyText(row.warnings),
            }));

            this.logger.info(`Found ${pregnancyInfo.length} pregnancy information records`);
            return pregnancyInfo;

        } catch (error) {
            this.logger.error('Error getting pregnancy information', { error, genericName });
            throw new Error(`Failed to get pregnancy information: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    private extractPregnancyText(text: string | null): string | null {
        if (!text) return null;
        
        const pregnancyRegex = /[^.]*pregnan[^.]*\./gi;
        const matches = text.match(pregnancyRegex);
        
        return matches ? matches.join(' ').trim() : null;
    }

    async getManufacturerInfo(manufacturer: string): Promise<any[]> {
        this.logger.info('Getting manufacturer information from DailyMed', { manufacturer });

        try {
            const query = `
                SELECT 
                    manufacturer,
                    COUNT(*) as product_count,
                    COUNT(DISTINCT generic_name) as unique_drugs,
                    array_agg(DISTINCT dosage_form) FILTER (WHERE dosage_form IS NOT NULL) as dosage_forms,
                    array_agg(DISTINCT therapeutic_equivalence) FILTER (WHERE therapeutic_equivalence IS NOT NULL) as therapeutic_classes
                FROM ${this.tableName}
                WHERE manufacturer ILIKE $1
                GROUP BY manufacturer
                ORDER BY product_count DESC
                LIMIT 10
            `;

            const result = await this.executeQuery(query, [`%${manufacturer}%`]);
            
            const manufacturerInfo = result.rows.map(row => ({
                manufacturer: row.manufacturer,
                product_count: parseInt(row.product_count),
                unique_drugs: parseInt(row.unique_drugs),
                dosage_forms: row.dosage_forms || [],
                therapeutic_classes: row.therapeutic_classes || [],
            }));

            this.logger.info(`Found ${manufacturerInfo.length} manufacturer records`);
            return manufacturerInfo;

        } catch (error) {
            this.logger.error('Error getting manufacturer information', { error, manufacturer });
            throw new Error(`Failed to get manufacturer information: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}