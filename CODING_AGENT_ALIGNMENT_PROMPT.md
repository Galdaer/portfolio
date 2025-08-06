# GitHub Coding Agent: Intelluxe AI Healthcare System Compliance Alignment

**MISSION**: Systematically align the entire Intelluxe AI healthcare codebase with latest privacy-first, database-first, offline-capable standards. Focus on **refactoring and compliance alignment** - do NOT add new features.

## **CRITICAL COMPLIANCE REQUIREMENTS**

### **DATABASE-FIRST ARCHITECTURE (Priority 1)**
- **ELIMINATE ALL** synthetic file fallbacks except for GitHub coding agent database setup
- **REQUIRE** database connectivity for ALL agents, scripts, core infrastructure
- **ADD** proper error handling with clear guidance when database unavailable
- **PATTERN**: Database connection required → Clear error message → Setup guidance

### **OFFLINE-FIRST CAPABILITIES (Priority 2)**  
- **UPDATE** MCP servers to support local mirror operation
- **ADD** offline mode configuration and fallback logic
- **IMPLEMENT** local website mirroring infrastructure where referenced
- **ENSURE** all services can function without internet when configured for offline mode

### **ENHANCED SYNTHETIC DATA (Priority 3)**
- **UPDATE** all synthetic data generators to create PHI-like realistic patterns
- **ENSURE** synthetic data triggers PHI detectors for proper testing
- **MAINTAIN** clear synthetic markers on all generated data
- **VALIDATE** PHI detection effectiveness with realistic synthetic patterns

### **ADVANCED INSURANCE CALCULATIONS (Priority 4)**
- **REFACTOR** insurance logic for percentage copays, not just fixed dollar amounts
- **ADD** deductible proximity tracking and remaining balance calculations  
- **IMPLEMENT** exact visit cost prediction capabilities
- **SUPPORT** complex insurance structures (HSA, family vs individual, etc.)

## **INSTRUCTION SOURCES TO FOLLOW**

Apply ALL patterns and requirements from:

1. **Primary Instructions**:
   - `.github/copilot-instructions.md` (main healthcare AI guidance)
   - `TODO.md` (priority requirements and implementation order)

2. **Specialized Instruction Files** (56+ files in `.github/instructions/`):
   - `tasks/database-development.instructions.md` ✅ (updated with database-first)
   - `data/healthcare-data-pipelines.instructions.md` ✅ (updated with PHI-like synthetic)
   - `domains/insurance-calculations.instructions.md` ✅ (NEW - advanced insurance)
   - `mcp-development.instructions.md` ✅ (updated with offline capabilities)
   - ALL other existing instruction files in tasks/, domains/, languages/, workflows/, patterns/, etc.

3. **Directory-Specific Instructions**:
   - `core/ai-instructions.md` ✅ (NEW - infrastructure with database-first)
   - `scripts/ai-instructions.md` ✅ (updated with database-first + enhanced synthetic data)
   - `config/ai-instructions.md` ✅ (NEW - configuration management)
   - `agents/*/ai-instructions.md` (6 agent files - updated to remove fallbacks)

## **SYSTEMATIC ALIGNMENT TASKS**

### **Phase 1: Database-First Enforcement**
1. **Scan entire codebase** for synthetic file fallback patterns
2. **Remove fallback logic** except in GitHub coding agent setup scripts
3. **Add database connectivity checks** to all agents, scripts, core services
4. **Standardize error messages** with setup guidance
5. **Update all tests** to require database connections

### **Phase 2: Agent Compliance Alignment**
1. **Update all 6 agents** (`agents/intake/`, `agents/document_processor/`, `agents/billing_helper/`, etc.)
2. **Remove duplicate healthcare compliance code** (it's now centralized)
3. **Ensure database-first patterns** in all agent initialization
4. **Apply agent-specific instruction requirements**

### **Phase 3: Infrastructure & Scripts Alignment**
1. **Update core infrastructure** (`core/infrastructure/`) to follow `core/ai-instructions.md`
2. **Update all scripts** (`scripts/`) to follow `scripts/ai-instructions.md`
3. **Update configuration management** (`config/`) to follow `config/ai-instructions.md`
4. **Ensure offline capabilities** in MCP and related systems

### **Phase 4: Enhanced Data & Insurance**
1. **Update synthetic data generators** to create PHI-like realistic patterns
2. **Refactor insurance calculation logic** for advanced features (percentage copays, deductible tracking)
3. **Add cost prediction capabilities** where insurance processing exists
4. **Ensure PHI detection testing** with enhanced synthetic data

### **Phase 5: Testing & Documentation Alignment**
1. **Update all tests** to database-first patterns
2. **Remove synthetic file test dependencies**  
3. **Update docstrings and comments** to match new compliance standards
4. **Ensure medical disclaimers** are consistent across codebase

## **STRICT RULES**

### **✅ DO:**
- Refactor existing code to match instruction patterns
- Remove code that violates new standards  
- Update error handling and logging patterns
- Standardize healthcare compliance implementation
- Add database connectivity requirements
- Apply privacy-first patterns throughout

### **❌ DO NOT:**
- Add new business features or functionality
- Create new agents or major components
- Change core business logic beyond compliance alignment
- Remove functional code unless it violates compliance
- Add external dependencies not already planned

## **DECISION FRAMEWORK**

When facing ambiguous situations, prioritize in this order:
1. **Privacy and HIPAA compliance** (most important)
2. **Database-first architecture** 
3. **Offline-capable operation**
4. **Comprehensive audit logging**
5. **User experience and clear error messages**

## **SUCCESS CRITERIA**

**Complete when:**
- Zero synthetic file fallbacks (except GitHub agent setup)
- All agents/scripts require database connectivity with proper errors
- All instruction patterns implemented consistently
- Enhanced synthetic data generates PHI-like test patterns
- Advanced insurance calculations support complex scenarios
- All tests run database-first
- Codebase fully aligned with all 60+ instruction files

## **EXECUTION APPROACH**

**Keep iterating and refactoring until the entire codebase is fully compliant and aligned.** Review each file systematically against the relevant instructions. This is a comprehensive alignment task - continue until completion.

**After completion**: A new TODO.md will be created based on docs/PHASE_*.md for future feature additions.
