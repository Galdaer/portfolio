---
type: "always_apply"
priority: "critical"
---

# Remote Agent Prompt Guidelines - CRITICAL RULES

## NEVER in Remote Agent Prompts

### ❌ Specific Code Implementations
- **Problem**: Guarantees formatting errors, import conflicts, structural mismatches
- **Instead**: Require codebase analysis and pattern matching

### ❌ Exact Import Statements  
- **Problem**: May not match actual file structure or existing imports
- **Instead**: Require examination of actual imports in target files

### ❌ Hardcoded Method Signatures
- **Problem**: May conflict with existing method definitions
- **Instead**: Require reading actual class definitions first

### ❌ Assumed File Contents
- **Problem**: Assumptions about code structure are often wrong
- **Instead**: Require reading actual files before modifications

### ❌ Predetermined Solutions
- **Problem**: May not address the actual root cause
- **Instead**: Require root cause analysis of actual errors

## ALWAYS in Remote Agent Prompts

### ✅ Mandatory Codebase Analysis Phase
```markdown
## MANDATORY FIRST STEP: Analyze Actual Codebase (30-45 minutes)
1. **Read actual error messages**: `make lint 2>&1 | tee errors.txt`
2. **Examine actual file structure**: `find src/ -name "*.py"`
3. **Understand actual imports**: Open files mentioned in errors
4. **Identify root causes**: Missing files? Import paths? Formatting?
```

### ✅ Systematic Error-by-Error Approach
```markdown
## SYSTEMATIC APPROACH: One Error at a Time
1. **Read the actual file** causing the error
2. **Understand what it's trying to do**
3. **Make minimal change** to fix specific error
4. **Validate immediately**: `python -m py_compile <file>`
5. **Only proceed if validation passes**
```

### ✅ Incremental Validation Workflow
```markdown
## VALIDATION WORKFLOW: After Each Change
```bash
# Individual file validation
python -m py_compile <modified_file>
flake8 --max-line-length=100 <modified_file>

# Only run full validation at the end
make lint && make validate && make test
```
```

### ✅ Pattern Matching Requirements
- **Match existing code style exactly**
- **Follow established project conventions**
- **Don't introduce new patterns or styles**
- **Preserve existing functionality**

## Remote Agent Success Criteria Template

```markdown
## Success Criteria:
- [ ] Actual codebase analyzed and understood
- [ ] Root cause identified for each error
- [ ] Minimal fixes applied matching existing patterns  
- [ ] Each fix validated individually before proceeding
- [ ] No new errors introduced during fixing process
- [ ] `make lint && make validate && make test` all pass
- [ ] Existing healthcare compliance patterns preserved
```

## Healthcare-Specific Requirements

### Security Pattern Preservation
- **PHI protection mechanisms must remain intact**
- **Audit logging functionality must be preserved**
- **Generic error messages must be maintained**
- **No sensitive data exposure in any changes**

### Compliance Validation
- **HIPAA compliance patterns must be preserved**
- **Security middleware must remain functional**
- **Healthcare-specific logging must be maintained**

## Why These Rules Matter

### The Cascade Effect
1. **Specific code in prompts** → Formatting errors
2. **Formatting errors** → Import resolution failures  
3. **Import failures** → Method signature mismatches
4. **Signature mismatches** → Runtime errors
5. **Runtime errors** → Broken healthcare functionality

### The Analysis-First Solution
1. **Understand actual codebase** → Correct fixes
2. **Match existing patterns** → No formatting conflicts
3. **Incremental validation** → Catch errors immediately
4. **Preserve working code** → Maintain healthcare compliance

## Enforcement

**These rules are CRITICAL for healthcare AI system stability.**

Any remote agent prompt that violates these guidelines will:
- Introduce cascading errors
- Break existing healthcare functionality
- Compromise PHI protection
- Violate HIPAA compliance patterns

**Always follow the analysis-first, validation-driven methodology.**