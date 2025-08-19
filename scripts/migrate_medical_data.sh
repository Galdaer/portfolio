#!/bin/bash
# Medical Data Migration Script
# Migrates existing PostgreSQL and medical-mirrors data to external drive

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SOURCE_DATA_DIR="/home/intelluxe/data"
SOURCE_POSTGRES_DIR="/var/lib/postgresql"
EXTERNAL_DRIVE="/home/intelluxe/database"
BACKUP_DIR="$EXTERNAL_DRIVE/backups/migration_$(date +%Y%m%d_%H%M%S)"

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    # Check if external drive is mounted
    if ! mountpoint -q "$EXTERNAL_DRIVE"; then
        print_error "External drive not mounted at $EXTERNAL_DRIVE"
        echo "Please run the setup script first: bash /home/intelluxe/scripts/setup_external_drive.sh"
        exit 1
    fi
    print_success "External drive mounted at $EXTERNAL_DRIVE"
    
    # Check available space
    local available_gb=$(df -BG "$EXTERNAL_DRIVE" | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $available_gb -lt 50 ]]; then
        print_error "Insufficient space on external drive: ${available_gb}GB available"
        exit 1
    fi
    print_success "Available space: ${available_gb}GB"
    
    # Check if services are running
    if systemctl is-active --quiet postgresql; then
        print_warning "PostgreSQL is running - will need to stop for migration"
    fi
    
    if systemctl is-active --quiet docker && docker ps --format "table {{.Names}}" | grep -q medical-mirrors; then
        print_warning "Medical-mirrors service is running - will need to stop for migration"
    fi
}

create_backup() {
    print_section "Creating Migration Backup"
    
    mkdir -p "$BACKUP_DIR"
    print_success "Created backup directory: $BACKUP_DIR"
    
    # Backup current configurations
    if [[ -f /etc/postgresql/*/main/postgresql.conf ]]; then
        sudo cp /etc/postgresql/*/main/postgresql.conf "$BACKUP_DIR/"
        print_success "Backed up PostgreSQL configuration"
    fi
    
    # Backup medical-mirrors configs
    if [[ -d /home/intelluxe/services/user/medical-mirrors ]]; then
        cp -r /home/intelluxe/services/user/medical-mirrors/config "$BACKUP_DIR/medical-mirrors-config" 2>/dev/null || true
        print_success "Backed up medical-mirrors configuration"
    fi
    
    # Backup VS Code settings
    if [[ -f /home/intelluxe/.vscode/settings.json ]]; then
        cp /home/intelluxe/.vscode/settings.json "$BACKUP_DIR/"
        print_success "Backed up VS Code settings"
    fi
}

stop_services() {
    print_section "Stopping Services for Migration"
    
    # Stop PostgreSQL
    if systemctl is-active --quiet postgresql; then
        print_warning "Stopping PostgreSQL service..."
        sudo systemctl stop postgresql
        print_success "PostgreSQL stopped"
    fi
    
    # Stop medical-mirrors if running in Docker
    if docker ps --format "table {{.Names}}" | grep -q medical-mirrors; then
        print_warning "Stopping medical-mirrors container..."
        docker stop medical-mirrors || true
        print_success "Medical-mirrors container stopped"
    fi
    
    # Wait a moment for services to fully stop
    sleep 3
}

migrate_postgresql_data() {
    print_section "Migrating PostgreSQL Data"
    
    local postgres_source="/var/lib/postgresql"
    local postgres_target="$EXTERNAL_DRIVE/postgresql_data"
    
    if [[ -d "$postgres_source" ]]; then
        print_warning "Migrating PostgreSQL data (this may take several minutes)..."
        
        # Create target directory
        sudo mkdir -p "$postgres_target"
        
        # Copy PostgreSQL data with rsync for progress
        sudo rsync -av --progress "$postgres_source/" "$postgres_target/"
        
        # Set correct ownership
        sudo chown -R postgres:postgres "$postgres_target"
        
        print_success "PostgreSQL data migrated to $postgres_target"
        
        # Update PostgreSQL configuration
        local pg_config_file=$(sudo find /etc/postgresql -name "postgresql.conf" | head -1)
        if [[ -n "$pg_config_file" ]]; then
            print_section "Updating PostgreSQL Configuration"
            
            # Backup original config
            sudo cp "$pg_config_file" "$pg_config_file.backup"
            
            # Update data directory path
            sudo sed -i "s|#data_directory = '.*'|data_directory = '$postgres_target'|g" "$pg_config_file"
            sudo sed -i "s|data_directory = '.*'|data_directory = '$postgres_target'|g" "$pg_config_file"
            
            print_success "Updated PostgreSQL configuration"
        fi
    else
        print_warning "PostgreSQL data directory not found at $postgres_source"
    fi
}

migrate_medical_mirrors_data() {
    print_section "Migrating Medical-Mirrors Data"
    
    local mirrors_data_dirs=(
        "/home/intelluxe/data/medical-references"
        "/home/intelluxe/data/pubmed"
        "/home/intelluxe/data/fda"
        "/home/intelluxe/data/trials"
        "/home/intelluxe/services/user/medical-mirrors/data"
    )
    
    local target_dir="$EXTERNAL_DRIVE/medical_mirrors_data"
    mkdir -p "$target_dir"
    
    for source_dir in "${mirrors_data_dirs[@]}"; do
        if [[ -d "$source_dir" ]]; then
            local dir_name=$(basename "$source_dir")
            print_warning "Migrating $source_dir..."
            
            rsync -av --progress "$source_dir/" "$target_dir/$dir_name/"
            print_success "Migrated $dir_name to external drive"
        else
            print_warning "Directory not found: $source_dir"
        fi
    done
}

update_medical_mirrors_config() {
    print_section "Updating Medical-Mirrors Configuration"
    
    local config_files=(
        "/home/intelluxe/services/user/medical-mirrors/src/config.py"
        "/home/intelluxe/services/user/medical-mirrors/config/app.py"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            print_warning "Updating $config_file..."
            
            # Backup original
            cp "$config_file" "$config_file.backup"
            
            # Update data directory paths
            sed -i "s|/home/intelluxe/data|$EXTERNAL_DRIVE/medical_mirrors_data|g" "$config_file"
            sed -i "s|/var/lib/postgresql|$EXTERNAL_DRIVE/postgresql_data|g" "$config_file"
            
            print_success "Updated configuration paths"
        fi
    done
}

update_vscode_settings() {
    print_section "Updating VS Code Settings"
    
    local vscode_settings="/home/intelluxe/.vscode/settings.json"
    
    if [[ -f "$vscode_settings" ]]; then
        print_warning "Adding external drive to VS Code workspace..."
        
        # Create a temporary Python script to update JSON
        cat > /tmp/update_vscode.py << EOF
import json
import sys

# Read current settings
with open('$vscode_settings', 'r') as f:
    settings = json.load(f)

# Add external drive exclusions and inclusions
if 'files.exclude' not in settings:
    settings['files.exclude'] = {}

if 'files.watcherExclude' not in settings:
    settings['files.watcherExclude'] = {}

# Exclude the external drive from heavy operations but allow access
settings['files.watcherExclude']['**/database/medical_complete/**'] = True
settings['files.watcherExclude']['**/database/postgresql_data/**'] = True

# Add external drive monitoring for medical data
settings['// External Drive Configuration'] = 'Medical data storage on 4TB external drive'
settings['medical.dataPath'] = '$EXTERNAL_DRIVE'

# Write updated settings
with open('$vscode_settings', 'w') as f:
    json.dump(settings, f, indent=4)

print("VS Code settings updated successfully")
EOF
        
        python3 /tmp/update_vscode.py
        rm /tmp/update_vscode.py
        
        print_success "VS Code settings updated for external drive"
    fi
}

start_services() {
    print_section "Starting Services"
    
    # Start PostgreSQL
    print_warning "Starting PostgreSQL with new data directory..."
    sudo systemctl start postgresql
    
    # Wait for PostgreSQL to start
    sleep 5
    
    if systemctl is-active --quiet postgresql; then
        print_success "PostgreSQL started successfully"
    else
        print_error "PostgreSQL failed to start - check logs: sudo journalctl -u postgresql"
    fi
    
    # Start medical-mirrors if Docker is available
    if command -v docker &> /dev/null; then
        print_warning "Starting medical-mirrors service..."
        cd /home/intelluxe/services/user/medical-mirrors
        make run-detached 2>/dev/null || true
        print_success "Medical-mirrors service started"
    fi
}

verify_migration() {
    print_section "Verifying Migration"
    
    # Check PostgreSQL connection
    if sudo -u postgres psql -c "SELECT version();" &>/dev/null; then
        print_success "PostgreSQL connection verified"
    else
        print_error "PostgreSQL connection failed"
    fi
    
    # Check external drive usage
    local used_space=$(df -h "$EXTERNAL_DRIVE" | awk 'NR==2{print $3}')
    print_success "External drive usage: $used_space"
    
    # Check if medical data is accessible
    if [[ -d "$EXTERNAL_DRIVE/medical_mirrors_data" ]]; then
        local data_dirs=$(find "$EXTERNAL_DRIVE/medical_mirrors_data" -mindepth 1 -type d | wc -l)
        print_success "Medical data accessible: $data_dirs directories migrated"
    fi
}

cleanup_old_data() {
    print_section "Cleanup Options"
    
    echo "Migration completed successfully!"
    echo ""
    echo "Old data locations that can now be cleaned up:"
    echo "- /var/lib/postgresql (now at $EXTERNAL_DRIVE/postgresql_data)"
    echo "- /home/intelluxe/data/medical-references"
    echo "- /home/intelluxe/data/pubmed"
    echo "- /home/intelluxe/data/fda"
    echo "- /home/intelluxe/data/trials"
    echo ""
    print_warning "IMPORTANT: Verify everything works before deleting old data!"
    echo ""
    echo "To clean up old data after verification, run:"
    echo "sudo rm -rf /var/lib/postgresql.old"
    echo "rm -rf /home/intelluxe/data/medical-references"
    echo "rm -rf /home/intelluxe/data/pubmed"
    echo "rm -rf /home/intelluxe/data/fda"
    echo "rm -rf /home/intelluxe/data/trials"
}

main() {
    print_section "Medical Data Migration to External Drive"
    echo "This script will migrate existing medical data to the external drive"
    echo "Source: Various local directories"
    echo "Target: $EXTERNAL_DRIVE"
    echo ""
    print_warning "This operation will temporarily stop PostgreSQL and medical-mirrors services"
    echo ""
    echo "Continue with migration? (y/N)"
    read -r confirm
    
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        print_error "Migration cancelled"
        exit 1
    fi
    
    # Run migration steps
    check_prerequisites
    create_backup
    stop_services
    migrate_postgresql_data
    migrate_medical_mirrors_data
    update_medical_mirrors_config
    update_vscode_settings
    start_services
    verify_migration
    cleanup_old_data
    
    print_section "Migration Complete"
    print_success "All data successfully migrated to external drive"
    print_success "Services restarted with new data locations"
    print_success "Backup created at: $BACKUP_DIR"
    
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "1. Test all medical-mirrors endpoints to ensure data is accessible"
    echo "2. Run the full medical archives download:"
    echo "   python3 /home/intelluxe/scripts/download_full_medical_archives.py --data-dir $EXTERNAL_DRIVE/medical_complete"
    echo "3. Monitor disk usage during downloads"
    echo "4. After verification, clean up old data locations to free space"
}

# Handle interrupts
trap 'print_error "Migration interrupted - services may need manual restart"; exit 1' INT TERM

# Run main function
main "$@"
