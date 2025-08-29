"""
Payment Processing and Tracking for Billing Engine
Handles payment processing, tracking, and reconciliation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import uuid4

from models.billing_models import (
    ClaimResult,
    ClaimStatus,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
)

logger = logging.getLogger(__name__)


class PaymentTracker:
    """Handles payment processing, tracking, and reconciliation"""

    def __init__(self):
        # Payment processing configuration
        self.processing_fees = {
            "electronic": Decimal("0.00"),  # No fee for electronic payments
            "check": Decimal("2.50"),       # Check processing fee
            "cash": Decimal("0.00"),        # No fee for cash
            "credit_card": Decimal("0.029"), # 2.9% for credit card
        }

        # Payment method validation rules
        self.payment_limits = {
            "electronic": {"min": Decimal("0.01"), "max": Decimal("100000.00")},
            "check": {"min": Decimal("0.01"), "max": Decimal("50000.00")},
            "cash": {"min": Decimal("0.01"), "max": Decimal("1000.00")},
            "credit_card": {"min": Decimal("0.01"), "max": Decimal("25000.00")},
        }

        # Reconciliation rules
        self.reconciliation_tolerance = Decimal("0.01")  # 1 cent tolerance

    async def process_payment(
        self,
        request: PaymentRequest,
        claim_info: ClaimResult,
    ) -> PaymentResult:
        """Process a payment against a claim"""

        payment_id = f"pay_{uuid4().hex[:8]}"

        try:
            # Validate payment request
            validation_result = await self._validate_payment_request(request, claim_info)
            if not validation_result["valid"]:
                return PaymentResult(
                    payment_id=payment_id,
                    claim_id=request.claim_id,
                    status=PaymentStatus.FAILED,
                    processed_amount=Decimal("0.00"),
                    remaining_balance=claim_info.total_charges,
                    payment_date=datetime.utcnow(),
                    processing_errors=validation_result["errors"],
                )

            # Calculate processing fees
            fee_info = await self._calculate_processing_fees(
                request.payment_amount, request.payment_method,
            )
            net_payment_amount = request.payment_amount - fee_info["fee"]

            # Process the payment
            processing_result = await self._execute_payment_processing(
                request, net_payment_amount,
            )

            if not processing_result["successful"]:
                return PaymentResult(
                    payment_id=payment_id,
                    claim_id=request.claim_id,
                    status=PaymentStatus.FAILED,
                    processed_amount=Decimal("0.00"),
                    remaining_balance=claim_info.total_charges,
                    payment_date=datetime.utcnow(),
                    processing_errors=processing_result["errors"],
                )

            # Update claim balance
            current_balance = await self._calculate_current_balance(claim_info.claim_id)
            new_balance = current_balance - net_payment_amount

            # Handle adjustments if provided
            if request.adjustment_amount:
                adjustment_result = await self._process_adjustment(
                    request.adjustment_amount,
                    request.adjustment_reason,
                    claim_info.claim_id,
                )
                new_balance += adjustment_result["net_adjustment"]

            # Generate reconciliation info
            reconciliation_info = await self._generate_reconciliation_info(
                request, claim_info, net_payment_amount, fee_info,
            )

            # Create payment result
            return PaymentResult(
                payment_id=payment_id,
                claim_id=request.claim_id,
                status=PaymentStatus.COMPLETED if new_balance <= self.reconciliation_tolerance else PaymentStatus.COMPLETED,
                processed_amount=net_payment_amount,
                remaining_balance=max(Decimal("0.00"), new_balance),
                payment_date=request.payment_date,
                confirmation_number=processing_result.get("confirmation_number"),
                reconciliation_info=reconciliation_info,
                metadata={
                    "processing_fee": fee_info["fee"],
                    "gross_payment": request.payment_amount,
                    "payment_method": request.payment_method,
                    "payer_name": request.payer_name,
                    "check_number": request.check_number,
                    "is_patient_payment": request.patient_payment,
                },
            )

        except Exception as e:
            logger.exception(f"Payment processing failed: {e}")
            return PaymentResult(
                payment_id=payment_id,
                claim_id=request.claim_id,
                status=PaymentStatus.FAILED,
                processed_amount=Decimal("0.00"),
                remaining_balance=claim_info.total_charges,
                payment_date=datetime.utcnow(),
                processing_errors=[f"Payment processing error: {str(e)}"],
            )

    async def reconcile_claim_payments(
        self,
        claim_id: str,
        expected_total: Decimal,
    ) -> dict[str, Any]:
        """Reconcile all payments for a claim against expected total"""

        reconciliation_id = f"recon_{uuid4().hex[:8]}"

        # Get all payments for this claim
        claim_payments = await self._get_claim_payments(claim_id)

        # Calculate totals
        total_payments = sum(payment["amount"] for payment in claim_payments)
        total_adjustments = sum(payment.get("adjustment", Decimal("0.00")) for payment in claim_payments)
        net_total = total_payments + total_adjustments

        # Calculate variance
        variance = expected_total - net_total

        # Determine reconciliation status
        if abs(variance) <= self.reconciliation_tolerance:
            status = "reconciled"
            actions_needed = []
        elif variance > self.reconciliation_tolerance:
            status = "underpaid"
            actions_needed = [
                f"Collect additional ${variance:.2f}",
                "Review for missing payments or incorrect expected amount",
            ]
        else:  # variance < -tolerance
            status = "overpaid"
            actions_needed = [
                f"Process refund of ${abs(variance):.2f}",
                "Review for duplicate payments or incorrect expected amount",
            ]

        return {
            "reconciliation_id": reconciliation_id,
            "claim_id": claim_id,
            "status": status,
            "expected_total": expected_total,
            "actual_total": net_total,
            "variance": variance,
            "payment_count": len(claim_payments),
            "payment_details": claim_payments,
            "actions_needed": actions_needed,
            "reconciliation_date": datetime.utcnow().isoformat(),
        }

    async def generate_payment_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive payment report for a date range"""

        report_id = f"report_{uuid4().hex[:8]}"
        filters = filters or {}

        # Mock data - in production, query from database
        payments_data = await self._get_payments_for_period(start_date, end_date, filters)

        # Calculate summary statistics
        total_payments = sum(payment["amount"] for payment in payments_data)
        payment_count = len(payments_data)
        avg_payment = total_payments / payment_count if payment_count > 0 else Decimal("0.00")

        # Group by payment method
        method_breakdown = {}
        for payment in payments_data:
            method = payment.get("method", "unknown")
            if method not in method_breakdown:
                method_breakdown[method] = {
                    "count": 0,
                    "total": Decimal("0.00"),
                    "percentage": 0.0,
                }
            method_breakdown[method]["count"] += 1
            method_breakdown[method]["total"] += payment["amount"]

        # Calculate percentages
        for method in method_breakdown:
            method_breakdown[method]["percentage"] = float(
                (method_breakdown[method]["total"] / total_payments * 100) if total_payments > 0 else 0,
            )

        # Identify processing issues
        processing_issues = await self._identify_processing_issues(payments_data)

        return {
            "report_id": report_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_payments": float(total_payments),
                "payment_count": payment_count,
                "average_payment": float(avg_payment),
                "largest_payment": float(max((p["amount"] for p in payments_data), default=Decimal("0.00"))),
                "smallest_payment": float(min((p["amount"] for p in payments_data), default=Decimal("0.00"))),
            },
            "method_breakdown": {
                method: {
                    "count": data["count"],
                    "total": float(data["total"]),
                    "percentage": data["percentage"],
                }
                for method, data in method_breakdown.items()
            },
            "processing_issues": processing_issues,
            "generated_date": datetime.utcnow().isoformat(),
        }

    async def track_payment_status(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        """Track the status of a specific payment"""

        # Mock payment tracking - in production, integrate with payment processors
        payment_info = await self._get_payment_info(payment_id)

        if not payment_info:
            return {
                "payment_id": payment_id,
                "status": "not_found",
                "error": "Payment not found",
            }

        # Determine detailed status
        status_details = await self._get_detailed_payment_status(payment_info)

        return {
            "payment_id": payment_id,
            "status": payment_info["status"],
            "status_details": status_details,
            "amount": float(payment_info["amount"]),
            "payment_method": payment_info["method"],
            "payment_date": payment_info["date"],
            "confirmation_number": payment_info.get("confirmation"),
            "last_updated": datetime.utcnow().isoformat(),
        }

    # Validation and helper methods
    async def _validate_payment_request(
        self,
        request: PaymentRequest,
        claim_info: ClaimResult,
    ) -> dict[str, Any]:
        """Validate payment request"""

        errors = []
        warnings = []

        # Amount validation
        if request.payment_amount <= Decimal("0.00"):
            errors.append("Payment amount must be greater than zero")

        # Payment method validation
        if request.payment_method not in self.payment_limits:
            errors.append(f"Invalid payment method: {request.payment_method}")
        else:
            limits = self.payment_limits[request.payment_method]
            if request.payment_amount < limits["min"]:
                errors.append(f"Payment amount below minimum for {request.payment_method}")
            elif request.payment_amount > limits["max"]:
                errors.append(f"Payment amount exceeds maximum for {request.payment_method}")

        # Check payment method specific requirements
        if request.payment_method == "check" and not request.check_number:
            errors.append("Check number required for check payments")

        # Claim status validation
        if claim_info.status not in [ClaimStatus.APPROVED, ClaimStatus.PAID]:
            warnings.append(f"Claim status is {claim_info.status} - payment may be premature")

        # Overpayment check
        current_balance = await self._calculate_current_balance(claim_info.claim_id)
        if request.payment_amount > current_balance + Decimal("100.00"):  # Allow some overpayment tolerance
            warnings.append(f"Payment amount (${request.payment_amount}) exceeds remaining balance (${current_balance})")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    async def _calculate_processing_fees(
        self,
        amount: Decimal,
        payment_method: str,
    ) -> dict[str, Any]:
        """Calculate processing fees for payment"""

        fee_rate = self.processing_fees.get(payment_method, Decimal("0.00"))

        if payment_method == "credit_card":
            # Percentage-based fee
            fee = (amount * fee_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            # Flat fee
            fee = fee_rate

        return {
            "fee": fee,
            "fee_rate": float(fee_rate),
            "fee_type": "percentage" if payment_method == "credit_card" else "flat",
        }

    async def _execute_payment_processing(
        self,
        request: PaymentRequest,
        net_amount: Decimal,
    ) -> dict[str, Any]:
        """Execute the actual payment processing"""

        # Mock payment processing - in production, integrate with payment gateway

        try:
            # Simulate processing delay
            await asyncio.sleep(0.1)

            # Generate confirmation number
            confirmation_number = f"{request.payment_method.upper()}{uuid4().hex[:8].upper()}"

            # Mock processing success
            return {
                "successful": True,
                "confirmation_number": confirmation_number,
                "processed_amount": net_amount,
                "processing_time": datetime.utcnow(),
            }

        except Exception as e:
            return {
                "successful": False,
                "errors": [f"Payment processing failed: {str(e)}"],
            }

    async def _process_adjustment(
        self,
        adjustment_amount: Decimal,
        adjustment_reason: str | None,
        claim_id: str,
    ) -> dict[str, Any]:
        """Process payment adjustment"""

        adjustment_id = f"adj_{uuid4().hex[:8]}"

        # Log adjustment for audit trail
        logger.info(
            f"Processing adjustment {adjustment_id} for claim {claim_id}: "
            f"${adjustment_amount} - {adjustment_reason or 'No reason provided'}",
        )

        return {
            "adjustment_id": adjustment_id,
            "net_adjustment": adjustment_amount,
            "reason": adjustment_reason,
            "processed_date": datetime.utcnow(),
        }

    async def _generate_reconciliation_info(
        self,
        request: PaymentRequest,
        claim_info: ClaimResult,
        net_amount: Decimal,
        fee_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate reconciliation information"""

        return {
            "reconciliation_id": f"recon_{uuid4().hex[:8]}",
            "original_claim_amount": float(claim_info.total_charges),
            "approved_amount": float(claim_info.approved_amount or Decimal("0.00")),
            "payment_gross": float(request.payment_amount),
            "payment_net": float(net_amount),
            "processing_fee": float(fee_info["fee"]),
            "adjustment": float(request.adjustment_amount or Decimal("0.00")),
            "reconciliation_date": datetime.utcnow().isoformat(),
        }

    # Mock data methods - replace with actual database queries
    async def _calculate_current_balance(self, claim_id: str) -> Decimal:
        """Calculate current balance for a claim"""
        # Mock calculation - in production, sum all payments against claim
        return Decimal("250.00")  # Mock remaining balance

    async def _get_claim_payments(self, claim_id: str) -> list[dict[str, Any]]:
        """Get all payments for a claim"""
        # Mock payments data
        return [
            {
                "payment_id": "pay_12345678",
                "amount": Decimal("150.00"),
                "method": "electronic",
                "date": datetime.utcnow() - timedelta(days=5),
                "adjustment": Decimal("0.00"),
            },
            {
                "payment_id": "pay_87654321",
                "amount": Decimal("50.00"),
                "method": "check",
                "date": datetime.utcnow() - timedelta(days=2),
                "adjustment": Decimal("-10.00"),
            },
        ]

    async def _get_payments_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Get payments for a specific period"""
        # Mock payments data
        return [
            {
                "payment_id": "pay_12345678",
                "amount": Decimal("150.00"),
                "method": "electronic",
                "date": start_date + timedelta(days=1),
                "claim_id": "claim_001",
            },
            {
                "payment_id": "pay_87654321",
                "amount": Decimal("75.50"),
                "method": "check",
                "date": start_date + timedelta(days=3),
                "claim_id": "claim_002",
            },
        ]

    async def _identify_processing_issues(
        self,
        payments_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Identify potential processing issues"""

        issues = []

        # Check for duplicate payments
        payment_amounts = {}
        for payment in payments_data:
            amount = payment["amount"]
            date = payment["date"].date()
            key = (amount, date)

            if key in payment_amounts:
                issues.append({
                    "type": "potential_duplicate",
                    "description": f"Multiple payments of ${amount} on {date}",
                    "payment_ids": [payment_amounts[key], payment["payment_id"]],
                })
            else:
                payment_amounts[key] = payment["payment_id"]

        # Check for unusual amounts (very large or very small)
        for payment in payments_data:
            amount = payment["amount"]
            if amount > Decimal("10000.00"):
                issues.append({
                    "type": "large_payment",
                    "description": f"Unusually large payment: ${amount}",
                    "payment_id": payment["payment_id"],
                })
            elif amount < Decimal("1.00"):
                issues.append({
                    "type": "small_payment",
                    "description": f"Unusually small payment: ${amount}",
                    "payment_id": payment["payment_id"],
                })

        return issues

    async def _get_payment_info(self, payment_id: str) -> dict[str, Any] | None:
        """Get payment information by ID"""
        # Mock payment info
        return {
            "payment_id": payment_id,
            "status": "completed",
            "amount": Decimal("125.00"),
            "method": "electronic",
            "date": datetime.utcnow().isoformat(),
            "confirmation": f"CONF_{uuid4().hex[:8].upper()}",
        }

    async def _get_detailed_payment_status(
        self,
        payment_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Get detailed payment status information"""

        return {
            "processing_stage": "completed",
            "estimated_settlement": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "bank_reference": f"BANK_{uuid4().hex[:8].upper()}",
            "fees_applied": "2.50",
            "currency": "USD",
        }
