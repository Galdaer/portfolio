"""
FDA API for local mirror
Provides search functionality matching Healthcare MCP interface
"""

import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import json
from datetime import datetime

from database import FDADrug, UpdateLog
from fda.downloader import FDADownloader
from fda.parser import FDAParser

logger = logging.getLogger(__name__)


class FDAAPI:
    """Local FDA API matching Healthcare MCP interface"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.downloader = FDADownloader()
        self.parser = FDAParser()
    
    async def search_drugs(self, generic_name: str = None, ndc: str = None, max_results: int = 10) -> List[Dict]:
        """
        Search FDA drugs in local database
        Matches the interface of Healthcare MCP get-drug-info tool
        """
        logger.info(f"Searching FDA drugs for generic_name: {generic_name}, ndc: {ndc}, max_results: {max_results}")
        
        db = self.session_factory()
        try:
            # Build search query
            query_parts = []
            params = {'limit': max_results}
            
            if generic_name:
                query_parts.append("search_vector @@ plainto_tsquery(:generic_name)")
                params['generic_name'] = generic_name
                params['search_term'] = generic_name
            
            if ndc:
                query_parts.append("ndc = :ndc")
                params['ndc'] = ndc
                if not generic_name:
                    params['search_term'] = ndc
            
            if not query_parts:
                # No specific search, return recent drugs
                query_parts.append("1=1")
                params['search_term'] = ""
            
            where_clause = " AND ".join(query_parts)
            
            if params.get('search_term'):
                search_query = text(f"""
                    SELECT ndc, name, generic_name, brand_name, manufacturer, ingredients,
                           dosage_form, route, approval_date, orange_book_code, therapeutic_class,
                           ts_rank(search_vector, plainto_tsquery(:search_term)) as rank
                    FROM fda_drugs 
                    WHERE {where_clause}
                    ORDER BY rank DESC, approval_date DESC
                    LIMIT :limit
                """)
            else:
                search_query = text(f"""
                    SELECT ndc, name, generic_name, brand_name, manufacturer, ingredients,
                           dosage_form, route, approval_date, orange_book_code, therapeutic_class,
                           0 as rank
                    FROM fda_drugs 
                    WHERE {where_clause}
                    ORDER BY approval_date DESC
                    LIMIT :limit
                """)
            
            result = db.execute(search_query, params)
            
            drugs = []
            for row in result:
                drug = {
                    'ndc': row.ndc,
                    'name': row.name,
                    'genericName': row.generic_name,
                    'brandName': row.brand_name,
                    'manufacturer': row.manufacturer,
                    'ingredients': row.ingredients or [],
                    'dosageForm': row.dosage_form,
                    'route': row.route,
                    'approvalDate': row.approval_date,
                    'orangeBookCode': row.orange_book_code,
                    'therapeuticClass': row.therapeutic_class
                }
                drugs.append(drug)
            
            logger.info(f"Found {len(drugs)} drugs")
            return drugs
            
        except Exception as e:
            logger.error(f"FDA search failed: {e}")
            raise
        finally:
            db.close()
    
    async def get_drug(self, ndc: str) -> Optional[Dict]:
        """Get specific drug by NDC"""
        db = self.session_factory()
        try:
            drug = db.query(FDADrug).filter(FDADrug.ndc == ndc).first()
            if not drug:
                return None
            
            return {
                'ndc': drug.ndc,
                'name': drug.name,
                'genericName': drug.generic_name,
                'brandName': drug.brand_name,
                'manufacturer': drug.manufacturer,
                'ingredients': drug.ingredients or [],
                'dosageForm': drug.dosage_form,
                'route': drug.route,
                'approvalDate': drug.approval_date,
                'orangeBookCode': drug.orange_book_code,
                'therapeuticClass': drug.therapeutic_class
            }
            
        finally:
            db.close()
    
    async def get_status(self) -> Dict:
        """Get status of FDA mirror"""
        db = self.session_factory()
        try:
            # Get total drug count
            total_count = db.query(func.count(FDADrug.ndc)).scalar()
            
            # Get last update info
            last_update = db.query(UpdateLog).filter(
                UpdateLog.source == 'fda'
            ).order_by(UpdateLog.started_at.desc()).first()
            
            status = {
                'source': 'fda',
                'total_drugs': total_count,
                'status': 'healthy' if total_count > 0 else 'empty',
                'last_update': last_update.started_at.isoformat() if last_update else None,
                'last_update_status': last_update.status if last_update else None
            }
            
            return status
            
        finally:
            db.close()
    
    async def trigger_update(self) -> Dict:
        """Trigger FDA data update"""
        logger.info("Triggering FDA data update")
        
        db = self.session_factory()
        try:
            # Log update start
            update_log = UpdateLog(
                source='fda',
                update_type='full',  # FDA updates are typically full refreshes
                status='in_progress',
                started_at=datetime.utcnow()
            )
            db.add(update_log)
            db.commit()
            
            # Download latest FDA data
            fda_data_dirs = await self.downloader.download_all_fda_data()
            total_processed = 0
            
            # Process each dataset
            for dataset_name, data_dir in fda_data_dirs.items():
                processed = await self.process_fda_dataset(dataset_name, data_dir, db)
                total_processed += processed
            
            # Update log
            update_log.status = 'success'
            update_log.records_processed = total_processed
            update_log.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"FDA update completed: {total_processed} drugs processed")
            return {
                'status': 'success',
                'records_processed': total_processed,
                'datasets_processed': len(fda_data_dirs)
            }
            
        except Exception as e:
            logger.error(f"FDA update failed: {e}")
            update_log.status = 'failed'
            update_log.error_message = str(e)
            update_log.completed_at = datetime.utcnow()
            db.commit()
            raise
        finally:
            db.close()
    
    async def process_fda_dataset(self, dataset_name: str, data_dir: str, db: Session) -> int:
        """Process a specific FDA dataset"""
        logger.info(f"Processing FDA dataset: {dataset_name}")
        
        import os
        processed_count = 0
        
        try:
            for file in os.listdir(data_dir):
                file_path = os.path.join(data_dir, file)
                
                if dataset_name == 'ndc' and file.endswith('.json'):
                    drugs = self.parser.parse_ndc_file(file_path)
                    stored = await self.store_drugs(drugs, db)
                    processed_count += stored
                
                elif dataset_name == 'drugs_fda' and file.endswith('.json'):
                    drugs = self.parser.parse_drugs_fda_file(file_path)
                    stored = await self.store_drugs(drugs, db)
                    processed_count += stored
                
                elif dataset_name == 'orange_book' and file.endswith(('.csv', '.txt')):
                    drugs = self.parser.parse_orange_book_file(file_path)
                    stored = await self.store_drugs(drugs, db)
                    processed_count += stored
                
                elif dataset_name == 'labels' and file.endswith('.json'):
                    drugs = self.parser.parse_drug_labels_file(file_path)
                    stored = await self.store_drugs(drugs, db)
                    processed_count += stored
            
            logger.info(f"Processed {processed_count} drugs from {dataset_name}")
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to process dataset {dataset_name}: {e}")
            return processed_count
    
    async def store_drugs(self, drugs: List[Dict], db: Session) -> int:
        """Store drugs in database"""
        stored_count = 0
        
        for drug_data in drugs:
            try:
                # Check if drug already exists
                existing = db.query(FDADrug).filter(
                    FDADrug.ndc == drug_data['ndc']
                ).first()
                
                if existing:
                    # Update existing drug
                    for key, value in drug_data.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new drug
                    drug = FDADrug(**drug_data)
                    db.add(drug)
                
                stored_count += 1
                
                # Commit in batches
                if stored_count % 100 == 0:
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Failed to store drug {drug_data.get('ndc')}: {e}")
                db.rollback()
        
        # Final commit
        db.commit()
        
        # Update search vectors
        await self.update_search_vectors(db)
        
        return stored_count
    
    async def update_search_vectors(self, db: Session):
        """Update full-text search vectors"""
        try:
            update_query = text("""
                UPDATE fda_drugs 
                SET search_vector = to_tsvector('english', 
                    COALESCE(name, '') || ' ' || 
                    COALESCE(generic_name, '') || ' ' ||
                    COALESCE(brand_name, '') || ' ' ||
                    COALESCE(manufacturer, '') || ' ' ||
                    COALESCE(array_to_string(ingredients, ' '), '') || ' ' ||
                    COALESCE(therapeutic_class, '')
                )
                WHERE search_vector IS NULL
            """)
            
            db.execute(update_query)
            db.commit()
            logger.info("Updated search vectors for FDA drugs")
            
        except Exception as e:
            logger.error(f"Failed to update search vectors: {e}")
            db.rollback()
    
    async def initialize_data(self) -> Dict:
        """Initialize FDA data"""
        logger.info("Initializing FDA data")
        
        db = self.session_factory()
        try:
            # Check if data already exists
            count = db.query(func.count(FDADrug.ndc)).scalar()
            if count > 0:
                logger.info(f"FDA data already exists: {count} drugs")
                return {'status': 'already_initialized', 'drug_count': count}
            
            # Download all FDA data
            fda_data_dirs = await self.downloader.download_all_fda_data()
            total_processed = 0
            
            # Process each dataset
            for dataset_name, data_dir in fda_data_dirs.items():
                processed = await self.process_fda_dataset(dataset_name, data_dir, db)
                total_processed += processed
                logger.info(f"Processed {processed} drugs from {dataset_name}")
            
            logger.info(f"FDA initialization completed: {total_processed} drugs")
            return {
                'status': 'initialized',
                'records_processed': total_processed,
                'datasets_processed': len(fda_data_dirs)
            }
            
        except Exception as e:
            logger.error(f"FDA initialization failed: {e}")
            raise
        finally:
            db.close()
