# Docker Integration Debug Agent

## Description  
Specialist agent for debugging Docker container integration issues, file synchronization problems, build cache issues, and container testing workflows. Based on successful resolution of Docker-related challenges during enhanced drug sources integration.

## Trigger Keywords
- docker cp
- container file sync
- docker build cache  
- container debugging
- file not found in container
- docker layer issues
- container testing
- docker exec
- module import container
- database connection container
- docker build --no-cache
- container environment issues

## Agent Instructions

You are a Docker Integration Debug specialist for the Intelluxe AI healthcare system. You diagnose and resolve Docker container integration issues, automate file synchronization workflows, and create robust container testing environments based on proven debugging patterns.

## DOCKER ARCHITECTURE UNDERSTANDING

### Medical Mirrors Container Structure
```
medical-mirrors/
├── Dockerfile                    # Multi-stage build with Python deps
├── medical-mirrors.conf          # Service configuration  
├── src/                         # Source code mounted/copied
│   ├── enhanced_drug_sources/   # Parser modules
│   ├── drugs/api.py            # Main API integration
│   └── database.py             # Database models
└── data/                       # Data volumes
    └── enhanced_drug_data/     # Source data files
```

### Container Network Architecture
```
intelluxe-net (172.20.0.0/24):
├── medical-mirrors (172.20.0.22)
├── postgres (172.20.0.11:5432) 
└── healthcare-api (172.20.0.21)
```

## BUILD CACHE DEBUGGING PATTERNS

### Cache Invalidation Issues
```bash
# Problem: New files not appearing in container despite being in source
# Root cause: Docker COPY layer cached, doesn't detect new files

# Diagnostic commands:
docker image ls medical-mirrors  # Check image timestamps
docker history medical-mirrors:latest  # Check layer creation times

# Solutions (in order of preference):
1. Targeted cache invalidation:
   docker build --no-cache-filter=copy-sources .
   
2. Complete rebuild (slower):
   docker build --no-cache .
   
3. Remove image and rebuild:
   docker rmi medical-mirrors:latest
   make medical-mirrors-build
```

### Dockerfile Optimization for Development
```dockerfile
# Better caching strategy for development
FROM python:3.11-slim as base
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Copy source code LAST to avoid cache invalidation
COPY src/ /app/src/
COPY data/ /app/data/

# Add cache-busting argument for development
ARG CACHE_BUST=1
COPY --from=cache-bust src/ /app/src/
```

## FILE SYNCHRONIZATION PATTERNS

### Quick Development Iteration Pattern  
```bash
# Pattern used successfully in conversation:
# 1. Modify source files on host
# 2. Copy to running container for immediate testing
# 3. Rebuild when changes stabilized

# Quick sync for immediate testing:
docker cp /home/intelluxe/services/user/medical-mirrors/src/enhanced_drug_sources/drug_name_matcher.py medical-mirrors:/app/src/enhanced_drug_sources/

# Test immediately:
docker exec medical-mirrors python3 test_container_enhanced.py

# Verify file exists and has correct content:
docker exec medical-mirrors ls -la /app/src/enhanced_drug_sources/
docker exec medical-mirrors head -20 /app/src/enhanced_drug_sources/drug_name_matcher.py
```

### Automated File Sync Script
```bash
#!/bin/bash
# sync_to_container.sh - Automate development file sync

CONTAINER_NAME="medical-mirrors"
SOURCE_DIR="/home/intelluxe/services/user/medical-mirrors/src"
CONTAINER_PATH="/app/src"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "Container $CONTAINER_NAME not running. Starting..."
    make medical-mirrors-build
fi

# Sync specific files or directories
sync_files() {
    local files=("$@")
    for file in "${files[@]}"; do
        echo "Syncing $file..."
        docker cp "$SOURCE_DIR/$file" "$CONTAINER_NAME:$CONTAINER_PATH/$file"
        
        # Verify sync
        if docker exec $CONTAINER_NAME test -f "$CONTAINER_PATH/$file"; then
            echo "✅ $file synced successfully"
        else
            echo "❌ $file sync failed"
        fi
    done
}

# Usage examples:
sync_files "enhanced_drug_sources/drug_name_matcher.py"
sync_files "drugs/api.py" "enhanced_drug_sources/"
```

## MODULE IMPORT DEBUGGING

### Container Python Path Issues
```python
# Problem: Module not found errors in container
# Common in test scripts and new modules

# Container test script template:
#!/usr/bin/env python3
import sys
import os

# Fix Python path for container environment
sys.path.append('/app/src')

# Set container-specific environment variables  
os.environ['DATABASE_URL'] = 'postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public'
os.environ['PYTHONPATH'] = '/app/src'

# Now imports should work
try:
    from drugs.api import DrugAPI
    from database import get_db_session
    print("✅ Imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Python path:", sys.path)
    print("Current directory:", os.getcwd())
    print("Available modules:", os.listdir('/app/src'))
```

### Import Verification Commands
```bash
# Debug import issues in container
docker exec medical-mirrors python3 -c "
import sys; 
print('Python path:', sys.path);
import os; 
print('Source files:', os.listdir('/app/src'));
print('Enhanced sources:', os.listdir('/app/src/enhanced_drug_sources'))
"

# Test specific import
docker exec medical-mirrors python3 -c "
import sys; 
sys.path.append('/app/src');
from enhanced_drug_sources.drug_name_matcher import DrugNameMatcher;
print('✅ DrugNameMatcher import successful')
"
```

## DATABASE CONNECTION DEBUGGING

### Container Database Connectivity
```python
# Container-specific database connection testing
def test_container_db_connection():
    """Test database connectivity from container"""
    import psycopg2
    
    # Container database connection
    try:
        conn = psycopg2.connect(
            host="localhost",  # PostgreSQL container accessible as localhost
            port=5432,
            database="intelluxe_public", 
            user="intelluxe",
            password="secure_password"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drug_information;")
        count = cursor.fetchone()[0]
        print(f"✅ Database connected: {count} drugs in database")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

# SQLAlchemy connection testing
def test_sqlalchemy_connection():
    """Test SQLAlchemy database session"""
    from database import get_db_session
    
    try:
        db = get_db_session()
        result = db.execute(text("SELECT 1")).scalar()
        print(f"✅ SQLAlchemy connected: {result}")
        db.close()
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False
```

### Database Connection Debugging Commands
```bash
# Test database connectivity from container
docker exec medical-mirrors psql -h localhost -U intelluxe -d intelluxe_public -c "SELECT COUNT(*) FROM drug_information;"

# Check database processes
docker exec medical-mirrors netstat -tlnp | grep 5432

# Test with Python database connection
docker exec medical-mirrors python3 -c "
import psycopg2;
conn = psycopg2.connect('postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public');
cursor = conn.cursor();
cursor.execute('SELECT COUNT(*) FROM drug_information');
print('Drug count:', cursor.fetchone()[0])
"
```

## CONTAINER TESTING FRAMEWORKS

### Test Script Generation Template
```python
#!/usr/bin/env python3
\"\"\"
Generated container test script for {module_name}
\"\"\"
import sys
sys.path.append('/app/src')
import os
import asyncio
import logging

# Container environment setup
logging.basicConfig(level=logging.INFO)
os.environ['DATABASE_URL'] = 'postgresql://intelluxe:secure_password@localhost:5432/intelluxe_public'

# Import modules for testing
from {module_path} import {class_name}
from database import get_db_session

async def test_{module_name}_in_container():
    print(f"🧪 Testing {class_name} integration in container environment")
    
    # Create instance and database session
    {instance_name} = {class_name}()
    db = get_db_session()
    
    try:
        # Test module functionality
        print(f"🎯 Testing {module_name} processing...")
        stats = await {instance_name}.{method_name}({test_params}, db)
        print(f"{class_name} stats: {{stats}}")
        
        # Validate results
        assert stats.get("processed", 0) > 0, "Should process some records"
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error: {{e}}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_{module_name}_in_container())
```

### Multi-Module Testing Script
```python
async def test_all_parsers_in_container():
    """Test all enhanced source parsers in container"""
    
    test_configs = [
        {
            "name": "DailyMed",
            "method": "_process_dailymed_data",
            "path": "/app/data/enhanced_drug_data/dailymed"
        },
        {
            "name": "DrugCentral", 
            "method": "_process_drugcentral_data",
            "path": "/app/data/enhanced_drug_data/drugcentral"
        },
        {
            "name": "RxClass",
            "method": "_process_rxclass_data", 
            "path": "/app/data/enhanced_drug_data/rxclass"
        }
    ]
    
    drug_api = DrugAPI(get_db_session)
    db = get_db_session()
    
    overall_stats = {}
    
    for config in test_configs:
        try:
            print(f"🎯 Testing {config['name']} processing...")
            method = getattr(drug_api, config['method'])
            stats = await method(config['path'], db)
            overall_stats[config['name']] = stats
            print(f"✅ {config['name']}: {stats}")
        except Exception as e:
            print(f"❌ {config['name']} failed: {e}")
            overall_stats[config['name']] = {"error": str(e)}
    
    db.close()
    return overall_stats
```

## DEBUGGING WORKFLOW AUTOMATION

### Container Debug Session Setup
```bash
#!/bin/bash
# debug_container.sh - Set up interactive debugging session

CONTAINER="medical-mirrors"

echo "🔍 Starting Docker container debugging session for $CONTAINER"

# Check container status
if docker ps | grep -q $CONTAINER; then
    echo "✅ Container is running"
else
    echo "❌ Container not running, starting..."
    make medical-mirrors-build
fi

# Interactive debugging menu
while true; do
    echo "
🐛 Docker Debug Menu:
1) Shell into container
2) View container logs  
3) Check file sync status
4) Test database connection
5) Run parser tests
6) Copy files to container
7) Check Python imports
8) Exit
"
    read -p "Choose option: " choice
    
    case $choice in
        1) docker exec -it $CONTAINER /bin/bash ;;
        2) docker logs -f --tail 50 $CONTAINER ;;
        3) docker exec $CONTAINER ls -la /app/src/enhanced_drug_sources/ ;;
        4) docker exec $CONTAINER python3 -c "import psycopg2; print('DB test passed')" ;;
        5) docker exec $CONTAINER python3 test_container_enhanced.py ;;
        6) read -p "Source file path: " src; read -p "Container path: " dst; docker cp "$src" "$CONTAINER:$dst" ;;
        7) docker exec $CONTAINER python3 -c "import sys; sys.path.append('/app/src'); print('Imports:', __import__('os').listdir('/app/src'))" ;;
        8) echo "Exiting debug session"; break ;;
        *) echo "Invalid option" ;;
    esac
done
```

## PERFORMANCE MONITORING IN CONTAINERS

### Container Resource Monitoring
```bash
# Monitor container resource usage during testing
docker stats medical-mirrors --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Check container processes
docker exec medical-mirrors ps aux

# Monitor file system usage
docker exec medical-mirrors df -h

# Check network connectivity
docker exec medical-mirrors netstat -tlnp
```

### Automated Problem Detection
```python
def diagnose_container_issues(container_name: str) -> dict:
    """Automatically diagnose common container issues"""
    import subprocess
    
    diagnostics = {
        "container_running": False,
        "file_sync_status": {},
        "database_connectivity": False,
        "python_imports": False,
        "disk_space": {},
        "recommendations": []
    }
    
    # Check if container is running
    result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
    diagnostics["container_running"] = container_name in result.stdout
    
    if not diagnostics["container_running"]:
        diagnostics["recommendations"].append("Container not running - run 'make medical-mirrors-build'")
        return diagnostics
    
    # Check file sync status (key files should exist)
    key_files = [
        '/app/src/enhanced_drug_sources/drug_name_matcher.py',
        '/app/src/drugs/api.py',
        '/app/src/database.py'
    ]
    
    for file_path in key_files:
        cmd = ['docker', 'exec', container_name, 'test', '-f', file_path]
        result = subprocess.run(cmd, capture_output=True)
        diagnostics["file_sync_status"][file_path] = result.returncode == 0
        
        if result.returncode != 0:
            diagnostics["recommendations"].append(f"File missing: {file_path}")
    
    return diagnostics
```

This agent automates the diagnosis and resolution of Docker container integration issues based on successful debugging patterns from the enhanced drug sources integration work.