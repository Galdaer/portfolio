import { DatabaseConnector } from '../DatabaseConnector';
import { Logger } from '../../utils/logger';

export interface DrugCentralDrug {
    id: string;
    drug_name: string;
    cas_number?: string;
    smiles?: string;
    inchi?: string;
    inchi_key?: string;
    formula?: string;
    molecular_weight?: number;
    approval_date?: string;
    approval_status?: string;
    first_approval?: string;
    drug_type?: string;
    administration_route?: string[];
    indication?: string;
    mechanism_of_action?: string;
    pharmacodynamics?: string;
    toxicity?: string;
    half_life?: string;
    protein_binding?: string;
    metabolism?: string;
    elimination_route?: string;
    clearance?: string;
    bioavailability?: string;
    atc_codes?: string[];
    target_names?: string[];
    target_types?: string[];
    synonyms?: string[];
    trade_names?: string[];
    drug_interactions?: any[];
    contraindications?: string[];
    black_box_warnings?: string[];
}

export interface DrugCentralTarget {
    target_id: string;
    target_name: string;
    target_type: string;
    organism: string;
    gene_name?: string;
    protein_accession?: string;
    description?: string;
    drugs_count?: number;
    associated_drugs?: string[];
}

export interface DrugCentralSearchParams {
    drugName?: string;
    casNumber?: string;
    atcCode?: string;
    targetName?: string;
    indication?: string;
    mechanismOfAction?: string;
    drugType?: string;
    approvalStatus?: string;
    maxResults?: number;
}

export class DrugCentralConnector extends DatabaseConnector {
    private readonly drugsTable = 'drugcentral_drugs';
    private readonly targetsTable = 'drugcentral_targets';
    private readonly interactionsTable = 'drugcentral_drug_interactions';
    private readonly logger = Logger.getInstance();

    async searchDrugs(params: DrugCentralSearchParams): Promise<DrugCentralDrug[]> {
        this.logger.info('Searching DrugCentral drugs', { params });

        try {
            let query = `
                SELECT 
                    id, drug_name, cas_number, smiles, inchi, inchi_key, formula,
                    molecular_weight, approval_date, approval_status, first_approval,
                    drug_type, administration_route, indication, mechanism_of_action,
                    pharmacodynamics, toxicity, half_life, protein_binding,
                    metabolism, elimination_route, clearance, bioavailability,
                    atc_codes, target_names, target_types, synonyms, trade_names,
                    drug_interactions, contraindications, black_box_warnings
                FROM ${this.drugsTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.drugName) {
                query += ` AND (drug_name ILIKE $${paramIndex} OR synonyms::text ILIKE $${paramIndex} OR trade_names::text ILIKE $${paramIndex})`;
                queryParams.push(`%${params.drugName}%`);
                paramIndex++;
            }

            if (params.casNumber) {
                query += ` AND cas_number = $${paramIndex}`;
                queryParams.push(params.casNumber);
                paramIndex++;
            }

            if (params.atcCode) {
                query += ` AND atc_codes::text ILIKE $${paramIndex}`;
                queryParams.push(`%${params.atcCode}%`);
                paramIndex++;
            }

            if (params.targetName) {
                query += ` AND target_names::text ILIKE $${paramIndex}`;
                queryParams.push(`%${params.targetName}%`);
                paramIndex++;
            }

            if (params.indication) {
                query += ` AND indication ILIKE $${paramIndex}`;
                queryParams.push(`%${params.indication}%`);
                paramIndex++;
            }

            if (params.mechanismOfAction) {
                query += ` AND mechanism_of_action ILIKE $${paramIndex}`;
                queryParams.push(`%${params.mechanismOfAction}%`);
                paramIndex++;
            }

            if (params.drugType) {
                query += ` AND drug_type = $${paramIndex}`;
                queryParams.push(params.drugType);
                paramIndex++;
            }

            if (params.approvalStatus) {
                query += ` AND approval_status = $${paramIndex}`;
                queryParams.push(params.approvalStatus);
                paramIndex++;
            }

            query += ` ORDER BY 
                CASE 
                    WHEN drug_name ILIKE $${paramIndex} THEN 1
                    WHEN synonyms::text ILIKE $${paramIndex} THEN 2
                    WHEN trade_names::text ILIKE $${paramIndex} THEN 3
                    ELSE 4
                END,
                drug_name ASC
            `;
            queryParams.push(`%${params.drugName || ''}%`);
            paramIndex++;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const drugs: DrugCentralDrug[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                cas_number: row.cas_number,
                smiles: row.smiles,
                inchi: row.inchi,
                inchi_key: row.inchi_key,
                formula: row.formula,
                molecular_weight: row.molecular_weight,
                approval_date: row.approval_date,
                approval_status: row.approval_status,
                first_approval: row.first_approval,
                drug_type: row.drug_type,
                administration_route: row.administration_route || [],
                indication: row.indication,
                mechanism_of_action: row.mechanism_of_action,
                pharmacodynamics: row.pharmacodynamics,
                toxicity: row.toxicity,
                half_life: row.half_life,
                protein_binding: row.protein_binding,
                metabolism: row.metabolism,
                elimination_route: row.elimination_route,
                clearance: row.clearance,
                bioavailability: row.bioavailability,
                atc_codes: row.atc_codes || [],
                target_names: row.target_names || [],
                target_types: row.target_types || [],
                synonyms: row.synonyms || [],
                trade_names: row.trade_names || [],
                drug_interactions: row.drug_interactions || [],
                contraindications: row.contraindications || [],
                black_box_warnings: row.black_box_warnings || [],
            }));

            this.logger.info(`Found ${drugs.length} DrugCentral drugs`);
            return drugs;

        } catch (error) {
            this.logger.error('Error searching DrugCentral drugs', { error, params });
            throw new Error(`Failed to search DrugCentral drugs: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugById(id: string): Promise<DrugCentralDrug | null> {
        this.logger.info('Getting DrugCentral drug by ID', { id });

        try {
            const query = `
                SELECT 
                    id, drug_name, cas_number, smiles, inchi, inchi_key, formula,
                    molecular_weight, approval_date, approval_status, first_approval,
                    drug_type, administration_route, indication, mechanism_of_action,
                    pharmacodynamics, toxicity, half_life, protein_binding,
                    metabolism, elimination_route, clearance, bioavailability,
                    atc_codes, target_names, target_types, synonyms, trade_names,
                    drug_interactions, contraindications, black_box_warnings
                FROM ${this.drugsTable}
                WHERE id = $1
            `;

            const result = await this.executeQuery(query, [id]);

            if (result.rows.length === 0) {
                this.logger.info('DrugCentral drug not found', { id });
                return null;
            }

            const row = result.rows[0];
            const drug: DrugCentralDrug = {
                id: row.id,
                drug_name: row.drug_name,
                cas_number: row.cas_number,
                smiles: row.smiles,
                inchi: row.inchi,
                inchi_key: row.inchi_key,
                formula: row.formula,
                molecular_weight: row.molecular_weight,
                approval_date: row.approval_date,
                approval_status: row.approval_status,
                first_approval: row.first_approval,
                drug_type: row.drug_type,
                administration_route: row.administration_route || [],
                indication: row.indication,
                mechanism_of_action: row.mechanism_of_action,
                pharmacodynamics: row.pharmacodynamics,
                toxicity: row.toxicity,
                half_life: row.half_life,
                protein_binding: row.protein_binding,
                metabolism: row.metabolism,
                elimination_route: row.elimination_route,
                clearance: row.clearance,
                bioavailability: row.bioavailability,
                atc_codes: row.atc_codes || [],
                target_names: row.target_names || [],
                target_types: row.target_types || [],
                synonyms: row.synonyms || [],
                trade_names: row.trade_names || [],
                drug_interactions: row.drug_interactions || [],
                contraindications: row.contraindications || [],
                black_box_warnings: row.black_box_warnings || [],
            };

            this.logger.info('Found DrugCentral drug', { id });
            return drug;

        } catch (error) {
            this.logger.error('Error getting DrugCentral drug by ID', { error, id });
            throw new Error(`Failed to get DrugCentral drug: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async searchTargets(params: { targetName?: string; targetType?: string; organism?: string; maxResults?: number }): Promise<DrugCentralTarget[]> {
        this.logger.info('Searching DrugCentral targets', { params });

        try {
            let query = `
                SELECT 
                    target_id, target_name, target_type, organism, gene_name,
                    protein_accession, description, drugs_count, associated_drugs
                FROM ${this.targetsTable}
                WHERE 1=1
            `;

            const queryParams: any[] = [];
            let paramIndex = 1;

            if (params.targetName) {
                query += ` AND (target_name ILIKE $${paramIndex} OR gene_name ILIKE $${paramIndex})`;
                queryParams.push(`%${params.targetName}%`);
                paramIndex++;
            }

            if (params.targetType) {
                query += ` AND target_type = $${paramIndex}`;
                queryParams.push(params.targetType);
                paramIndex++;
            }

            if (params.organism) {
                query += ` AND organism ILIKE $${paramIndex}`;
                queryParams.push(`%${params.organism}%`);
                paramIndex++;
            }

            query += ` ORDER BY drugs_count DESC NULLS LAST, target_name ASC`;

            if (params.maxResults && params.maxResults > 0) {
                query += ` LIMIT $${paramIndex}`;
                queryParams.push(params.maxResults);
            }

            const result = await this.executeQuery(query, queryParams);
            
            const targets: DrugCentralTarget[] = result.rows.map(row => ({
                target_id: row.target_id,
                target_name: row.target_name,
                target_type: row.target_type,
                organism: row.organism,
                gene_name: row.gene_name,
                protein_accession: row.protein_accession,
                description: row.description,
                drugs_count: row.drugs_count,
                associated_drugs: row.associated_drugs || [],
            }));

            this.logger.info(`Found ${targets.length} DrugCentral targets`);
            return targets;

        } catch (error) {
            this.logger.error('Error searching DrugCentral targets', { error, params });
            throw new Error(`Failed to search DrugCentral targets: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugInteractions(drugName: string, maxResults: number = 50): Promise<any[]> {
        this.logger.info('Getting drug interactions from DrugCentral', { drugName, maxResults });

        try {
            const query = `
                SELECT 
                    drug_a, drug_b, interaction_type, severity, description,
                    mechanism, clinical_significance, evidence_level, source
                FROM ${this.interactionsTable}
                WHERE drug_a ILIKE $1 OR drug_b ILIKE $1
                ORDER BY 
                    CASE severity
                        WHEN 'major' THEN 1
                        WHEN 'moderate' THEN 2
                        WHEN 'minor' THEN 3
                        ELSE 4
                    END,
                    drug_a ASC, drug_b ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`, maxResults]);
            
            const interactions = result.rows.map(row => ({
                drug_a: row.drug_a,
                drug_b: row.drug_b,
                interaction_type: row.interaction_type,
                severity: row.severity,
                description: row.description,
                mechanism: row.mechanism,
                clinical_significance: row.clinical_significance,
                evidence_level: row.evidence_level,
                source: row.source,
            }));

            this.logger.info(`Found ${interactions.length} drug interactions`);
            return interactions;

        } catch (error) {
            this.logger.error('Error getting drug interactions', { error, drugName });
            throw new Error(`Failed to get drug interactions: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getPharmacokineticData(drugName: string): Promise<any[]> {
        this.logger.info('Getting pharmacokinetic data', { drugName });

        try {
            const query = `
                SELECT 
                    id, drug_name, half_life, protein_binding, metabolism,
                    elimination_route, clearance, bioavailability, administration_route,
                    formula, molecular_weight
                FROM ${this.drugsTable}
                WHERE drug_name ILIKE $1 OR synonyms::text ILIKE $1
                AND (half_life IS NOT NULL OR protein_binding IS NOT NULL OR 
                     metabolism IS NOT NULL OR clearance IS NOT NULL OR 
                     bioavailability IS NOT NULL)
                ORDER BY drug_name ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const pkData = result.rows.map(row => ({
                drug_id: row.id,
                drug_name: row.drug_name,
                half_life: row.half_life,
                protein_binding: row.protein_binding,
                metabolism: row.metabolism,
                elimination_route: row.elimination_route,
                clearance: row.clearance,
                bioavailability: row.bioavailability,
                administration_route: row.administration_route || [],
                molecular_properties: {
                    formula: row.formula,
                    molecular_weight: row.molecular_weight,
                },
            }));

            this.logger.info(`Found ${pkData.length} pharmacokinetic data records`);
            return pkData;

        } catch (error) {
            this.logger.error('Error getting pharmacokinetic data', { error, drugName });
            throw new Error(`Failed to get pharmacokinetic data: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsByTarget(targetName: string, maxResults: number = 25): Promise<DrugCentralDrug[]> {
        this.logger.info('Getting drugs by target', { targetName, maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_name, cas_number, approval_status, drug_type,
                    indication, mechanism_of_action, target_names, target_types,
                    synonyms, trade_names
                FROM ${this.drugsTable}
                WHERE target_names::text ILIKE $1
                ORDER BY 
                    CASE approval_status
                        WHEN 'approved' THEN 1
                        WHEN 'investigational' THEN 2
                        WHEN 'experimental' THEN 3
                        ELSE 4
                    END,
                    drug_name ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${targetName}%`, maxResults]);
            
            const drugs: DrugCentralDrug[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                cas_number: row.cas_number,
                approval_status: row.approval_status,
                drug_type: row.drug_type,
                indication: row.indication,
                mechanism_of_action: row.mechanism_of_action,
                target_names: row.target_names || [],
                target_types: row.target_types || [],
                synonyms: row.synonyms || [],
                trade_names: row.trade_names || [],
            }));

            this.logger.info(`Found ${drugs.length} drugs for target`);
            return drugs;

        } catch (error) {
            this.logger.error('Error getting drugs by target', { error, targetName });
            throw new Error(`Failed to get drugs by target: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getStructuralData(drugName: string): Promise<any[]> {
        this.logger.info('Getting structural data', { drugName });

        try {
            const query = `
                SELECT 
                    id, drug_name, cas_number, smiles, inchi, inchi_key,
                    formula, molecular_weight, synonyms
                FROM ${this.drugsTable}
                WHERE (drug_name ILIKE $1 OR synonyms::text ILIKE $1)
                AND (smiles IS NOT NULL OR inchi IS NOT NULL OR formula IS NOT NULL)
                ORDER BY drug_name ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const structuralData = result.rows.map(row => ({
                drug_id: row.id,
                drug_name: row.drug_name,
                cas_number: row.cas_number,
                structural_identifiers: {
                    smiles: row.smiles,
                    inchi: row.inchi,
                    inchi_key: row.inchi_key,
                },
                molecular_properties: {
                    formula: row.formula,
                    molecular_weight: row.molecular_weight,
                },
                synonyms: row.synonyms || [],
            }));

            this.logger.info(`Found ${structuralData.length} structural data records`);
            return structuralData;

        } catch (error) {
            this.logger.error('Error getting structural data', { error, drugName });
            throw new Error(`Failed to get structural data: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugsByIndicaton(indication: string, maxResults: number = 50): Promise<DrugCentralDrug[]> {
        this.logger.info('Getting drugs by indication', { indication, maxResults });

        try {
            const query = `
                SELECT 
                    id, drug_name, approval_status, drug_type, indication,
                    mechanism_of_action, synonyms, trade_names
                FROM ${this.drugsTable}
                WHERE indication ILIKE $1
                ORDER BY 
                    CASE approval_status
                        WHEN 'approved' THEN 1
                        WHEN 'investigational' THEN 2
                        WHEN 'experimental' THEN 3
                        ELSE 4
                    END,
                    drug_name ASC
                LIMIT $2
            `;

            const result = await this.executeQuery(query, [`%${indication}%`, maxResults]);
            
            const drugs: DrugCentralDrug[] = result.rows.map(row => ({
                id: row.id,
                drug_name: row.drug_name,
                approval_status: row.approval_status,
                drug_type: row.drug_type,
                indication: row.indication,
                mechanism_of_action: row.mechanism_of_action,
                synonyms: row.synonyms || [],
                trade_names: row.trade_names || [],
            }));

            this.logger.info(`Found ${drugs.length} drugs for indication`);
            return drugs;

        } catch (error) {
            this.logger.error('Error getting drugs by indication', { error, indication });
            throw new Error(`Failed to get drugs by indication: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }

    async getDrugSafetyInfo(drugName: string): Promise<any[]> {
        this.logger.info('Getting drug safety information', { drugName });

        try {
            const query = `
                SELECT 
                    id, drug_name, toxicity, contraindications, black_box_warnings,
                    drug_interactions, approval_status
                FROM ${this.drugsTable}
                WHERE drug_name ILIKE $1 OR synonyms::text ILIKE $1
                AND (toxicity IS NOT NULL OR contraindications IS NOT NULL OR 
                     black_box_warnings IS NOT NULL OR drug_interactions IS NOT NULL)
                ORDER BY drug_name ASC
            `;

            const result = await this.executeQuery(query, [`%${drugName}%`]);
            
            const safetyInfo = result.rows.map(row => ({
                drug_id: row.id,
                drug_name: row.drug_name,
                toxicity: row.toxicity,
                contraindications: row.contraindications || [],
                black_box_warnings: row.black_box_warnings || [],
                drug_interactions: row.drug_interactions || [],
                approval_status: row.approval_status,
            }));

            this.logger.info(`Found ${safetyInfo.length} safety information records`);
            return safetyInfo;

        } catch (error) {
            this.logger.error('Error getting drug safety information', { error, drugName });
            throw new Error(`Failed to get drug safety information: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    }
}