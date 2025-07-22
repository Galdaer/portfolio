#!/bin/bash

# Healthcare AI Development Environment Validation Script
# Validates the complete development environment for Intelluxe AI healthcare system

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation result caching
declare -A VALIDATION_RESULTS
declare -A VALIDATION_TIMESTAMPS

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CRITICAL_FAILURES=0
WARNINGS=0

# Caching functions
cache_validation_result() {
    local test_name="$1"
    local result="$2"
    VALIDATION_RESULTS["$test_name"]="$result"
    VALIDATION_TIMESTAMPS["$test_name"]=$(date +%s)
}

get_cached_validation_result() {
    local test_name="$1"
    local max_age="${2:-300}"  # 5 minutes default

    if [[ -n "${VALIDATION_RESULTS[$test_name]:-}" ]]; then
        local timestamp="${VALIDATION_TIMESTAMPS[$test_name]}"
        local current_time
        current_time=$(date +%s)
        local age=$((current_time - timestamp))

        if [[ $age -lt $max_age ]]; then
            echo "${VALIDATION_RESULTS[$test_name]}"
            return 0
        fi
    fi
    return 1
}

# Validation functions
validate_python_environment() {
    log_info "Validating Python environment..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        if [[ "$PYTHON_VERSION" =~ ^3\.(9|10|11|12) ]]; then
            log_success "Python version: $PYTHON_VERSION"
        else
            log_error "Python version $PYTHON_VERSION not supported. Requires 3.9+"
            ((CRITICAL_FAILURES++))
        fi
    else
        log_error "Python3 not found"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        log_success "Virtual environment active: $VIRTUAL_ENV"
    else
        log_warning "No virtual environment detected"
        ((WARNINGS++))
    fi
    
    # Check required packages
    local required_packages=(
        "fastapi"
        "uvicorn"
        "psycopg2"
        "redis"
        "cryptography"
        "deepeval"
        "presidio-analyzer"
        "structlog"
    )
    
    for package in "${required_packages[@]}"; do
        if python3 -c "import $package" 2>/dev/null; then
            log_success "Package $package: installed"
        else
            log_error "Package $package: missing"
            ((CRITICAL_FAILURES++))
        fi
    done
}

validate_database_connections() {
    log_info "Validating database connections..."
    
    # PostgreSQL connection
    if command -v psql &> /dev/null; then
        local pg_host="${POSTGRES_HOST:-localhost}"
        local pg_port="${POSTGRES_PORT:-5432}"
        local pg_db="${POSTGRES_DB:-intelluxe}"
        local pg_user="${POSTGRES_USER:-intelluxe}"
        
        if PGPASSWORD="${POSTGRES_PASSWORD:-intelluxe}" psql -h "$pg_host" -p "$pg_port" -U "$pg_user" -d "$pg_db" -c "SELECT 1;" &>/dev/null; then
            log_success "PostgreSQL connection: OK"
        else
            log_error "PostgreSQL connection: FAILED"
            ((CRITICAL_FAILURES++))
        fi
    else
        log_warning "psql not found, skipping PostgreSQL test"
        ((WARNINGS++))
    fi
    
    # Redis connection
    if command -v redis-cli &> /dev/null; then
        local redis_host="${REDIS_HOST:-localhost}"
        local redis_port="${REDIS_PORT:-6379}"
        
        if redis-cli -h "$redis_host" -p "$redis_port" ping | grep -q "PONG"; then
            log_success "Redis connection: OK"
        else
            log_error "Redis connection: FAILED"
            ((CRITICAL_FAILURES++))
        fi
    else
        log_warning "redis-cli not found, skipping Redis test"
        ((WARNINGS++))
    fi
}

validate_ollama_service() {
    log_info "Validating Ollama service..."
    
    local ollama_host="${OLLAMA_HOST:-localhost}"
    local ollama_port="${OLLAMA_PORT:-11434}"
    local ollama_url="http://$ollama_host:$ollama_port"
    
    # Check Ollama health
    if curl -sf "$ollama_url/api/version" &>/dev/null; then
        log_success "Ollama service: running"
        
        # Check required models
        local required_models=(
            "llama3.1:8b-instruct-q4_K_M"
            "mistral:7b-instruct-q4_K_M"
        )
        
        local available_models
        available_models=$(curl -s "$ollama_url/api/tags" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = [model['name'] for model in data.get('models', [])]
    print(' '.join(models))
except:
    print('')
")
        
        for model in "${required_models[@]}"; do
            if echo "$available_models" | grep -q "$model"; then
                log_success "Model $model: available"
            else
                log_warning "Model $model: not available"
                ((WARNINGS++))
            fi
        done
    else
        log_error "Ollama service: not running"
        ((CRITICAL_FAILURES++))
    fi
}

validate_healthcare_components() {
    log_info "Validating healthcare-specific components..."
    
    # Check PHI detection
    if python3 -c "
from src.healthcare_mcp.phi_detection import PHIDetector
detector = PHIDetector()
result = detector.detect_phi_sync('John Smith, SSN: 123-45-6789')
assert result.phi_detected, 'PHI detection failed'
print('PHI detection: OK')
" 2>/dev/null; then
        log_success "PHI detection: functional"
    else
        log_error "PHI detection: failed"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check encryption manager
    if python3 -c "
import psycopg2
from src.security.encryption_manager import HealthcareEncryptionManager
# Mock connection for testing
class MockConn:
    def cursor(self): return self
    def execute(self, *args): pass
    def fetchall(self): return []
    def fetchone(self): return None
    def commit(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass

conn = MockConn()
manager = HealthcareEncryptionManager(conn)
print('Encryption manager: OK')
" 2>/dev/null; then
        log_success "Encryption manager: functional"
    else
        log_error "Encryption manager: failed"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check RBAC system
    if python3 -c "
from src.security.rbac_foundation import HealthcareRBACManager, Permission, ResourceType
# Mock connection for testing
class MockConn:
    def cursor(self): return self
    def execute(self, *args): pass
    def fetchall(self): return []
    def fetchone(self): return None
    def commit(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass

conn = MockConn()
rbac = HealthcareRBACManager(conn)
print('RBAC system: OK')
" 2>/dev/null; then
        log_success "RBAC system: functional"
    else
        log_error "RBAC system: failed"
        ((CRITICAL_FAILURES++))
    fi
}

validate_testing_framework() {
    log_info "Validating testing framework..."
    
    # Check DeepEval
    if python3 -c "
from tests.healthcare_evaluation.deepeval_config import HealthcareEvaluationFramework
from tests.healthcare_evaluation.synthetic_data_generator import SyntheticHealthcareDataGenerator
print('DeepEval framework: OK')
" 2>/dev/null; then
        log_success "DeepEval framework: functional"
    else
        log_error "DeepEval framework: failed"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check synthetic data generation
    if python3 -c "
from tests.healthcare_evaluation.synthetic_data_generator import SyntheticHealthcareDataGenerator
generator = SyntheticHealthcareDataGenerator()
patient = generator.generate_synthetic_patient()
assert patient.patient_id.startswith('SYN-'), 'Synthetic data generation failed'
print('Synthetic data generation: OK')
" 2>/dev/null; then
        log_success "Synthetic data generation: functional"
    else
        log_error "Synthetic data generation: failed"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check pytest configuration
    if python3 -m pytest --version &>/dev/null; then
        log_success "Pytest: available"
    else
        log_error "Pytest: not available"
        ((CRITICAL_FAILURES++))
    fi
}

validate_security_configuration() {
    log_info "Validating security configuration..."
    
    # Check HIPAA configuration
    if [[ -f "$PROJECT_ROOT/config/security/hipaa_compliance.yml" ]]; then
        log_success "HIPAA configuration: present"
        
        # Validate HIPAA config structure
        if python3 -c "
import yaml
with open('config/security/hipaa_compliance.yml', 'r') as f:
    config = yaml.safe_load(f)

required_sections = [
    'administrative_safeguards',
    'physical_safeguards',
    'technical_safeguards',
    'encryption',
    'audit_monitoring'
]

for section in required_sections:
    assert section in config, f'Missing section: {section}'

print('HIPAA configuration: valid')
" 2>/dev/null; then
            log_success "HIPAA configuration: valid"
        else
            log_error "HIPAA configuration: invalid structure"
            ((CRITICAL_FAILURES++))
        fi
    else
        log_error "HIPAA configuration: missing"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check healthcare metrics configuration
    if [[ -f "$PROJECT_ROOT/config/testing/healthcare_metrics.yml" ]]; then
        log_success "Healthcare metrics configuration: present"
    else
        log_error "Healthcare metrics configuration: missing"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check pre-commit configuration
    if [[ -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]]; then
        log_success "Pre-commit configuration: present"
        
        # Check if pre-commit is installed
        if command -v pre-commit &> /dev/null; then
            log_success "Pre-commit: installed"
        else
            log_warning "Pre-commit: not installed"
            ((WARNINGS++))
        fi
    else
        log_error "Pre-commit configuration: missing"
        ((CRITICAL_FAILURES++))
    fi
}

validate_development_tools() {
    log_info "Validating development tools..."
    
    # Check VS Code configuration
    if [[ -f "$PROJECT_ROOT/.vscode/settings.json" ]]; then
        log_success "VS Code configuration: present"
    else
        log_warning "VS Code configuration: missing"
        ((WARNINGS++))
    fi
    
    # Check code quality tools
    local tools=("black" "flake8" "pylint" "mypy")
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null || python3 -m "$tool" --version &>/dev/null; then
            log_success "Code quality tool $tool: available"
        else
            log_warning "Code quality tool $tool: not available"
            ((WARNINGS++))
        fi
    done
    
    # Check AI assistant configuration
    if python3 -c "
from src.development.ai_assistant_config import HealthcareAIAssistant, AIAssistantConfig
assistant = HealthcareAIAssistant(AIAssistantConfig())
print('AI assistant: OK')
" 2>/dev/null; then
        log_success "AI assistant configuration: functional"
    else
        log_error "AI assistant configuration: failed"
        ((CRITICAL_FAILURES++))
    fi
}

validate_service_deployment() {
    log_info "Validating service deployment configuration..."
    
    # Check universal service runner
    if [[ -f "$PROJECT_ROOT/scripts/universal-service-runner.sh" ]]; then
        log_success "Universal service runner: present"
        
        # Check if it's executable
        if [[ -x "$PROJECT_ROOT/scripts/universal-service-runner.sh" ]]; then
            log_success "Universal service runner: executable"
        else
            log_warning "Universal service runner: not executable"
            ((WARNINGS++))
        fi
    else
        log_error "Universal service runner: missing"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check healthcare MCP service configuration
    if [[ -f "$PROJECT_ROOT/services/user/healthcare-mcp/healthcare-mcp.conf" ]]; then
        log_success "Healthcare MCP service config: present"
    else
        log_error "Healthcare MCP service config: missing"
        ((CRITICAL_FAILURES++))
    fi
    
    # Check Docker configuration
    if [[ -f "$PROJECT_ROOT/docker/mcp-server/Dockerfile.healthcare" ]]; then
        log_success "Healthcare MCP Dockerfile: present"
    else
        log_error "Healthcare MCP Dockerfile: missing"
        ((CRITICAL_FAILURES++))
    fi
}

validate_ci_cd_pipeline() {
    log_info "Validating CI/CD pipeline..."
    
    # Check GitHub workflows
    local workflows=(
        "healthcare_evaluation.yml"
        "security_validation.yml"
    )
    
    for workflow in "${workflows[@]}"; do
        if [[ -f "$PROJECT_ROOT/.github/workflows/$workflow" ]]; then
            log_success "Workflow $workflow: present"
        else
            log_error "Workflow $workflow: missing"
            ((CRITICAL_FAILURES++))
        fi
    done
}

generate_validation_report() {
    log_info "Generating validation report..."
    
    local report_file="$PROJECT_ROOT/validation-report.md"
    
    cat > "$report_file" << EOF
# Healthcare AI Development Environment Validation Report

**Generated:** $(date -u)
**Project:** Intelluxe AI Healthcare System
**Validation Script:** $0

## Summary

- **Critical Failures:** $CRITICAL_FAILURES
- **Warnings:** $WARNINGS
- **Overall Status:** $([ "$CRITICAL_FAILURES" -eq 0 ] && echo "✅ PASSED" || echo "❌ FAILED")

## Validation Results

### Python Environment
$(validate_python_environment 2>&1 | sed 's/^/- /')

### Database Connections
$(validate_database_connections 2>&1 | sed 's/^/- /')

### Ollama Service
$(validate_ollama_service 2>&1 | sed 's/^/- /')

### Healthcare Components
$(validate_healthcare_components 2>&1 | sed 's/^/- /')

### Testing Framework
$(validate_testing_framework 2>&1 | sed 's/^/- /')

### Security Configuration
$(validate_security_configuration 2>&1 | sed 's/^/- /')

### Development Tools
$(validate_development_tools 2>&1 | sed 's/^/- /')

### Service Deployment
$(validate_service_deployment 2>&1 | sed 's/^/- /')

### CI/CD Pipeline
$(validate_ci_cd_pipeline 2>&1 | sed 's/^/- /')

## Recommendations

$([ "$CRITICAL_FAILURES" -gt 0 ] && echo "### Critical Issues
- Address all critical failures before proceeding with development
- Ensure all required dependencies are installed
- Verify database and service connections")

$([ "$WARNINGS" -gt 0 ] && echo "### Warnings
- Review and address warnings for optimal development experience
- Install recommended development tools
- Configure optional but beneficial components")

## Next Steps

1. Fix any critical failures identified above
2. Address warnings for improved development experience
3. Run the validation script again to verify fixes
4. Proceed with healthcare AI development

---
*This report was generated automatically by the healthcare AI development environment validation script.*
EOF

    log_success "Validation report generated: $report_file"
}

run_parallel_validations() {
    log_info "🚀 Running parallel validation checks..."

    # Run independent checks in parallel
    validate_python_environment &
    validate_database_connections &
    validate_ollama_service &

    # Wait for all background jobs
    wait

    # Run dependent checks sequentially
    validate_healthcare_components
    validate_testing_framework
    validate_security_configuration
    validate_development_tools
    validate_service_deployment
    validate_ci_cd_pipeline
}

main() {
    log_info "Starting Healthcare AI Development Environment Validation"
    log_info "Project root: $PROJECT_ROOT"
    echo

    # Change to project root
    cd "$PROJECT_ROOT"

    # Check for parallel execution option
    case "${1:-}" in
        --parallel)
            run_parallel_validations
            ;;
        *)
            # Run all validations sequentially (default)
            validate_python_environment
    echo
    validate_database_connections
    echo
    validate_ollama_service
    echo
    validate_healthcare_components
    echo
    validate_testing_framework
    echo
    validate_security_configuration
    echo
    validate_development_tools
    echo
    validate_service_deployment
    echo
    validate_ci_cd_pipeline
    echo
            ;;
    esac

    # Generate report
    generate_validation_report
    echo
    
    # Final summary
    log_info "Validation Summary:"
    log_info "Critical Failures: $CRITICAL_FAILURES"
    log_info "Warnings: $WARNINGS"
    
    if [ "$CRITICAL_FAILURES" -eq 0 ]; then
        log_success "✅ Healthcare AI development environment validation PASSED"
        echo
        log_info "Your development environment is ready for healthcare AI development!"
        exit 0
    else
        log_error "❌ Healthcare AI development environment validation FAILED"
        echo
        log_error "Please address the critical failures before proceeding."
        exit 1
    fi
}

# Run main function
main "$@"
