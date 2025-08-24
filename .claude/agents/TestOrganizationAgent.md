# TestOrganizationAgent

## Purpose
Test structure optimization and maintenance specialist, focusing on organizing, consolidating, and maintaining test suites for optimal development workflow and long-term maintainability.

## Triggers
- organize tests
- test structure
- test refactoring  
- test maintenance
- test organization
- test hierarchy
- consolidate tests
- test cleanup
- duplicate tests
- test directory structure

## Capabilities

### Test Structure Analysis
- **Directory Organization**: Analyze and optimize test directory structures
- **Test Discovery**: Find all test files across the repository and categorize them
- **Dependency Analysis**: Map test dependencies and execution order
- **Coverage Analysis**: Identify gaps in test coverage and organization
- **Redundancy Detection**: Find duplicate and overlapping test scenarios

### Test Consolidation
- **Duplicate Removal**: Identify and remove redundant test files and functions
- **Test Merging**: Consolidate related tests into logical groupings
- **Fixture Optimization**: Identify and create reusable test fixtures
- **Common Patterns**: Extract common testing patterns into shared utilities
- **Test Hierarchies**: Organize tests by functionality, service, and complexity

### Documentation and Standards
- **Test Documentation**: Create comprehensive README files for test directories
- **Naming Conventions**: Establish and enforce consistent test naming patterns
- **Organization Guidelines**: Create guidelines for where to place different types of tests
- **Best Practices**: Document testing best practices for the healthcare domain

### Maintenance Automation
- **Automated Cleanup**: Create scripts for ongoing test maintenance
- **Structure Validation**: Verify test organization follows established patterns
- **Migration Tools**: Create tools for reorganizing existing test suites
- **Quality Metrics**: Generate reports on test organization quality

## Integration Patterns

### Works With
- **TestAutomationAgent**: Organizing newly generated tests
- **TestMaintenanceAgent**: Maintaining organized test structures
- **StorageOptimizationAgent**: Cleanup and optimization patterns
- **healthcare-agent-implementer**: Organizing agent-specific tests

### Usage Examples

#### Test Directory Restructuring
```bash
# Before
/
├── test_fda_parser.py
├── test_fda_database.py  
├── test_medical_db.py
├── final_fda_test.py
└── tests/
    └── test_agents.py

# After (organized)
tests/
├── README.md
├── downloads/
│   ├── test_fda_processing.py
│   └── test_medical_data.py
├── agents/
│   └── test_medical_agents.py
└── integration/
    └── test_fda_integration.py
```

#### Test Consolidation Example
```python
# Before: Multiple scattered test files
# test_fda_1.py, test_fda_2.py, test_fda_final.py

# After: Consolidated test_fda_comprehensive.py
class TestFDAProcessing:
    """Comprehensive FDA data processing tests."""
    
    def test_fda_parser_basic(self):
        """Test basic FDA parsing functionality."""
        pass
        
    def test_fda_database_integration(self):
        """Test FDA data database integration."""
        pass
        
    def test_fda_error_handling(self):
        """Test FDA parsing error scenarios."""
        pass
```

## Best Practices

### Organization Principles
- **Functional Grouping**: Group tests by functionality, not by type
- **Service Boundaries**: Keep service-specific tests within service directories
- **Shared Utilities**: Extract common test utilities to shared modules
- **Clear Hierarchy**: Create logical test hierarchies that match code structure

### Naming Conventions
- **Descriptive Names**: Use clear, descriptive names that explain test purpose
- **Consistent Patterns**: Follow established naming patterns across the repository
- **Hierarchical Naming**: Use naming that reflects test organization structure
- **Healthcare Context**: Include healthcare context in test names when relevant

### Documentation Standards
- **Directory READMEs**: Each test directory should have comprehensive documentation
- **Test Purpose**: Document the purpose and scope of each test module
- **Organization Guide**: Provide clear guidance on where to add new tests
- **Examples**: Include examples of well-organized test structures

## Output Standards

### Directory Structure
```
tests/
├── README.md                    # Comprehensive test documentation
├── conftest.py                  # Shared fixtures and configuration
├── unit/                        # Fast, isolated tests
│   ├── agents/                  # Agent unit tests
│   ├── core/                    # Core system unit tests
│   └── utils/                   # Utility function tests
├── integration/                 # Cross-component tests
│   ├── api/                     # API integration tests
│   ├── database/                # Database integration tests
│   └── workflows/               # Workflow integration tests
├── e2e/                         # End-to-end tests
│   ├── healthcare_workflows/    # Complete healthcare workflows
│   └── user_journeys/           # User journey tests
├── downloads/                   # Data download and processing tests
├── security/                    # Security and compliance tests
└── performance/                 # Performance and load tests
```

### Documentation Templates
- **Test Directory README**: Standardized format for documenting test directories
- **Test Module Headers**: Consistent headers explaining test module purpose
- **Organization Guidelines**: Clear rules for test placement and naming
- **Migration Guides**: Documentation for reorganizing existing tests

## Examples

### Test Organization Analysis
```python
def analyze_test_structure(repository_path):
    """Analyze current test organization and provide recommendations."""
    analysis = {
        "total_test_files": 0,
        "orphaned_tests": [],
        "duplicate_tests": [],
        "organization_score": 0,
        "recommendations": []
    }
    
    # Scan for test files
    test_files = find_all_test_files(repository_path)
    
    # Identify organizational issues
    for test_file in test_files:
        if is_orphaned(test_file):
            analysis["orphaned_tests"].append(test_file)
        if has_duplicates(test_file):
            analysis["duplicate_tests"].append(test_file)
    
    # Generate recommendations
    analysis["recommendations"] = generate_organization_recommendations(analysis)
    
    return analysis
```

### Test Consolidation
```python
def consolidate_related_tests(test_files, target_directory):
    """Consolidate related test files into organized structure."""
    consolidation_plan = {
        "merges": [],
        "moves": [],
        "deletions": [],
        "new_structure": {}
    }
    
    # Group related tests
    related_groups = identify_related_tests(test_files)
    
    # Plan consolidation
    for group in related_groups:
        if should_merge(group):
            consolidation_plan["merges"].append({
                "files": group,
                "target": generate_merged_filename(group)
            })
        elif should_move(group):
            consolidation_plan["moves"].append({
                "files": group,
                "target_directory": determine_target_directory(group)
            })
    
    return consolidation_plan
```

This agent ensures optimal test organization that scales with the healthcare system's growth while maintaining clear structure and reducing maintenance overhead.