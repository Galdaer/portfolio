# Advanced Insurance Calculations for Healthcare AI

## Purpose

Comprehensive insurance calculation patterns supporting percentage copays, deductible tracking, cost prediction, and complex coverage scenarios for accurate patient cost estimates.

## Enhanced Insurance Coverage Modeling

### Type Safety and Method Signature Consistency

**✅ CORRECT: Consistent method signatures with proper types:**
```python
from decimal import Decimal
from typing import Optional, Dict, Any

class InsuranceCoverageCalculator:
    def calculate_patient_cost(
        self, 
        cpt_code: str, 
        billed_amount: Decimal,  # Always use Decimal for money
        patient_coverage: PatientCoverage
    ) -> PatientCostResult:
        """Calculate patient cost with proper type handling"""
        pass
    
    def _ensure_decimal(self, value: Any) -> Decimal:
        """Convert various number types to Decimal safely"""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))  # Convert via string for precision
        if isinstance(value, str):
            return Decimal(value)
        raise ValueError(f"Cannot convert {type(value)} to Decimal")
```

### Edge Case Handling Patterns

**✅ CORRECT: Division by zero protection:**
```python
def _calculate_deductible_status(self, patient_coverage: PatientCoverage) -> DeductibleStatus:
    """Calculate deductible status with edge case protection"""
    if patient_coverage.annual_deductible <= 0:
        # Handle zero or negative deductible (some plans have no deductible)
        return DeductibleStatus(
            remaining=Decimal('0'),
            percentage_met=1.0,
            status="no_deductible"
        )
    
    remaining = patient_coverage.annual_deductible - patient_coverage.deductible_met
    percentage_met = float(patient_coverage.deductible_met / patient_coverage.annual_deductible)
    
    return DeductibleStatus(
        remaining=max(remaining, Decimal('0')),  # Never negative
        percentage_met=min(percentage_met, 1.0),  # Never over 100%
        status=self._determine_deductible_status(percentage_met)
    )
```

### Complex Copay Structures

**✅ CORRECT: Multi-Type Copay Support**
```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional, Union, List
from enum import Enum

class CopayType(Enum):
    FIXED_DOLLAR = "fixed_dollar"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    DEDUCTIBLE_THEN_PERCENTAGE = "deductible_then_percentage"

@dataclass
class CopayStructure:
    """Advanced copay calculation structure"""
    copay_type: CopayType
    primary_amount: Decimal  # Dollar amount or percentage
    secondary_amount: Optional[Decimal] = None  # For complex structures
    service_type: str = "general"  # office_visit, specialist, emergency, etc.
    
    # Advanced features
    max_out_of_pocket: Optional[Decimal] = None
    applies_to_deductible: bool = True
    family_vs_individual: str = "individual"

class InsuranceCoverageCalculator:
    """Advanced insurance coverage calculation engine"""
    
    def calculate_patient_cost(
        self, 
        cpt_code: str, 
        billed_amount: Decimal,
        patient_coverage: 'PatientCoverage'
    ) -> 'CostEstimate':
        """Calculate exact patient cost for a procedure"""
        
        # Step 1: Determine service category
        service_category = self.categorize_cpt_code(cpt_code)
        
        # Step 2: Check deductible status
        deductible_status = self.calculate_deductible_status(patient_coverage)
        
        # Step 3: Apply appropriate copay structure
        copay_structure = patient_coverage.get_copay_for_service(service_category)
        
        # Step 4: Calculate patient responsibility
        if deductible_status.remaining > 0:
            patient_cost = self.calculate_with_deductible(
                billed_amount, deductible_status, copay_structure
            )
        else:
            patient_cost = self.calculate_post_deductible(
                billed_amount, copay_structure
            )
        
        # Step 5: Apply out-of-pocket maximums
        final_cost = self.apply_oop_maximum(patient_cost, patient_coverage)
        
        return CostEstimate(
            total_billed=billed_amount,
            patient_responsibility=final_cost,
            insurance_payment=billed_amount - final_cost,
            deductible_applied=deductible_status.applied_amount,
            confidence_level=self.calculate_confidence(patient_coverage)
        )
```

### Deductible Proximity Tracking

**✅ CORRECT: Comprehensive Deductible Analysis**
```python
@dataclass
class DeductibleStatus:
    """Detailed deductible tracking and projection"""
    annual_deductible: Decimal
    amount_applied: Decimal
    remaining_amount: Decimal
    percentage_met: float
    projected_meet_date: Optional[datetime]
    family_vs_individual: str
    
    # Advanced tracking
    monthly_average_spending: Decimal
    historical_meet_date: Optional[datetime]
    likelihood_to_meet: float  # 0.0 to 1.0

class DeductibleTracker:
    """Advanced deductible tracking and prediction"""
    
    def calculate_deductible_proximity(
        self, 
        patient_id: str,
        coverage_period: str = "current_year"
    ) -> DeductibleStatus:
        """Calculate how close patient is to meeting deductible"""
        
        # Get historical spending data
        spending_history = self.get_patient_spending_history(patient_id)
        current_applied = self.get_current_deductible_applied(patient_id)
        
        # Calculate trends
        monthly_average = self.calculate_monthly_average(spending_history)
        projected_meet_date = self.project_deductible_meet_date(
            current_applied, monthly_average
        )
        
        # Calculate likelihood based on historical patterns
        likelihood = self.calculate_meet_likelihood(
            patient_id, current_applied, monthly_average
        )
        
        return DeductibleStatus(
            annual_deductible=coverage.annual_deductible,
            amount_applied=current_applied,
            remaining_amount=coverage.annual_deductible - current_applied,
            percentage_met=current_applied / coverage.annual_deductible,
            projected_meet_date=projected_meet_date,
            monthly_average_spending=monthly_average,
            likelihood_to_meet=likelihood
        )
    
    def generate_deductible_insights(self, status: DeductibleStatus) -> List[str]:
        """Generate patient-friendly deductible insights"""
        insights = []
        
        if status.percentage_met > 0.8:
            insights.append(
                f"You're {status.percentage_met:.0%} of the way to meeting "
                f"your annual deductible (${status.remaining_amount:.2f} remaining)"
            )
        
        if status.projected_meet_date and status.projected_meet_date < datetime.now().replace(month=12):
            insights.append(
                f"Based on your spending patterns, you're likely to meet "
                f"your deductible by {status.projected_meet_date.strftime('%B %Y')}"
            )
        
        return insights
```

### Exact Visit Cost Prediction

**✅ CORRECT: Pre-Visit Cost Estimation**
```python
@dataclass
class CostEstimate:
    """Comprehensive cost estimate for patient transparency"""
    total_billed: Decimal
    patient_responsibility: Decimal
    insurance_payment: Decimal
    deductible_applied: Decimal
    confidence_level: float
    
    # Detailed breakdown
    copay_amount: Decimal
    coinsurance_amount: Decimal
    out_of_pocket_impact: Decimal
    
    # Patient-friendly explanations
    cost_explanation: List[str]
    potential_variations: Dict[str, Decimal]  # Best/worst case scenarios

class VisitCostPredictor:
    """Predict exact costs for scheduled visits"""
    
    def predict_visit_cost(
        self,
        patient_id: str,
        provider_id: str,
        scheduled_cpt_codes: List[str],
        visit_date: datetime
    ) -> CostEstimate:
        """Predict exact cost before patient visit"""
        
        # Get patient coverage details
        coverage = self.get_patient_coverage(patient_id, visit_date)
        
        # Get provider's negotiated rates
        negotiated_rates = self.get_negotiated_rates(provider_id, scheduled_cpt_codes)
        
        # Calculate for each CPT code
        total_estimate = CostEstimate(
            total_billed=Decimal("0"),
            patient_responsibility=Decimal("0"),
            insurance_payment=Decimal("0"),
            confidence_level=1.0
        )
        
        for cpt_code in scheduled_cpt_codes:
            cpt_estimate = self.calculate_patient_cost(
                cpt_code, negotiated_rates[cpt_code], coverage
            )
            total_estimate = self.combine_estimates(total_estimate, cpt_estimate)
        
        # Add patient-friendly explanations
        total_estimate.cost_explanation = self.generate_cost_explanation(
            total_estimate, coverage
        )
        
        return total_estimate
    
    def generate_cost_explanation(
        self, 
        estimate: CostEstimate, 
        coverage: 'PatientCoverage'
    ) -> List[str]:
        """Generate patient-friendly cost explanations"""
        explanations = []
        
        if estimate.deductible_applied > 0:
            explanations.append(
                f"${estimate.deductible_applied:.2f} will be applied to your "
                f"${coverage.annual_deductible:.2f} annual deductible"
            )
        
        if estimate.copay_amount > 0:
            explanations.append(f"${estimate.copay_amount:.2f} copay")
        
        if estimate.coinsurance_amount > 0:
            coinsurance_pct = coverage.get_coinsurance_percentage()
            explanations.append(
                f"${estimate.coinsurance_amount:.2f} coinsurance "
                f"({coinsurance_pct:.0%} of allowed amount)"
            )
        
        explanations.append(
            f"Total estimated cost: ${estimate.patient_responsibility:.2f}"
        )
        
        return explanations
```

## Privacy and Compliance Considerations

### HIPAA-Compliant Cost Calculations

**✅ CRITICAL: Privacy-First Implementation**
```python
class PrivacyCompliantCostCalculator:
    """Insurance calculations with maximum privacy protection"""
    
    def __init__(self):
        self.audit_logger = get_healthcare_logger('insurance_calculations')
        self.phi_monitor = PHIMonitor()
    
    @healthcare_log_method
    @phi_monitor
    def calculate_costs(self, patient_data: Dict[str, Any]) -> CostEstimate:
        """Calculate costs with full audit trail and PHI protection"""
        
        # Log calculation request (no PHI in logs)
        self.audit_logger.info(
            "Insurance cost calculation requested",
            extra={
                'patient_id_hash': hash(patient_data['patient_id']),
                'calculation_type': 'visit_estimate',
                'timestamp': datetime.now(),
                'user_role': get_current_user_role()
            }
        )
        
        # Perform calculations locally - never send to external APIs
        estimate = self._perform_local_calculation(patient_data)
        
        # Log calculation completion (audit trail)
        self.audit_logger.info(
            "Insurance cost calculation completed",
            extra={
                'calculation_id': estimate.calculation_id,
                'confidence_level': estimate.confidence_level
            }
        )
        
        return estimate
```

## Implementation Guidelines

### Integration with Billing Helper Agent

Update `agents/billing_helper/ai-instructions.md` to include these advanced patterns:

```python
# Enhanced billing helper with advanced insurance
class AdvancedBillingHelper:
    def __init__(self):
        self.cost_predictor = VisitCostPredictor()
        self.deductible_tracker = DeductibleTracker()
        self.insurance_calculator = InsuranceCoverageCalculator()
    
    async def predict_visit_costs(self, appointment_data):
        """Provide accurate cost predictions for scheduled visits"""
        return await self.cost_predictor.predict_visit_cost(
            appointment_data['patient_id'],
            appointment_data['provider_id'],
            appointment_data['expected_cpt_codes'],
            appointment_data['visit_date']
        )
```

### Testing with Enhanced Synthetic Data

All insurance calculations must be tested with realistic synthetic data that matches real-world patterns:

```python
def generate_synthetic_insurance_data():
    """Generate realistic insurance test data"""
    return {
        'annual_deductible': Decimal('2000.00'),
        'deductible_met': Decimal('450.00'),
        'copay_structure': {
            'office_visit': CopayStructure(CopayType.FIXED_DOLLAR, Decimal('25.00')),
            'specialist': CopayStructure(CopayType.PERCENTAGE, Decimal('0.20')),
            'emergency': CopayStructure(CopayType.DEDUCTIBLE_THEN_PERCENTAGE, Decimal('0.10'))
        },
        'out_of_pocket_maximum': Decimal('8000.00'),
        'family_deductible': Decimal('4000.00')
    }
```

---

**Privacy Excellence**: All insurance calculations remain local, exceed HIPAA requirements, and provide complete audit trails for healthcare compliance.
