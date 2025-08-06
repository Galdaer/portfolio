"""
Advanced Insurance Calculations for Healthcare AI

Supports:
- Percentage copays (not just fixed dollar amounts)
- Deductible proximity tracking and remaining balance calculations  
- Exact visit cost prediction capabilities
- Complex insurance structures (HSA, family vs individual, etc.)

MEDICAL DISCLAIMER: These calculations provide administrative support only.
They assist healthcare professionals with insurance processing and cost estimation.
They do not provide medical advice or replace clinical judgment.
All medical decisions must be made by qualified healthcare professionals.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


class CopayType(Enum):
    """Types of copayment structures supported"""
    FIXED_DOLLAR = "fixed_dollar"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    DEDUCTIBLE_THEN_PERCENTAGE = "deductible_then_percentage"


class InsuranceType(Enum):
    """Insurance plan types"""
    PPO = "ppo"
    HMO = "hmo"
    EPO = "epo"
    POS = "pos"
    HSA = "hsa"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"


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
    historical_meet_date: Optional[datetime] = None
    likelihood_to_meet: float = 0.0  # 0.0 to 1.0


@dataclass
class CostEstimate:
    """Comprehensive cost estimate for patient transparency"""
    total_billed: Decimal
    patient_responsibility: Decimal
    insurance_payment: Decimal
    deductible_applied: Decimal
    confidence_level: float
    
    # Detailed breakdown
    copay_amount: Decimal = Decimal("0")
    coinsurance_amount: Decimal = Decimal("0")
    out_of_pocket_impact: Decimal = Decimal("0")
    
    # Patient-friendly explanations
    cost_explanation: List[str] = field(default_factory=list)
    potential_variations: Dict[str, Decimal] = field(default_factory=dict)  # Best/worst case scenarios


@dataclass 
class PatientCoverage:
    """Patient's insurance coverage details"""
    patient_id: str
    insurance_type: InsuranceType
    annual_deductible: Decimal
    deductible_met: Decimal
    out_of_pocket_maximum: Decimal
    out_of_pocket_met: Decimal
    copay_structures: Dict[str, CopayStructure]
    coinsurance_rate: Decimal  # e.g., 0.20 for 20%
    family_plan: bool = False
    hsa_balance: Optional[Decimal] = None


class InsuranceCoverageCalculator:
    """Advanced insurance coverage calculation engine"""
    
    def __init__(self):
        self.service_categories = {
            "99213": "office_visit",
            "99214": "office_visit", 
            "99215": "office_visit",
            "99241": "specialist_consultation",
            "99242": "specialist_consultation",
            "36415": "laboratory",
            "85025": "laboratory",
            "99281": "emergency",
            "99282": "emergency",
        }
    
    def _ensure_decimal(self, value: Any) -> Decimal:
        """Convert various number types to Decimal safely"""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))  # Convert via string for precision
        if isinstance(value, str):
            return Decimal(value)
        raise ValueError(f"Cannot convert {type(value)} to Decimal")
        
    def calculate_patient_cost(
        self, 
        cpt_code: str, 
        billed_amount: Decimal,
        patient_coverage: PatientCoverage
    ) -> CostEstimate:
        """Calculate exact patient cost for a procedure"""
        
        # Ensure billed_amount is Decimal
        billed_amount = self._ensure_decimal(billed_amount)
        
        logger.info(f"Calculating patient cost for CPT {cpt_code}, amount ${billed_amount}")
        
        # Step 1: Determine service category
        service_category = self.categorize_cpt_code(cpt_code)
        
        # Step 2: Check deductible status
        deductible_status = self._calculate_deductible_status(patient_coverage)
        
        # Step 3: Apply appropriate copay structure
        copay_structure = patient_coverage.copay_structures.get(
            service_category, 
            patient_coverage.copay_structures.get("general")
        )
        
        if not copay_structure:
            # Default copay structure
            copay_structure = CopayStructure(
                copay_type=CopayType.PERCENTAGE,
                primary_amount=Decimal("0.20"),  # 20% coinsurance
                service_type=service_category
            )
        
        # Step 4: Calculate patient responsibility
        if deductible_status.remaining_amount > 0:
            patient_cost = self._calculate_with_deductible(
                billed_amount, deductible_status, copay_structure
            )
        else:
            patient_cost = self._calculate_post_deductible(
                billed_amount, copay_structure
            )
        
        # Step 5: Apply out-of-pocket maximums
        final_cost = self._apply_oop_maximum(patient_cost, patient_coverage)
        
        # Step 6: Generate patient-friendly explanation
        cost_explanation = self._generate_cost_explanation(
            billed_amount, final_cost, copay_structure, deductible_status
        )
        
        return CostEstimate(
            total_billed=billed_amount,
            patient_responsibility=final_cost,
            insurance_payment=billed_amount - final_cost,
            deductible_applied=min(deductible_status.remaining_amount, billed_amount),
            confidence_level=self._calculate_confidence(patient_coverage),
            cost_explanation=cost_explanation
        )
    
    def categorize_cpt_code(self, cpt_code: str) -> str:
        """Categorize CPT code for copay determination"""
        return self.service_categories.get(cpt_code, "general")
    
    def _calculate_deductible_status(self, patient_coverage: PatientCoverage) -> DeductibleStatus:
        """Calculate current deductible status with edge case protection"""
        # Handle zero or negative deductible (some plans have no deductible)
        if patient_coverage.annual_deductible <= 0:
            return DeductibleStatus(
                annual_deductible=patient_coverage.annual_deductible,
                amount_applied=patient_coverage.deductible_met,
                remaining_amount=Decimal('0'),
                percentage_met=1.0,
                projected_meet_date=None,
                family_vs_individual="family" if patient_coverage.family_plan else "individual",
                monthly_average_spending=Decimal("200.00")  # Mock value
            )
        
        remaining = patient_coverage.annual_deductible - patient_coverage.deductible_met
        percentage_met = float(patient_coverage.deductible_met / patient_coverage.annual_deductible)
        
        return DeductibleStatus(
            annual_deductible=patient_coverage.annual_deductible,
            amount_applied=patient_coverage.deductible_met,
            remaining_amount=max(remaining, Decimal('0')),  # Never negative
            percentage_met=min(percentage_met, 1.0),  # Never over 100%
            projected_meet_date=None,  # Would calculate based on spending patterns
            family_vs_individual="family" if patient_coverage.family_plan else "individual",
            monthly_average_spending=Decimal("200.00")  # Mock value
        )
    
    def _calculate_with_deductible(
        self, 
        billed_amount: Decimal, 
        deductible_status: DeductibleStatus,
        copay_structure: CopayStructure
    ) -> Decimal:
        """Calculate cost when deductible hasn't been met"""
        if deductible_status.remaining_amount >= billed_amount:
            # Patient pays full amount toward deductible
            return billed_amount
        else:
            # Patient pays remaining deductible + coinsurance on remainder
            deductible_portion = deductible_status.remaining_amount
            remainder = billed_amount - deductible_portion
            
            if copay_structure.copay_type == CopayType.PERCENTAGE:
                coinsurance = remainder * copay_structure.primary_amount
            elif copay_structure.copay_type == CopayType.FIXED_DOLLAR:
                coinsurance = copay_structure.primary_amount
            else:
                coinsurance = remainder * Decimal("0.20")  # Default 20%
            
            return deductible_portion + coinsurance
    
    def _calculate_post_deductible(
        self,
        billed_amount: Decimal,
        copay_structure: CopayStructure  
    ) -> Decimal:
        """Calculate cost after deductible is met"""
        if copay_structure.copay_type == CopayType.FIXED_DOLLAR:
            return copay_structure.primary_amount
        elif copay_structure.copay_type == CopayType.PERCENTAGE:
            return billed_amount * copay_structure.primary_amount
        else:
            return billed_amount * Decimal("0.20")  # Default 20%
    
    def _apply_oop_maximum(self, calculated_cost: Decimal, patient_coverage: PatientCoverage) -> Decimal:
        """Apply out-of-pocket maximum limits"""
        remaining_oop = patient_coverage.out_of_pocket_maximum - patient_coverage.out_of_pocket_met
        return min(calculated_cost, remaining_oop)
    
    def _calculate_confidence(self, patient_coverage: PatientCoverage) -> float:
        """Calculate confidence level in cost estimate"""
        # Higher confidence for simpler insurance types
        confidence_by_type = {
            InsuranceType.HMO: 0.95,
            InsuranceType.PPO: 0.85,
            InsuranceType.HSA: 0.75,
            InsuranceType.MEDICARE: 0.90,
            InsuranceType.MEDICAID: 0.80,
        }
        return confidence_by_type.get(patient_coverage.insurance_type, 0.75)
    
    def _generate_cost_explanation(
        self,
        billed_amount: Decimal,
        patient_cost: Decimal,
        copay_structure: CopayStructure,
        deductible_status: DeductibleStatus
    ) -> List[str]:
        """Generate patient-friendly cost explanations"""
        explanations = []
        
        if deductible_status.remaining_amount > 0:
            explanations.append(
                f"${min(deductible_status.remaining_amount, billed_amount):.2f} "
                f"will be applied to your ${deductible_status.annual_deductible:.2f} annual deductible"
            )
        
        if copay_structure.copay_type == CopayType.FIXED_DOLLAR:
            explanations.append(f"${copay_structure.primary_amount:.2f} copay")
        elif copay_structure.copay_type == CopayType.PERCENTAGE:
            percentage = copay_structure.primary_amount * 100
            explanations.append(f"{percentage:.0f}% coinsurance")
        
        explanations.append(f"Total estimated cost: ${patient_cost:.2f}")
        
        return explanations


class DeductibleTracker:
    """Advanced deductible tracking and prediction"""
    
    def __init__(self):
        self.spending_patterns = {}  # Would connect to actual spending history
    
    async def calculate_deductible_proximity(
        self, 
        patient_id: str,
        coverage_period: str = "current_year"
    ) -> DeductibleStatus:
        """Calculate how close patient is to meeting deductible"""
        
        # Mock data - in production, would query actual spending
        mock_coverage = PatientCoverage(
            patient_id=patient_id,
            insurance_type=InsuranceType.PPO,
            annual_deductible=Decimal("2000.00"),
            deductible_met=Decimal("450.00"),
            out_of_pocket_maximum=Decimal("8000.00"),
            out_of_pocket_met=Decimal("450.00"),
            copay_structures={},
            coinsurance_rate=Decimal("0.20")
        )
        
        remaining = mock_coverage.annual_deductible - mock_coverage.deductible_met
        percentage_met = float(mock_coverage.deductible_met / mock_coverage.annual_deductible)
        
        # Calculate likelihood to meet based on spending patterns
        monthly_average = Decimal("200.00")  # Mock calculation
        months_remaining = 12 - datetime.now().month
        projected_spending = monthly_average * months_remaining
        likelihood = min(float(projected_spending / remaining), 1.0) if remaining > 0 else 1.0
        
        return DeductibleStatus(
            annual_deductible=mock_coverage.annual_deductible,
            amount_applied=mock_coverage.deductible_met,
            remaining_amount=remaining,
            percentage_met=percentage_met,
            projected_meet_date=self._project_meet_date(monthly_average, remaining),
            monthly_average_spending=monthly_average,
            likelihood_to_meet=likelihood,
            family_vs_individual="individual"
        )
    
    def _project_meet_date(self, monthly_spending: Decimal, remaining: Decimal) -> Optional[datetime]:
        """Project when deductible will be met"""
        if remaining <= 0 or monthly_spending <= 0:
            return None
        
        months_to_meet = float(remaining / monthly_spending)
        if months_to_meet > 12:
            return None
        
        current_date = datetime.now()
        projected_month = current_date.month + int(months_to_meet)
        projected_year = current_date.year
        
        if projected_month > 12:
            projected_month -= 12
            projected_year += 1
        
        return datetime(projected_year, projected_month, 15)  # Mid-month estimate
    
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
        
        if status.likelihood_to_meet > 0.7:
            insights.append(
                f"High likelihood ({status.likelihood_to_meet:.0%}) of meeting your deductible this year"
            )
        elif status.likelihood_to_meet < 0.3:
            insights.append(
                "Low likelihood of meeting your deductible this year based on current spending patterns"
            )
        
        return insights


class VisitCostPredictor:
    """Predict exact costs for scheduled visits"""
    
    def __init__(self):
        self.calculator = InsuranceCoverageCalculator()
        self.negotiated_rates = self._load_negotiated_rates()
    
    async def predict_visit_cost(
        self,
        patient_id: str,
        provider_id: str,
        scheduled_cpt_codes: List[str],
        visit_date: datetime
    ) -> CostEstimate:
        """Predict exact cost before patient visit"""
        
        # Get patient coverage details (mock implementation)
        coverage = await self._get_patient_coverage(patient_id, visit_date)
        
        # Get provider's negotiated rates
        negotiated_rates = self._get_negotiated_rates(provider_id, scheduled_cpt_codes)
        
        # Calculate for each CPT code
        total_estimate = CostEstimate(
            total_billed=Decimal("0"),
            patient_responsibility=Decimal("0"),
            insurance_payment=Decimal("0"),
            deductible_applied=Decimal("0"),
            confidence_level=1.0
        )
        
        for cpt_code in scheduled_cpt_codes:
            cpt_estimate = self.calculator.calculate_patient_cost(
                cpt_code, negotiated_rates[cpt_code], coverage
            )
            total_estimate = self._combine_estimates(total_estimate, cpt_estimate)
        
        return total_estimate
    
    def _load_negotiated_rates(self) -> Dict[str, Decimal]:
        """Load negotiated rates by provider (mock implementation)"""
        return {
            "99213": Decimal("150.00"),
            "99214": Decimal("200.00"),
            "36415": Decimal("25.00"),
            "85025": Decimal("35.00"),
        }
    
    async def _get_patient_coverage(self, patient_id: str, visit_date: datetime) -> PatientCoverage:
        """Get patient coverage details (mock implementation)"""
        return PatientCoverage(
            patient_id=patient_id,
            insurance_type=InsuranceType.PPO,
            annual_deductible=Decimal("2000.00"),
            deductible_met=Decimal("450.00"),
            out_of_pocket_maximum=Decimal("8000.00"),
            out_of_pocket_met=Decimal("450.00"),
            copay_structures={
                "office_visit": CopayStructure(
                    copay_type=CopayType.FIXED_DOLLAR,
                    primary_amount=Decimal("25.00"),
                    service_type="office_visit"
                ),
                "specialist": CopayStructure(
                    copay_type=CopayType.PERCENTAGE,
                    primary_amount=Decimal("0.20"),
                    service_type="specialist"
                )
            },
            coinsurance_rate=Decimal("0.20")
        )
    
    def _get_negotiated_rates(self, provider_id: str, cpt_codes: List[str]) -> Dict[str, Decimal]:
        """Get negotiated rates for provider"""
        return {cpt_code: self.negotiated_rates.get(cpt_code, Decimal("100.00")) for cpt_code in cpt_codes}
    
    def _combine_estimates(self, total: CostEstimate, individual: CostEstimate) -> CostEstimate:
        """Combine individual CPT estimates into total"""
        total.total_billed += individual.total_billed
        total.patient_responsibility += individual.patient_responsibility
        total.insurance_payment += individual.insurance_payment
        total.deductible_applied += individual.deductible_applied
        total.cost_explanation.extend(individual.cost_explanation)
        return total