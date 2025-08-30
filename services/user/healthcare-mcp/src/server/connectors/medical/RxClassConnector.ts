import { DatabaseConnector } from '../DatabaseConnector';
import { Logger } from '../../utils/logger';

export interface RxClassDrugClassification {
    id: string;
    drug_name: string;
    rxcui?: string;
    class_id: string;
    class_name: string;
    class_type: string;
    rela?: string;
    rela_description?: string;
    class_url?: string;
    drug_url?: string;
    last_updated?: string;
}

export interface RxClassTherapeuticClass {
    class_id: string;
    class_name: string;
    class_type: string;
    description?: string;
    parent_class_id?: string;
    parent_class_name?: string;
    level?: number;
    drug_count?: number;
    example_drugs?: string[];
}

export interface RxClassSearchParams {
    drugName?: string;
    rxcui?: string;
    className?: string;
    classType?: string;
    rela?: string;
    maxResults?: number;
    includeHierarchy?: boolean;
}

export class RxClassConnector extends DatabaseConnector {
    private readonly classificationsTable = 'rxclass_drug_classifications';
    private readonly classesTable = 'rxclass_therapeutic_classes';
    private readonly logger = (Logger as any).getInstance('RxClassConnector');

    constructor() {
        super('rxclass_drug_classifications', ['drug_name', 'class_name', 'class_type']);
    }

    async searchDrugClassifications(params: RxClassSearchParams): Promise<RxClassDrugClassification[]> {
        this.logger.info('Searching RxClass drug classifications', { params });

        try {
            let query = `
                SELECT 
                    id, drug_name, rxcui, class_id, class_name, class_type,
                    rela, rela_description, class_url, drug_url, last_updated
                FROM ${this.classificationsTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.drugName) {
                query += ` AND drug_name ILIKE $${paramIndex}`;
                queryParams.push(`%${params.drugName}%`);
                paramIndex++;
            }

            if (params.rxcui) {
                query += ` AND rxcui = $${paramIndex}`;
                queryParams.push(params.rxcui);
                paramIndex++;
            }

            if (params.className) {
                query += ` AND class_name ILIKE $${paramIndex}`;
                queryParams.push(`%${params.className}%`);
                paramIndex++;
            }

            if (params.classType) {
                query += ` AND class_type = $${paramIndex}`;
                queryParams.push(params.classType);
                paramIndex++;
            }

            if (params.rela) {
                query += ` AND rela = $${paramIndex}`;
                queryParams.push(params.rela);
                paramIndex++;
            }

            query += ` ORDER BY 
                CASE 
                    WHEN drug_name ILIKE $${paramIndex} THEN 1
                    WHEN class_name ILIKE $${paramIndex} THEN 2
                    ELSE 3
                END,
                drug_name ASC, class_type ASC
            `;
            queryParams.push(`%${params.drugName || params.className || ''}%`);
            paramIndex++;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const classifications: RxClassDrugClassification[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                rxcui: row.rxcui,
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                rela: row.rela,
                rela_description: row.rela_description,
                class_url: row.class_url,
                drug_url: row.drug_url,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${classifications.length} drug classifications`);
            return classifications;

        } catch (error) {
            this.logger.error('Error searching drug classifications', { error, params });
            throw new Error(`Failed to search drug classifications: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getTherapeuticClasses(params: { classType?: string; parentClassId?: string; maxResults?: number }): Promise<RxClassTherapeuticClass[]> {
        this.logger.info('Getting therapeutic classes', { params });

        try {
            let query = `
                SELECT 
                    class_id, class_name, class_type, description, parent_class_id,
                    parent_class_name, level, drug_count, example_drugs
                FROM ${this.classesTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.classType) {
                query += ` AND class_type = $${paramIndex}`;
                queryParams.push(params.classType);
                paramIndex++;
            }

            if (params.parentClassId) {
                query += ` AND parent_class_id = $${paramIndex}`;
                queryParams.push(params.parentClassId);
                paramIndex++;
            }

            query += ` ORDER BY class_type, level, class_name`;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const classes: RxClassTherapeuticClass[] = result.rows.map(row => ({
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                description: row.description,
                parent_class_id: row.parent_class_id,
                parent_class_name: row.parent_class_name,
                level: row.level,
                drug_count: row.drug_count,
                example_drugs: row.example_drugs || [],
            }));

            this.logger.info(`Found ${classes.length} therapeutic classes`);
            return classes;

        } catch (error) {
            this.logger.error('Error getting therapeutic classes', { error, params });
            throw new Error(`Failed to get therapeutic classes: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsByClass(classId: string, maxResults: number = 50): Promise<RxClassDrugClassification[]> {
        this.logger.info('Getting drugs by therapeutic class', { classId, maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_name, rxcui, class_id, class_name, class_type,
                    rela, rela_description, class_url, drug_url, last_updated
                FROM ${this.classificationsTable}
                WHERE class_id = $1
                ORDER BY drug_name ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [classId, maxResults]);
            
            const drugs: RxClassDrugClassification[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                rxcui: row.rxcui,
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                rela: row.rela,
                rela_description: row.rela_description,
                class_url: row.class_url,
                drug_url: row.drug_url,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${drugs.length} drugs in therapeutic class`);
            return drugs;

        } catch (error) {
            this.logger.error('Error getting drugs by class', { error, classId });
            throw new Error(`Failed to get drugs by class: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getClassificationsByDrug(drugName: string): Promise<RxClassDrugClassification[]> {
        this.logger.info('Getting classifications by drug', { drugName });

        try {
            const query = `
                SELECT 
                    id, drug_name, rxcui, class_id, class_name, class_type,
                    rela, rela_description, class_url, drug_url, last_updated
                FROM ${this.classificationsTable}
                WHERE drug_name ILIKE $1
                ORDER BY 
                    CASE class_type
                        WHEN 'ATC' THEN 1
                        WHEN 'EPC' THEN 2
                        WHEN 'MOA' THEN 3
                        WHEN 'PE' THEN 4
                        WHEN 'PK' THEN 5
                        WHEN 'TC' THEN 6
                        WHEN 'VA' THEN 7
                        ELSE 8
                    END,
                    class_name ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const classifications: RxClassDrugClassification[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                rxcui: row.rxcui,
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                rela: row.rela,
                rela_description: row.rela_description,
                class_url: row.class_url,
                drug_url: row.drug_url,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${classifications.length} classifications for drug`);
            return classifications;

        } catch (error) {
            this.logger.error('Error getting classifications by drug', { error, drugName });
            throw new Error(`Failed to get classifications by drug: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getATCClassifications(drugName?: string): Promise<RxClassDrugClassification[]> {
        this.logger.info('Getting ATC classifications', { drugName });

        try {
            let query = `
                SELECT 
                    id, drug_name, rxcui, class_id, class_name, class_type,
                    rela, rela_description, class_url, drug_url, last_updated
                FROM ${this.classificationsTable}
                WHERE class_type = 'ATC'
            `;

            const queryParams: any[] = [];
            if (drugName) {
                query += ` AND drug_name ILIKE $1`;
                queryParams.push(`%${drugName}%`);
            }

            query += ` ORDER BY class_name ASC, drug_name ASC LIMIT 100`;

            const result = await this.executeQuery(query, queryParams);
            
            const atcClassifications: RxClassDrugClassification[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                rxcui: row.rxcui,
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                rela: row.rela,
                rela_description: row.rela_description,
                class_url: row.class_url,
                drug_url: row.drug_url,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${atcClassifications.length} ATC classifications`);
            return atcClassifications;

        } catch (error) {
            this.logger.error('Error getting ATC classifications', { error, drugName });
            throw new Error(`Failed to get ATC classifications: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getMechanismOfAction(drugName: string): Promise<RxClassDrugClassification[]> {
        this.logger.info('Getting mechanism of action classifications', { drugName });

        try {
            const query = `
                SELECT 
                    id, drug_name, rxcui, class_id, class_name, class_type,
                    rela, rela_description, class_url, drug_url, last_updated
                FROM ${this.classificationsTable}
                WHERE class_type = 'MOA' AND drug_name ILIKE $1
                ORDER BY class_name ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const moaClassifications: RxClassDrugClassification[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                rxcui: row.rxcui,
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                rela: row.rela,
                rela_description: row.rela_description,
                class_url: row.class_url,
                drug_url: row.drug_url,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${moaClassifications.length} mechanism of action classifications`);
            return moaClassifications;

        } catch (error) {
            this.logger.error('Error getting mechanism of action', { error, drugName });
            throw new Error(`Failed to get mechanism of action: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getPhysiologicEffect(drugName: string): Promise<RxClassDrugClassification[]> {
        this.logger.info('Getting physiologic effect classifications', { drugName });

        try {
            const query = `
                SELECT 
                    id, drug_name, rxcui, class_id, class_name, class_type,
                    rela, rela_description, class_url, drug_url, last_updated
                FROM ${this.classificationsTable}
                WHERE class_type = 'PE' AND drug_name ILIKE $1
                ORDER BY class_name ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const peClassifications: RxClassDrugClassification[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                rxcui: row.rxcui,
                class_id: row.class_id,
                class_name: row.class_name,
                class_type: row.class_type,
                rela: row.rela,
                rela_description: row.rela_description,
                class_url: row.class_url,
                drug_url: row.drug_url,
                last_updated: row.last_updated,
            }));

            this.logger.info(`Found ${peClassifications.length} physiologic effect classifications`);
            return peClassifications;

        } catch (error) {
            this.logger.error('Error getting physiologic effect', { error, drugName });
            throw new Error(`Failed to get physiologic effect: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getClassificationSummary(drugName: string): Promise<any> {
        this.logger.info('Getting classification summary for drug', { drugName });

        try {
            const query = `
                SELECT 
                    drug_name,
                    class_type,
                    COUNT(*) as classification_count,
                    array_agg(class_name ORDER BY class_name) as class_names,
                    array_agg(DISTINCT rela) FILTER (WHERE rela IS NOT NULL) as relationships
                FROM ${this.classificationsTable}
                WHERE drug_name ILIKE $1
                GROUP BY drug_name, class_type
                ORDER BY 
                    CASE class_type
                        WHEN 'ATC' THEN 1
                        WHEN 'EPC' THEN 2
                        WHEN 'MOA' THEN 3
                        WHEN 'PE' THEN 4
                        ELSE 5
                    END
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const summary = {
                drug_name: drugName,
                total_classifications: result.rows.reduce((sum, row) => sum + parseInt(row.classification_count), 0),
                classification_types: result.rows.map(row => ({
                    type: row.class_type,
                    count: parseInt(row.classification_count),
                    classes: row.class_names || [],
                    relationships: row.relationships || [],
                })),
            };

            this.logger.info(`Generated classification summary for drug`);
            return summary;

        } catch (error) {
            this.logger.error('Error getting classification summary', { error, drugName });
            throw new Error(`Failed to get classification summary: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getSimilarDrugs(drugName: string, classType: string = 'ATC', limit: number = 20): Promise<string[]> {
        this.logger.info('Getting similar drugs', { drugName, classType, limit });

        try {
            // First get the classes for the input drug
            const classQuery = `
                SELECT DISTINCT class_id 
                FROM ${this.classificationsTable}
                WHERE drug_name ILIKE $1 AND class_type = $2
            `;

            const classResult = await this.executeQuery(classQuery, [`%${drugName}%`, classType]);
            
            if (classResult.rows.length === 0) {
                this.logger.info('No classifications found for drug');
                return [];
            }

            const classIds = classResult.rows.map(row => row.class_id);

            // Get other drugs in the same classes
            const drugsQuery = `
                SELECT DISTINCT drug_name, COUNT(*) as shared_classes
                FROM ${this.classificationsTable}
                WHERE class_id = ANY($1) 
                AND drug_name NOT ILIKE $2
                AND class_type = $3
                GROUP BY drug_name
                ORDER BY shared_classes DESC, drug_name ASC
                LIMIT $4
            `;

            const drugsResult = await this.executeQuery(drugsQuery, [classIds, `%${drugName}%`, classType, limit]);
            
            const similarDrugs = drugsResult.rows.map(row => row.drug_name);

            this.logger.info(`Found ${similarDrugs.length} similar drugs`);
            return similarDrugs;

        } catch (error) {
            this.logger.error('Error getting similar drugs', { error, drugName, classType });
            throw new Error(`Failed to get similar drugs: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}