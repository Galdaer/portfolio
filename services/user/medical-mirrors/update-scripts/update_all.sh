#!/bin/bash
# Master update script - runs all data source updates
# Can be used for manual updates or scheduled maintenance

set -e

LOG_FILE="/app/logs/master_update.log"

echo "$(date): Starting master update for all medical data sources" >> $LOG_FILE

# Make scripts executable
chmod +x /app/update-scripts/*.sh

# Run PubMed update
echo "$(date): Running PubMed update" >> $LOG_FILE
/app/update-scripts/update_pubmed.sh

# Run ClinicalTrials update
echo "$(date): Running ClinicalTrials update" >> $LOG_FILE
/app/update-scripts/update_trials.sh

# Run FDA update
echo "$(date): Running FDA update" >> $LOG_FILE
/app/update-scripts/update_fda.sh

# Run ICD-10 codes update
echo "$(date): Running ICD-10 codes update" >> $LOG_FILE
/app/update-scripts/update_icd10.sh

# Run billing codes update
echo "$(date): Running billing codes update" >> $LOG_FILE
/app/update-scripts/update_billing.sh

# Run health information update
echo "$(date): Running health information update" >> $LOG_FILE
/app/update-scripts/update_health_info.sh

echo "$(date): Master update completed successfully" >> $LOG_FILE
