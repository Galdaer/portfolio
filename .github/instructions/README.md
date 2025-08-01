# AI Instructions Directory

This directory contains specialized AI instruction files for different development contexts, tasks, and tools. These files are **officially supported by GitHub Copilot coding agent** and enable enhanced AI assistance across the healthcare AI development workflow.

## When to Use Which Instructions

### 🔧 **Main Copilot Instructions** (`.github/copilot-instructions.md`)

**Use for**: General project guidance, architecture decisions, healthcare principles

- Project overview and core architecture
- Healthcare security and compliance principles
- Service architecture patterns
- Development workflow overview
- Synthetic data infrastructure overview

### 📂 **Specialized Instructions** (`.github/instructions/**/*.instructions.md`)

**Use for**: Task-specific or technology-specific development work

#### Task-Specific Instructions

- **`tasks/debugging.instructions.md`** → When debugging healthcare code, fixing errors, troubleshooting
- **`tasks/code-review.instructions.md`** → When reviewing code, validating compliance, checking quality
- **`tasks/testing.instructions.md`** → When writing tests, validating functionality, using synthetic data
- **`tasks/refactoring.instructions.md`** → When refactoring code, improving architecture, modernizing
- **`tasks/documentation.instructions.md`** → When writing docs, creating README files, documenting APIs
- **`tasks/planning.instructions.md`** → When planning features, designing architecture, making decisions

#### Language-Specific Instructions

- **`languages/python.instructions.md`** → When working with Python files (.py), type safety, modern tooling

#### Domain-Specific Instructions

- **`healthcare.instructions.md`** → When working with medical data, PHI, compliance, patient records

## Official GitHub Copilot Support

According to GitHub's documentation: _"You can add instructions in a single `.github/copilot-instructions.md` file in the repository, or create one or more `.github/instructions/\*\*/_.instructions.md` files applying to different files or directories in your repository."\*

This means:

- ✅ **GitHub Copilot coding agent** automatically reads and applies these specialized instructions
- ✅ **Context-specific guidance** is provided based on the files you're working on
- ✅ **Task-specific assistance** is available for debugging, code reviews, and language-specific development
- ✅ **Healthcare domain expertise** is integrated into all AI interactions

## Usage Examples

### ✅ **When to Reference Specialized Instructions**

```bash
# Python type safety issues → Use python.instructions.md
"Fix the MyPy errors in core/medical/patient_data.py"

# Healthcare compliance review → Use healthcare.instructions.md + code-review.instructions.md
"Review this patient processing code for HIPAA compliance"

# Test failures with synthetic data → Use testing.instructions.md
"Debug why the synthetic patient data tests are failing"

# Complex debugging session → Use debugging.instructions.md + healthcare.instructions.md
"Debug the PHI exposure risk in the agent session logs"
```

### 🚫 **When to Stay with Main Instructions**

```bash
# Architecture decisions → Use main copilot-instructions.md
"Should we add a new service for insurance verification?"

# General project questions → Use main copilot-instructions.md
"What's our overall approach to healthcare AI safety?"

# Service deployment issues → Use main copilot-instructions.md
"How do I deploy the universal service runner?"
```

## Directory Structure

```
.github/instructions/
├── tasks/              # Task-specific AI instructions
│   ├── debugging.instructions.md
│   └── code-review.instructions.md
├── languages/          # Programming language patterns
│   └── python.instructions.md
└── domains/            # Domain-specific guidance
    └── healthcare.instructions.md
```

## How This Enhances Your AI Development

### Automatic Context Application

When you're working on healthcare Python code and ask for debugging help, GitHub Copilot will automatically reference:

1. **Healthcare domain requirements** (PHI protection, medical safety)
2. **Python-specific patterns** (Ruff, MyPy, modern Python practices)
3. **Debugging best practices** (healthcare-safe debugging, compliance patterns)

### Specialized AI Assistance

- **Debugging healthcare code**: Follows PHI-safe debugging patterns automatically
- **Code reviews**: Applies healthcare compliance checking and modern Python standards
- **Python development**: Uses healthcare-specific type safety and modern tooling patterns
- **Healthcare domain**: Ensures medical safety and compliance in all AI suggestions

## Usage Patterns

### For GitHub Copilot Coding Agent

When you assign tasks to @copilot, it will automatically apply these specialized instructions:

```
@copilot Fix the debugging issue in agents/document_processor/main.py
# Automatically applies: healthcare domain + Python language + debugging task instructions
```

### For Development Teams

Reference specific instruction files for focused guidance:

- **Healthcare compliance**: Follow patterns in `domains/healthcare.instructions.md`
- **Python modernization**: Apply guidance from `languages/python.instructions.md`
- **Safe debugging**: Use instructions from `tasks/debugging.instructions.md`

### For Custom Tools and Extensions

These instruction files can be programmatically read by:

- Custom VS Code extensions
- Healthcare development scripts
- Automated compliance checking tools
- Team onboarding and training systems

## Integration with Existing System

These specialized instructions **complement** rather than replace:

- `.github/copilot-instructions.md` - Primary instructions for GitHub Copilot
- `agents/*/ai-instructions.md` - Agent-specific implementation guidance
- Healthcare compliance and security documentation

## Modern Development Tools Integration

Each instruction file integrates modern development tools:

- **Ruff**: Ultra-fast Python linting and formatting (10-100x faster than traditional tools)
- **Pre-commit hooks**: Multi-language validation with healthcare compliance
- **MyPy**: Comprehensive type checking for healthcare data safety
- **Healthcare-specific patterns**: PHI protection, medical safety, audit logging

## Future-Proofing Benefits

This structured approach provides:

- ✅ **Enhanced AI accuracy** through context-specific guidance
- ✅ **Consistent healthcare compliance** across all AI interactions
- ✅ **Modern development practices** automatically applied
- ✅ **Team knowledge sharing** through documented patterns
- ✅ **Scalable AI assistance** as the healthcare system grows
