#!/bin/bash
# Comprehensive linting for healthcare codebase

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_ISSUES=0
CRITICAL_ISSUES=0

echo -e "${BLUE}🔍 Running comprehensive code quality checks...${NC}"
echo "=================================================="

# Function to log results
log_result() {
    local tool="$1"
    local status="$2"
    local issues="$3"
    
    if [ "$status" -eq 0 ]; then
        echo -e "${GREEN}✅ $tool: PASSED${NC}"
    else
        echo -e "${RED}❌ $tool: FAILED ($issues issues found)${NC}"
        TOTAL_ISSUES=$((TOTAL_ISSUES + issues))
        if [ "$tool" = "Security scanning" ] || [ "$tool" = "PHI pattern check" ]; then
            CRITICAL_ISSUES=$((CRITICAL_ISSUES + issues))
        fi
    fi
}

# Python linting with flake8
echo -e "${YELLOW}📋 Python linting (flake8)...${NC}"
if flake8 --max-line-length=100 --extend-ignore=E203,W503 \
    --exclude=.git,__pycache__,venv,env,.venv,.env \
    src/ tests/ scripts/*.py > flake8-report.txt 2>&1; then
    log_result "Python linting" 0 0
else
    issues=$(wc -l < flake8-report.txt)
    log_result "Python linting" 1 "$issues"
    echo "  📄 Report saved to: flake8-report.txt"
fi

# Python formatting check with black
echo -e "${YELLOW}🎨 Python formatting (black)...${NC}"
if black --check --diff src/ tests/ scripts/*.py > black-report.txt 2>&1; then
    log_result "Python formatting" 0 0
else
    issues=$(grep -c "would reformat" black-report.txt || echo "0")
    log_result "Python formatting" 1 "$issues"
    echo "  📄 Report saved to: black-report.txt"
fi

# Python import sorting with isort
echo -e "${YELLOW}📦 Import sorting (isort)...${NC}"
if isort --check-only --diff src/ tests/ scripts/*.py > isort-report.txt 2>&1; then
    log_result "Import sorting" 0 0
else
    issues=$(grep -c "ERROR" isort-report.txt || echo "0")
    log_result "Import sorting" 1 "$issues"
    echo "  📄 Report saved to: isort-report.txt"
fi

# Shell script linting with shellcheck
echo -e "${YELLOW}🐚 Shell script linting (shellcheck)...${NC}"
shell_issues=0
if command -v shellcheck >/dev/null 2>&1; then
    for script in scripts/*.sh; do
        if [ -f "$script" ]; then
            if ! shellcheck -x "$script" >> shellcheck-report.txt 2>&1; then
                shell_issues=$((shell_issues + 1))
            fi
        fi
    done
    
    if [ $shell_issues -eq 0 ]; then
        log_result "Shell script linting" 0 0
    else
        log_result "Shell script linting" 1 "$shell_issues"
        echo "  📄 Report saved to: shellcheck-report.txt"
    fi
else
    echo -e "${YELLOW}⚠️  shellcheck not installed - skipping shell script linting${NC}"
fi

# Security scanning with bandit
echo -e "${YELLOW}🔒 Security scanning (bandit)...${NC}"
if command -v bandit >/dev/null 2>&1; then
    if bandit -r src/ -f json -o bandit-report.json > /dev/null 2>&1; then
        log_result "Security scanning" 0 0
    else
        issues=$(jq '.results | length' bandit-report.json 2>/dev/null || echo "unknown")
        log_result "Security scanning" 1 "$issues"
        echo "  📄 Report saved to: bandit-report.json"
    fi
else
    echo -e "${YELLOW}⚠️  bandit not installed - skipping security scanning${NC}"
fi

# Healthcare-specific PHI pattern checks
echo -e "${YELLOW}🏥 Healthcare PHI pattern checks...${NC}"
phi_issues=0

# Check for potential PHI patterns in code
echo "Checking for potential PHI patterns in source code..."

# SSN patterns
ssn_matches=$(grep -r "\\b[0-9]\\{3\\}-[0-9]\\{2\\}-[0-9]\\{4\\}\\b" src/ tests/ || true)
if [ -n "$ssn_matches" ]; then
    phi_issues=$((phi_issues + 1))
    echo "⚠️  Found potential SSN patterns:"
    echo "$ssn_matches" | head -5
fi

# Phone number patterns
phone_matches=$(grep -r "\\b[0-9]\\{3\\}-[0-9]\\{3\\}-[0-9]\\{4\\}\\b" src/ tests/ || true)
if [ -n "$phone_matches" ]; then
    phi_issues=$((phi_issues + 1))
    echo "⚠️  Found potential phone number patterns:"
    echo "$phone_matches" | head -5
fi

# Email patterns (excluding obvious test emails)
email_matches=$(grep -r "[a-zA-Z0-9._%+-]\\+@[a-zA-Z0-9.-]\\+\\.[a-zA-Z]\\{2,\\}" src/ tests/ | grep -v "test@" | grep -v "example.com" || true)
if [ -n "$email_matches" ]; then
    phi_issues=$((phi_issues + 1))
    echo "⚠️  Found potential email patterns:"
    echo "$email_matches" | head -5
fi

if [ $phi_issues -eq 0 ]; then
    log_result "PHI pattern check" 0 0
else
    log_result "PHI pattern check" 1 "$phi_issues"
fi

# Type checking with mypy (if available)
echo -e "${YELLOW}🔍 Type checking (mypy)...${NC}"
if command -v mypy >/dev/null 2>&1; then
    if mypy src/ --ignore-missing-imports > mypy-report.txt 2>&1; then
        log_result "Type checking" 0 0
    else
        issues=$(grep -c "error:" mypy-report.txt || echo "0")
        log_result "Type checking" 1 "$issues"
        echo "  📄 Report saved to: mypy-report.txt"
    fi
else
    echo -e "${YELLOW}⚠️  mypy not installed - skipping type checking${NC}"
fi

# Documentation validation
echo -e "${YELLOW}📚 Documentation validation...${NC}"
doc_issues=0

# Check for missing docstrings in Python files
echo "Checking for missing docstrings..."
missing_docstrings=$(find src/ -name "*.py" -exec grep -L '"""' {} \; | wc -l)
if [ "$missing_docstrings" -gt 0 ]; then
    doc_issues=$((doc_issues + missing_docstrings))
fi

# Check for TODO/FIXME comments
echo "Checking for TODO/FIXME comments..."
todo_comments=$(grep -r "TODO\|FIXME" src/ tests/ | wc -l || echo "0")
if [ "$todo_comments" -gt 0 ]; then
    doc_issues=$((doc_issues + todo_comments))
    echo "  Found $todo_comments TODO/FIXME comments"
fi

if [ $doc_issues -eq 0 ]; then
    log_result "Documentation validation" 0 0
else
    log_result "Documentation validation" 1 "$doc_issues"
fi

# Final summary
echo ""
echo "=================================================="
echo -e "${BLUE}📊 LINTING SUMMARY${NC}"
echo "=================================================="

if [ $TOTAL_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Code quality is excellent.${NC}"
    exit 0
elif [ $CRITICAL_ISSUES -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Found $TOTAL_ISSUES non-critical issues.${NC}"
    echo "Consider fixing these issues to improve code quality."
    exit 1
else
    echo -e "${RED}❌ Found $TOTAL_ISSUES total issues, including $CRITICAL_ISSUES critical security issues.${NC}"
    echo "Critical issues must be fixed before deployment!"
    exit 2
fi
