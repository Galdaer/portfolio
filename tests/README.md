# Test Organization and Structure

This directory contains the organized test suite for the Intelluxe AI healthcare system.

## Directory Structure

```
tests/
├── README.md                    # This file - test documentation
├── conftest.py                  # Shared pytest fixtures
├── agents/                      # Agent-specific tests
├── core/                        # Core system tests
├── downloads/                   # Download script and data processing tests  
├── healthcare_evaluation/       # AI evaluation and healthcare-specific tests
├── security/                    # Security, PHI, and compliance tests
└── *.py                        # Main integration and e2e tests
```

### Test Categories

#### Unit Tests
- **Location**: Throughout the directory structure
- **Purpose**: Fast, isolated tests of individual components
- **Markers**: Use `@pytest.mark.unit` or no marker (default)
- **Run with**: `make test-unit`

#### Integration Tests  
- **Location**: Root test files and service-specific directories
- **Purpose**: Test component interactions and cross-system functionality
- **Markers**: Use `@pytest.mark.integration`
- **Run with**: `make test-integration`

#### End-to-End Tests
- **Location**: `test_e2e_*.py` files
- **Purpose**: Complete workflow testing from user input to output
- **Markers**: Use `@pytest.mark.e2e`
- **Run with**: Standard `make test` (included in main suite)

#### Service Tests
- **Location**: `services/user/*/tests/` directories
- **Purpose**: Service-specific functionality testing
- **Run with**: `make test-services`

#### Download Tests
- **Location**: `tests/downloads/`
- **Purpose**: Test data download, parsing, and processing scripts
- **Run with**: `make test-downloads`

## Make Commands

### Primary Commands
- `make test`: Run main test suite (tests/ directory)
- `make test-all`: Run ALL tests across entire repository
- `make test-quiet`: Run tests in quiet mode
- `make test-coverage`: Run with coverage reporting

### Specialized Commands  
- `make test-unit`: Fast unit tests only
- `make test-integration`: Cross-component integration tests
- `make test-services`: Service-specific tests
- `make test-downloads`: Download and data processing tests
- `make test-ai`: Healthcare AI evaluation tests

## Test Organization Guidelines

### Where to Put New Tests

1. **Agent Tests** → `tests/agents/`
   - Agent-specific functionality
   - Agent routing and coordination
   - Medical search, transcription, etc.

2. **Core System Tests** → `tests/core/`
   - Database operations
   - Configuration management
   - Utility functions

3. **Security Tests** → `tests/security/`
   - PHI detection and redaction
   - Encryption and compliance
   - Environment detection

4. **Download Tests** → `tests/downloads/`
   - Data source integration
   - Download script validation
   - Parser functionality

5. **Service Tests** → `services/user/SERVICE_NAME/tests/`
   - Keep service-specific tests with their services
   - Healthcare API, Medical Mirrors, etc.

6. **Integration Tests** → `tests/` (root level)
   - Cross-service workflows
   - End-to-end user journeys
   - Infrastructure integration

### Test Naming Conventions

- **Files**: `test_*.py` or `*_test.py`
- **Functions**: `test_function_name()` or `test_class_method()`
- **Classes**: `TestClassName`
- **Markers**: `@pytest.mark.{unit|integration|e2e|slow}`

### Best Practices

1. **Keep related tests together** - organize by functionality, not by type
2. **Use descriptive names** - test names should explain what is being tested
3. **Add appropriate markers** - helps with selective test running
4. **Include docstrings** - explain complex test scenarios
5. **Use fixtures** - share setup code via conftest.py
6. **Test both success and failure cases** - comprehensive coverage

## Cleanup Summary

The following changes were made to organize the test suite:

### Removed Files
- Redundant FDA test files (`test_fda_*.py` duplicates)
- Multiple medical database test files
- Empty test files (`test_fda_parser_validation.py`)

### Moved Files
- `final_fda_success_test.py` → `tests/downloads/test_fda_success.py`
- `test_comprehensive_exercise_download.py` → `tests/downloads/`
- `test_comprehensive_food_download.py` → `tests/downloads/`
- `test_secure_db.py` → `tests/security/`

### Download Script Consolidation
- Replaced `smart_drug_download.py` with enhanced version
- `smart_fda_download.py` now symlinks to main drug downloader
- Removed duplicate and legacy download scripts

## Running Tests

```bash
# Run all tests across entire repository
make test-all

# Run only main test suite
make test

# Run specific test categories
make test-unit
make test-integration  
make test-services
make test-downloads

# Run with coverage
make test-coverage

# Quiet mode
make test-quiet
```

This organization provides clear separation of concerns while maintaining the ability to run comprehensive test suites across the entire healthcare AI system.