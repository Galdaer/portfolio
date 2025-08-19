"""
Healthcare financial utilities for shared financial calculations.

This module provides shared utilities for healthcare financial operations
including type safety, decimal conversion, and billing calculations.
"""

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class HealthcareFinancialUtils:
    """Shared financial utilities for healthcare calculations."""

    @staticmethod
    def ensure_decimal(value: Any) -> Decimal:
        """
        Convert various number types to Decimal safely for healthcare financial calculations.

        Args:
            value: The value to convert (int, float, str, or Decimal)

        Returns:
            Decimal: The value as a Decimal for precise financial calculations

        Raises:
            ValueError: If the value cannot be converted to Decimal
        """
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int | float):
            return Decimal(str(value))  # Convert via string for precision
        if isinstance(value, str):
            try:
                return Decimal(value)
            except Exception as e:
                msg = f"Cannot convert string '{value}' to Decimal"
                raise ValueError(msg) from e

        msg = f"Cannot convert {type(value)} to Decimal"
        raise ValueError(msg)

    @staticmethod
    def safe_division(
        numerator: Decimal,
        denominator: Decimal,
        default: Decimal = Decimal("0"),
    ) -> Decimal:
        """
        Perform safe division with zero protection for healthcare calculations.

        Args:
            numerator: The numerator value
            denominator: The denominator value
            default: Value to return if denominator is zero

        Returns:
            Decimal: The result of division or default if denominator is zero
        """
        if denominator <= 0:
            logger.warning(
                f"Division by zero avoided: {numerator} / {denominator}, returning {default}",
            )
            return default
        return numerator / denominator

    @staticmethod
    def calculate_percentage(amount: Decimal, total: Decimal) -> float:
        """
        Calculate percentage with zero protection.

        Args:
            amount: The amount value
            total: The total value

        Returns:
            float: The percentage (0.0 to 1.0) or 0.0 if total is zero
        """
        if total <= 0:
            return 0.0
        return float(amount / total)

    @staticmethod
    def validate_financial_amount(amount: Any, field_name: str = "amount") -> Decimal:
        """
        Validate and convert a financial amount to Decimal.

        Args:
            amount: The amount to validate
            field_name: Name of the field for error messages

        Returns:
            Decimal: The validated amount

        Raises:
            ValueError: If amount is invalid for financial calculations
        """
        try:
            decimal_amount = HealthcareFinancialUtils.ensure_decimal(amount)

            if decimal_amount < 0:
                msg = f"{field_name} cannot be negative: {decimal_amount}"
                raise ValueError(msg)

            return decimal_amount

        except (ValueError, TypeError) as e:
            msg = f"Invalid {field_name}: {amount} - {str(e)}"
            raise ValueError(msg) from e
