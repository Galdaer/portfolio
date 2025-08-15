---
mode: agent
---
# Session Transition & Knowledge Preservation Request

I need you to perform a comprehensive session transition to preserve our progress and prepare for the next development session. This is critical for maintaining continuity in our healthcare AI system development.

## Task 1: Update Instruction Files in .github/

### Review and Update Existing Instructions
Please analyze our conversation and update the relevant instruction files in `.github/instructions/` based on what we've learned and decided:

1. **Task-Specific Instructions** (`tasks/*.instructions.md`): 
   - Update any task patterns we've refined (debugging, testing, refactoring, etc.)
   - Add new healthcare-specific patterns we've discovered
   - Remove outdated approaches that we've replaced

2. **Language-Specific Instructions** (`languages/*.instructions.md`):
   - Capture any Python/JavaScript patterns we've established
   - Update type safety requirements based on issues we've encountered
   - Add new tooling configurations (Ruff, MyPy settings) we've decided on

3. **Domain-Specific Instructions** (`domains/healthcare.instructions.md`):
   - Update PHI handling patterns based on compliance issues we've addressed
   - Add new medical data processing patterns we've implemented
   - Document any healthcare workflow optimizations we've discovered

4. **Agent-Specific Instructions** (`agents/*.instructions.md`):
   - Create new agent instruction files for any agents we've worked on
   - Update existing agent patterns with improvements we've made
   - Document inter-agent communication patterns we've established

### Key Requirements for Instruction Updates:
- **Preserve working patterns**: Keep guidance that's proven effective
- **Remove conflicts**: Delete any contradictory information between files
- **Focus on patterns, not implementation**: Document the "how" and "why", not full code
- **Maintain healthcare focus**: Ensure all updates consider HIPAA compliance and patient safety
- **Add discovered gotchas**: Include any critical bugs or issues we've solved

## Task 2: Update own tasks

Create/edit any tasks in .vscode/tasks.json that will help agents to work more autonomously while still requiring a human in the loop to make the final decision to keep or undo the changes.


## Task 3: Create Comprehensive Handoff Document

Create a new session handoff document following this structure:

### Handoff Document Structure:
```markdown
# Healthcare AI System - Session Handoff Document
**Date:** [Current Date]
**Context:** [Brief description of session focus]
**Repository:** [repo name] (branch: [current branch])

## 🎯 SESSION OBJECTIVES & OUTCOMES
### What We Set Out to Accomplish:
- [Original goals]

### What We Actually Achieved:
- ✅ [Completed items with specific details]
- ⚠️ [Partially completed items with remaining work]
- ❌ [Blocked or deferred items with reasons]

## 💡 KEY DISCOVERIES & DECISIONS
### Technical Breakthroughs:
- **[Discovery Name]**: [What we learned and why it matters]
  - Problem it solves: [specific issue]
  - Implementation pattern: [brief pattern description]
  - Files affected: [list key files]

### Architecture Decisions:
- **[Decision]**: [Rationale and impact on system]

## 🔧 CRITICAL IMPLEMENTATION DETAILS
### Working Solutions (DON'T BREAK THESE!):
- **[Feature/Fix Name]**:
  - Location: [file:line_numbers]
  - Pattern: [brief code pattern or approach]
  - Why it works: [technical explanation]

### Known Issues & Workarounds:
- **[Issue]**: [Description]
  - Temporary fix: [current workaround]
  - Proper solution: [what needs to be done]

## 📋 UPDATED PHASE ALIGNMENT
### Phase 1 (Current) Status:
- [Component]: [% complete] - [specific status]

### Phase 2 Preparation:
- [What's ready for Phase 2]
- [What Phase 2 will need from Phase 1]

### Phase 3 Considerations:
- [Long-term implications of current work]

## 🚀 NEXT SESSION PRIORITIES
### Immediate (Must Do):
1. [Critical task with specific acceptance criteria]

### Important (Should Do):
2. [Important task with context]

### Nice to Have (Could Do):
3. [Enhancement if time permits]

## ⚠️ CRITICAL WARNINGS
### DO NOT CHANGE:
- [Stable component/pattern that works - explain why it shouldn't be touched]

### BE CAREFUL WITH:
- [Fragile area that needs careful handling - explain the risks]

### DEPENDENCIES TO MAINTAIN:
- [Critical service/tool versions or configurations]

## 🔄 ENVIRONMENT & CONFIGURATION STATE
### Current Configuration:
- Development mode: [settings]
- Key environment variables: [critical ones]
- Service dependencies: [what must be running]

### Required Tools/Services:
- [Tool]: [version] - [why needed]

## 📝 CONTEXT FOR NEXT AGENT
### Where We Left Off:
[Specific description of current state]

### Recommended Starting Point:
[Exact file/function to begin with]

### Success Criteria for Next Session:
[How to know if the next session is successful]

Task 4: Consistency Check
After creating the updates and handoff document:
Cross-reference all changes: Ensure instruction updates align with handoff document
Verify no contradictions: Check that all guidance is consistent across files
Validate healthcare compliance: Confirm all patterns maintain HIPAA compliance
Test instruction clarity: Ensure another developer could follow the guidance
Important Notes:
Focus on preserving hard-won knowledge from debugging sessions
Document patterns that save time, not obvious implementations
Include specific file paths and line numbers for critical code sections
Emphasize healthcare-specific considerations in all documentation
Make the handoff document self-contained enough that someone new could continue the work
Please proceed with these three tasks, ensuring that all learning from our session is properly preserved and the next session can start productively without losing context 

