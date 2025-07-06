# Code Citation Policy

## Overview

This project follows industry-standard practices for code attribution while recognizing that generic, functional code patterns do not constitute copyrightable expression.

## What Requires Attribution

✅ **Substantial creative code** - Complex algorithms, unique implementations, creative solutions
✅ **Significant code blocks** - Functions, classes, or modules with creative expression
✅ **Novel approaches** - Innovative or non-obvious solutions to specific problems

## What Does NOT Require Attribution

❌ **Generic shell commands** - Basic system operations any developer would write identically
❌ **Standard Docker patterns** - Common Dockerfile instructions and package installations
❌ **Functional code snippets** - Simple, utilitarian code with no creative expression
❌ **Industry-standard configurations** - Common configuration patterns and boilerplate

## Examples of Non-Copyrightable Patterns

### Docker/Shell Commands
```bash
RUN apt-get update && apt-get install -y package-name
RUN git clone https://github.com/user/repo.git
mkdir -p /some/directory
cd /path/to/directory
```

### Standard Configuration
```yaml
version: '3.8'
services:
  app:
    restart: unless-stopped
    ports:
      - "80:80"
```

### Basic Shell Scripts
```bash
#!/usr/bin/env bash
set -euo pipefail
if [[ -z "$VAR" ]]; then
    echo "Variable not set"
    exit 1
fi
```

## Legal Rationale

These patterns are excluded from attribution requirements because they:

1. **Lack sufficient creativity** for copyright protection
2. **Are purely functional** with no expressive elements
3. **Would be written identically** by any competent developer
4. **Represent standard industry practices**

## False Positive Handling

If automated tools flag generic patterns as requiring attribution:

1. **Evaluate the creativity** - Does the code show unique expression?
2. **Consider alternatives** - Could it be written differently with same function?
3. **Document the decision** - Record why attribution was deemed unnecessary
4. **Update ignore patterns** - Add to `.copilotignore` if appropriate

## When in Doubt

If uncertain about whether code requires attribution:
- **Err on the side of attribution** for substantial code blocks
- **Document the source** for reference and transparency
- **Focus on creative expression** rather than functional necessity

---

*This policy ensures proper attribution for genuine creative work while avoiding unnecessary citations for standard development practices.*
