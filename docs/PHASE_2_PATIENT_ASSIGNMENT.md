# Phase 2: Patient Assignment System

## Overview
Implement proper patient-provider assignment system for healthcare access control in the Intelluxe AI platform.

## Current Status (Phase 1)
- ✅ **RBAC Foundation**: Complete role-based access control framework
- ✅ **Environment Detection**: Secure environment-aware configuration
- ✅ **Placeholder Implementation**: Configurable patient access for development
- ✅ **Security Framework**: Comprehensive audit logging and PHI protection

## Phase 2 Features to Implement

### 1. Patient Assignment Database Schema

```sql
-- Patient-Provider Assignments
CREATE TABLE patient_assignments (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    assignment_type VARCHAR(20) NOT NULL, -- 'primary', 'consulting', 'emergency'
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT unique_primary_assignment 
        UNIQUE (patient_id, assignment_type, start_date) 
        WHERE assignment_type = 'primary' AND end_date IS NULL
);

-- Care Teams
CREATE TABLE care_teams (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    team_type VARCHAR(50) NOT NULL, -- 'primary', 'specialty', 'emergency'
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Care Team Members
CREATE TABLE care_team_members (
    id SERIAL PRIMARY KEY,
    care_team_id INTEGER REFERENCES care_teams(id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'attending', 'resident', 'nurse', 'specialist'
    permissions JSONB DEFAULT '{}', -- Role-specific permissions
    added_at TIMESTAMP DEFAULT NOW(),
    removed_at TIMESTAMP,
    
    CONSTRAINT unique_active_member 
        UNIQUE (care_team_id, provider_id) 
        WHERE removed_at IS NULL
);

-- Emergency Access Log
CREATE TABLE emergency_access_log (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(50) NOT NULL,
    patient_id VARCHAR(50) NOT NULL,
    access_reason TEXT NOT NULL,
    supervisor_id VARCHAR(50),
    approved_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_emergency_access_active (provider_id, patient_id, expires_at)
);
```

### 2. Patient Assignment Service

```python
class PatientAssignmentService:
    """Service for managing patient-provider assignments"""
    
    def __init__(self, connection_factory: ConnectionFactory):
        self.connection_factory = connection_factory
        self.logger = logging.getLogger(f"{__name__}.PatientAssignmentService")
    
    async def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
        """Check if user is assigned to patient through any mechanism"""
        
        # Check direct assignments
        if await self._check_direct_assignment(user_id, patient_id):
            return True
        
        # Check care team membership
        if await self._check_care_team_membership(user_id, patient_id):
            return True
        
        # Check emergency access
        if await self._check_emergency_access(user_id, patient_id):
            return True
        
        return False
    
    async def _check_direct_assignment(self, user_id: str, patient_id: str) -> bool:
        """Check direct patient-provider assignments"""
        # Implementation details...
        pass
    
    async def _check_care_team_membership(self, user_id: str, patient_id: str) -> bool:
        """Check care team membership"""
        # Implementation details...
        pass
    
    async def _check_emergency_access(self, user_id: str, patient_id: str) -> bool:
        """Check emergency/break-glass access"""
        # Implementation details...
        pass
```

### 3. Break-Glass Emergency Access

```python
class EmergencyAccessManager:
    """Manage emergency access to patient data"""
    
    async def request_emergency_access(
        self, 
        provider_id: str, 
        patient_id: str, 
        reason: str,
        duration_hours: int = 24
    ) -> str:
        """Request emergency access to patient data"""
        
        # Validate request
        self._validate_emergency_request(provider_id, patient_id, reason)
        
        # Create emergency access record
        access_id = await self._create_emergency_access(
            provider_id, patient_id, reason, duration_hours
        )
        
        # Notify supervisors
        await self._notify_supervisors(provider_id, patient_id, reason)
        
        # Log security event
        await self._log_emergency_access(provider_id, patient_id, reason)
        
        return access_id
    
    async def approve_emergency_access(
        self, 
        access_id: str, 
        supervisor_id: str
    ) -> bool:
        """Approve emergency access request"""
        # Implementation details...
        pass
```

### 4. Assignment Validation Rules

```python
class AssignmentValidator:
    """Validate patient assignment rules and constraints"""
    
    def validate_primary_assignment(self, patient_id: str, provider_id: str) -> bool:
        """Validate primary care provider assignment"""
        # Rules:
        # - Only one primary provider per patient at a time
        # - Provider must have appropriate credentials
        # - Assignment must not conflict with existing assignments
        pass
    
    def validate_specialist_assignment(self, patient_id: str, provider_id: str, specialty: str) -> bool:
        """Validate specialist assignment"""
        # Rules:
        # - Provider must have specialty credentials
        # - Referral must exist from primary provider
        # - Assignment duration must be specified
        pass
    
    def validate_care_team_membership(self, team_id: str, provider_id: str, role: str) -> bool:
        """Validate care team membership"""
        # Rules:
        # - Provider must have appropriate role credentials
        # - Team must not exceed maximum size
        # - Role must not conflict with existing roles
        pass
```

### 5. Cross-Coverage Arrangements

```python
class CrossCoverageManager:
    """Manage cross-coverage arrangements between providers"""
    
    async def create_coverage_arrangement(
        self,
        primary_provider_id: str,
        covering_provider_id: str,
        start_date: datetime,
        end_date: datetime,
        coverage_type: str = 'full'
    ) -> str:
        """Create cross-coverage arrangement"""
        # Implementation details...
        pass
    
    async def get_covering_provider(
        self,
        primary_provider_id: str,
        date: datetime
    ) -> Optional[str]:
        """Get covering provider for a specific date"""
        # Implementation details...
        pass
```

## Implementation Plan

### Phase 2.1: Core Assignment System (4 weeks)
1. **Week 1**: Database schema and migrations
2. **Week 2**: Patient assignment service implementation
3. **Week 3**: RBAC integration and validation rules
4. **Week 4**: Testing and security validation

### Phase 2.2: Emergency Access (2 weeks)
1. **Week 1**: Break-glass access implementation
2. **Week 2**: Supervisor approval workflow

### Phase 2.3: Advanced Features (3 weeks)
1. **Week 1**: Care team management
2. **Week 2**: Cross-coverage arrangements
3. **Week 3**: Reporting and analytics

### Phase 2.4: Integration and Testing (2 weeks)
1. **Week 1**: End-to-end integration testing
2. **Week 2**: Security audit and performance optimization

## Security Considerations

### Access Control
- ✅ **Principle of Least Privilege**: Users only access assigned patients
- ✅ **Audit Logging**: All access attempts logged with full context
- ✅ **Time-based Access**: Assignments have start/end dates
- ✅ **Emergency Procedures**: Break-glass access with supervisor approval

### Data Protection
- ✅ **PHI Masking**: Sensitive data masked in logs and audit trails
- ✅ **Encryption**: All assignment data encrypted at rest and in transit
- ✅ **Access Monitoring**: Real-time monitoring of unusual access patterns
- ✅ **Compliance**: HIPAA-compliant audit trails and access controls

## Testing Strategy

### Unit Tests
- Assignment validation logic
- Emergency access workflows
- Care team management
- Cross-coverage arrangements

### Integration Tests
- RBAC system integration
- Database transaction integrity
- Audit logging completeness
- Performance under load

### Security Tests
- Unauthorized access attempts
- Privilege escalation scenarios
- Emergency access abuse prevention
- Data leakage prevention

## Migration from Phase 1

### Current Placeholder Behavior
```python
# Phase 1 (Current)
def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
    default_access = os.getenv('RBAC_DEFAULT_PATIENT_ACCESS', 'false').lower() == 'true'
    return default_access  # Configurable for development
```

### Phase 2 Implementation
```python
# Phase 2 (Target)
async def is_user_assigned_to_patient(self, user_id: str, patient_id: str) -> bool:
    return await self.assignment_service.is_user_assigned_to_patient(user_id, patient_id)
```

### Migration Steps
1. **Deploy Phase 2 code** with feature flags
2. **Migrate existing data** to new assignment tables
3. **Enable new assignment logic** gradually
4. **Remove placeholder code** after validation
5. **Update documentation** and training materials

## Success Criteria

### Functional Requirements
- ✅ **Accurate Assignment Checking**: 99.9% accuracy in assignment validation
- ✅ **Emergency Access**: Sub-5-minute emergency access approval
- ✅ **Performance**: <100ms response time for assignment checks
- ✅ **Scalability**: Support for 10,000+ concurrent users

### Security Requirements
- ✅ **Zero Unauthorized Access**: No false positives in access control
- ✅ **Complete Audit Trail**: 100% of access attempts logged
- ✅ **Emergency Monitoring**: Real-time alerts for emergency access
- ✅ **Compliance**: Pass HIPAA security audit

### Operational Requirements
- ✅ **High Availability**: 99.9% uptime for assignment service
- ✅ **Disaster Recovery**: <1 hour RTO for assignment data
- ✅ **Monitoring**: Comprehensive metrics and alerting
- ✅ **Documentation**: Complete API and operational documentation

---

**Status**: Phase 1 Complete ✅ | Phase 2 Planning Complete ✅ | Ready for Implementation 🚀
