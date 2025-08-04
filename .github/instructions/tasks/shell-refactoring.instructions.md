# Shell Function Refactoring Instructions

## Function Single Responsibility Pattern

**When reviewing shell functions, apply the extraction pattern used in `bootstrap.sh` environment validation:**

### Refactoring Triggers
Functions that should be candidates for extraction:
- **>20 lines of code**
- **Multiple nested if/elif blocks with different purposes**
- **Mixed concerns** (e.g., detection + validation, setup + execution)
- **Multiple logical sections** separated by blank lines or comments
- **Functions with multiple exit points** for different reasons

### Extraction Pattern

**❌ BEFORE: Mixed concerns in one function**
```bash
validate_and_setup_service() {
    # Auto-detect service type
    if [[ -f "docker-compose.yml" ]]; then
        service_type="docker"
    elif [[ -f "systemd.service" ]]; then
        service_type="systemd"
    else
        service_type="manual"
    fi
    
    # Validate service type
    case "$service_type" in
        docker|systemd|manual) echo "Valid service type" ;;
        *) echo "ERROR: Invalid service type"; exit 1 ;;
    esac
    
    # Setup service
    setup_directories
    configure_permissions
}
```

**✅ AFTER: Separated concerns**
```bash
detect_service_type() {
    local detected_type=""
    
    if [[ -f "docker-compose.yml" ]]; then
        detected_type="docker"
    elif [[ -f "systemd.service" ]]; then
        detected_type="systemd"
    else
        detected_type="manual"
    fi
    
    echo "$detected_type"
}

validate_service_type() {
    local service_type="${1:-$(detect_service_type)}"
    
    case "$service_type" in
        docker|systemd|manual) 
            echo "✅ Valid service type: $service_type" 
            ;;
        *) 
            echo "ERROR: Invalid service type: $service_type"
            exit 1 
            ;;
    esac
}

setup_service() {
    validate_service_type
    setup_directories
    configure_permissions
}
```

### Healthcare Compliance Benefits

1. **Auditable Logic**: Each function has one clear responsibility
2. **Testable Components**: Individual functions can be unit tested
3. **Maintainable Code**: Easier to understand and modify
4. **Error Isolation**: Problems are contained to specific functions

### Implementation Checklist

When refactoring shell functions:
- [ ] Each function has one clear purpose
- [ ] Detection logic is separate from validation logic
- [ ] Setup/configuration is separate from execution
- [ ] Functions are <20 lines where possible
- [ ] Function names clearly indicate their single responsibility
- [ ] No mixed echo output and return values in the same function

### AI/Copilot Detection Pattern

**Prompt for systematic detection:**
```
Review shell functions for single responsibility violations:
1. Functions >20 lines with multiple logical sections
2. Functions mixing detection + validation logic
3. Functions with multiple purposes (setup + execution)
4. Extract detection logic into separate functions
5. Keep validation/setup functions focused on their specific task
```

### Testing Pattern

```bash
# Test detection function independently
test_detect_service_type() {
    # Setup test environment
    touch docker-compose.yml
    
    # Test detection
    result=$(detect_service_type)
    [[ "$result" == "docker" ]] || fail "Expected 'docker', got '$result'"
    
    # Cleanup
    rm docker-compose.yml
}

# Test validation function independently  
test_validate_service_type() {
    # Test valid types
    validate_service_type "docker" || fail "Should accept 'docker'"
    
    # Test invalid types
    ! validate_service_type "invalid" || fail "Should reject 'invalid'"
}
```

This pattern ensures healthcare-compliant, maintainable shell code with clear separation of concerns.
