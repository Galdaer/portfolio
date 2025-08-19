# Complete Medical Archives Setup Guide
## 4TB External Drive Configuration for Medical AI Training Data

### Overview
This guide sets up a 4TB external drive for complete medical archives (~242GB) to support comprehensive medical AI training. The setup includes:

- **Complete PubMed corpus**: ~220GB (1,219 baseline files + updates)
- **All ClinicalTrials.gov data**: ~500MB (450,000 studies with results)
- **Complete FDA databases**: ~22GB (drug labels, Orange Book, NDC, Drugs@FDA)
- **PostgreSQL migration**: Database moved to external storage
- **Medical-mirrors migration**: All current data preserved

### Prerequisites
- 4TB external drive (USB 3.0+ recommended for performance)
- Ubuntu/Linux system with sudo access
- At least 50GB free space during migration
- VS Code workspace at `/home/intelluxe`

---

## Phase 1: External Drive Setup

### Step 1: Connect and Identify Drive
```bash
# Connect the 4TB external drive and identify the device
lsblk
sudo fdisk -l

# Look for a device like /dev/sdb with ~4TB capacity
```

### Step 2: Run Drive Setup Script
```bash
# Make the setup script executable
chmod +x /home/intelluxe/scripts/setup_external_drive.sh

# Run the setup (will format the drive - ALL DATA WILL BE LOST)
sudo bash /home/intelluxe/scripts/setup_external_drive.sh
```

**What this script does:**
- ✅ Formats the 4TB drive with ext4 filesystem
- ✅ Creates partition table and single partition
- ✅ Mounts drive at `/home/intelluxe/database/`
- ✅ Adds automatic mount to `/etc/fstab`
- ✅ Creates directory structure for medical data
- ✅ Tests drive performance (read/write speeds)
- ✅ Sets correct ownership permissions

### Step 3: Verify Drive Setup
```bash
# Check if drive is mounted
mountpoint /home/intelluxe/database

# Check available space
df -h /home/intelluxe/database

# List created directory structure
ls -la /home/intelluxe/database/
```

**Expected output:**
```
/home/intelluxe/database/
├── medical_complete/
│   ├── pubmed_complete/
│   │   ├── baseline/
│   │   └── updates/
│   ├── clinicaltrials_complete/
│   └── fda_complete/
│       ├── drug_labels/
│       ├── orange_book/
│       ├── ndc_directory/
│       └── drugs_fda/
├── postgresql_data/
├── medical_mirrors_data/
├── backups/
└── logs/
```

---

## Phase 2: Data Migration

### Step 1: Run Migration Script
```bash
# Make the migration script executable
chmod +x /home/intelluxe/scripts/migrate_medical_data.sh

# Run the migration (will temporarily stop services)
bash /home/intelluxe/scripts/migrate_medical_data.sh
```

**What this script does:**
- ✅ Creates backup of current configurations
- ✅ Stops PostgreSQL and medical-mirrors services
- ✅ Migrates PostgreSQL data to external drive
- ✅ Migrates existing medical-mirrors data
- ✅ Updates configuration files for new paths
- ✅ Updates VS Code settings for external drive
- ✅ Restarts services with new data locations
- ✅ Verifies migration success

### Step 2: Verify Migration
```bash
# Check PostgreSQL is running with new data location
sudo systemctl status postgresql
sudo -u postgres psql -c "SHOW data_directory;"

# Check medical-mirrors service
cd /home/intelluxe/services/user/medical-mirrors
make status

# Test API endpoints
curl http://localhost:8081/health
curl http://localhost:8081/status
```

### Step 3: Test Data Access
```bash
# Test PubMed search
curl "http://localhost:8081/pubmed/search?query=diabetes&max_results=5"

# Test ClinicalTrials search
curl "http://localhost:8081/trials/search?condition=diabetes&max_results=5"

# Test FDA search
curl "http://localhost:8081/fda/search?generic_name=insulin&max_results=5"
```

---

## Phase 3: Complete Medical Archives Download

### Step 1: Estimate Download Requirements
```bash
# Check size estimates for complete download
python3 /home/intelluxe/scripts/download_full_medical_archives.py --estimate-only
```

**Expected output:**
```
=== COMPLETE MEDICAL ARCHIVES SIZE ESTIMATES ===

📊 PUBMED_COMPLETE:
   baseline_files: ~1,219 files x ~100MB = ~120GB
   update_files: ~2,000 files x ~50MB = ~100GB
   total: ~220GB (complete PubMed corpus)
   articles: ~36 million articles (1946-present)
   value: Complete medical literature - ESSENTIAL for medical AI

📊 CLINICALTRIALS_COMPLETE:
   all_studies: ~450,000 studies x ~1MB = ~450MB
   total: ~500MB (all ClinicalTrials.gov data)
   studies: All trials since 1999 with results
   value: Treatment outcomes & efficacy data - CRITICAL for evidence-based medicine

📊 FDA_COMPLETE:
   drug_labels: 13 files x ~1.5GB = ~20GB
   orange_book: ~100MB
   ndc_directory: ~500MB
   drugs_fda: ~1GB
   total: ~22GB (complete FDA drug database)
   value: Complete drug safety & prescribing information

📊 GRAND_TOTAL:
   estimated_size: ~242GB
   vs_current: Current ~15GB vs Full ~242GB
   medical_coverage: Complete vs Partial medical knowledge
```

### Step 2: Start Complete Download
```bash
# Download everything (will take several hours)
python3 /home/intelluxe/scripts/download_full_medical_archives.py \
    --data-dir /home/intelluxe/database/medical_complete

# OR download specific datasets:

# PubMed only (~220GB)
python3 /home/intelluxe/scripts/download_full_medical_archives.py \
    --pubmed-only --data-dir /home/intelluxe/database/medical_complete

# ClinicalTrials only (~500MB)
python3 /home/intelluxe/scripts/download_full_medical_archives.py \
    --clinicaltrials-only --data-dir /home/intelluxe/database/medical_complete

# FDA only (~22GB)
python3 /home/intelluxe/scripts/download_full_medical_archives.py \
    --fda-only --data-dir /home/intelluxe/database/medical_complete
```

### Step 3: Monitor Download Progress
```bash
# Monitor disk usage during downloads
watch -n 30 'df -h /home/intelluxe/database && echo "---" && du -h /home/intelluxe/database/medical_complete'

# Check download logs
tail -f /home/intelluxe/database/logs/full_download.log

# Monitor download directory growth
ls -lah /home/intelluxe/database/medical_complete/
```

---

## Phase 4: VS Code Integration

### Step 1: Verify VS Code Settings Update
```bash
# Check that VS Code settings include external drive configuration
grep -A5 -B5 "database" /home/intelluxe/.vscode/settings.json
```

### Step 2: Open Medical Data in VS Code
```bash
# Open workspace with external drive visible
code /home/intelluxe

# Navigate to medical data
# File Explorer -> database -> medical_complete
```

### Step 3: Configure Exclusions for Performance
The migration script automatically adds these VS Code exclusions:
```json
{
    "files.watcherExclude": {
        "**/database/medical_complete/**": true,
        "**/database/postgresql_data/**": true
    },
    "medical.dataPath": "/home/intelluxe/database"
}
```

---

## Phase 5: Performance Optimization

### Step 1: Monitor Drive Performance
```bash
# Test current read/write speeds
sudo hdparm -Tt /dev/sdb1  # Replace sdb1 with your partition

# Monitor I/O usage
sudo iotop

# Check drive health
sudo smartctl -a /dev/sdb  # Replace sdb with your drive
```

### Step 2: Optimize PostgreSQL for External Drive
```bash
# Edit PostgreSQL configuration for external drive
sudo nano /etc/postgresql/*/main/postgresql.conf

# Add these optimizations for external drive:
# shared_buffers = 1GB
# effective_cache_size = 4GB
# checkpoint_segments = 32
# wal_buffers = 16MB
# checkpoint_completion_target = 0.9

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 3: Set Up Download Monitoring
```bash
# Create download monitoring script
cat > /home/intelluxe/scripts/monitor_downloads.sh << 'EOF'
#!/bin/bash
while true; do
    clear
    echo "=== Medical Data Download Monitor ==="
    echo "Time: $(date)"
    echo ""
    df -h /home/intelluxe/database
    echo ""
    echo "Directory sizes:"
    du -sh /home/intelluxe/database/medical_complete/* 2>/dev/null || echo "No data yet"
    echo ""
    echo "Recent download activity:"
    tail -10 /home/intelluxe/database/logs/full_download.log 2>/dev/null || echo "No log yet"
    sleep 30
done
EOF

chmod +x /home/intelluxe/scripts/monitor_downloads.sh
```

---

## Troubleshooting

### Drive Not Mounting
```bash
# Check if drive is detected
lsblk | grep -E "sd[b-z]"

# Manual mount
sudo mount /dev/sdb1 /home/intelluxe/database

# Check fstab entry
grep database /etc/fstab
```

### PostgreSQL Won't Start
```bash
# Check PostgreSQL logs
sudo journalctl -u postgresql -n 50

# Verify data directory permissions
sudo ls -la /home/intelluxe/database/postgresql_data

# Reset ownership if needed
sudo chown -R postgres:postgres /home/intelluxe/database/postgresql_data
```

### Medical-Mirrors Service Issues
```bash
# Check service status
cd /home/intelluxe/services/user/medical-mirrors
make status

# View logs
make logs

# Restart service
make restart
```

### Slow Download Performance
```bash
# Check network speed
speedtest-cli

# Monitor drive I/O
sudo iotop -o

# Check available RAM for caching
free -h

# Reduce parallel downloads if needed
# Edit max_workers in download script
```

### VS Code Performance Issues
```bash
# Restart VS Code language servers
# Command Palette -> "Developer: Reload Window"

# Check VS Code settings are excluding large directories
grep -C3 "watcherExclude" /home/intelluxe/.vscode/settings.json

# Monitor VS Code memory usage
ps aux | grep "code"
```

---

## Maintenance

### Weekly Checks
```bash
# Check drive health
sudo smartctl -H /dev/sdb

# Monitor available space
df -h /home/intelluxe/database

# Update medical data
cd /home/intelluxe/services/user/medical-mirrors
make update-all
```

### Monthly Backups
```bash
# Backup configurations
cp -r /home/intelluxe/.vscode /home/intelluxe/database/backups/vscode_$(date +%Y%m%d)
sudo cp /etc/postgresql/*/main/postgresql.conf /home/intelluxe/database/backups/

# Backup critical databases
sudo -u postgres pg_dumpall > /home/intelluxe/database/backups/postgres_backup_$(date +%Y%m%d).sql
```

### Space Management
```bash
# Clean old download files
find /home/intelluxe/database/medical_complete -name "*.zip" -mtime +30 -delete

# Compress old logs
find /home/intelluxe/database/logs -name "*.log" -mtime +7 -exec gzip {} \;

# Archive old backups
tar -czf /home/intelluxe/database/backups/archive_$(date +%Y%m%d).tar.gz \
    /home/intelluxe/database/backups/*.sql /home/intelluxe/database/backups/vscode_*
```

---

## Success Verification Checklist

### ✅ Drive Setup Complete
- [ ] 4TB drive formatted and mounted at `/home/intelluxe/database/`
- [ ] Directory structure created
- [ ] Automatic mounting configured in `/etc/fstab`
- [ ] Drive performance tested (>50 MB/s read/write)

### ✅ Data Migration Complete  
- [ ] PostgreSQL data migrated and service running
- [ ] Medical-mirrors data migrated and service running
- [ ] All API endpoints responding correctly
- [ ] VS Code settings updated for external drive

### ✅ Complete Archives Downloaded
- [ ] PubMed complete corpus: ~220GB
- [ ] ClinicalTrials complete data: ~500MB  
- [ ] FDA complete databases: ~22GB
- [ ] Total medical data: ~242GB accessible

### ✅ System Integration Working
- [ ] Medical-mirrors APIs serving complete data
- [ ] VS Code workspace includes external drive
- [ ] PostgreSQL using external drive storage
- [ ] All services auto-start on boot

---

## Contact and Support

For issues with this setup:

1. **Drive/Hardware Issues**: Check system logs with `dmesg` and `journalctl`
2. **PostgreSQL Issues**: Check `/var/log/postgresql/` logs
3. **Medical-mirrors Issues**: Check service logs in `/home/intelluxe/services/user/medical-mirrors/logs/`
4. **VS Code Issues**: Check VS Code Developer Console and restart language servers

**Next Phase**: With complete medical archives in place, the system now has comprehensive medical knowledge for advanced AI training and inference across all medical domains.
