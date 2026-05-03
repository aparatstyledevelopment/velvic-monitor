"""Property tests for daily_return_pct.

Catches edge cases AI-generated code tends to miss: zero divisor, negative
returns, very small/large prices, exact-equal closes (should be 0%).
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.shared.prices import daily_return_pct

# Bounded positive prices.
prices = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("100000"),
    allow_nan=False,
    allow_infinity=False,
    places=4,
)


@given(today=prices, prior=prices)
@settings(max_examples=50, deadline=None)
def test_return_recovers_today_from_prior(today: Decimal, prior: Decimal) -> None:
    pct = daily_return_pct(today, prior)
    # today should equal prior * (1 + pct/100), within rounding.
    reconstructed = prior * (Decimal("1") + pct / Decimal("100"))
    diff = abs(reconstructed - today)
    # Allow tiny numerical slack for very small denominators.
    assert diff <= max(today, prior) * Decimal("1e-6") + Decimal("1e-6")


def test_zero_prior_returns_zero() -> None:
    assert daily_return_pct(Decimal("100"), Decimal("0")) == Decimal("0.0")


def test_equal_closes_returns_zero() -> None:
    assert daily_return_pct(Decimal("250.5"), Decimal("250.5")) == Decimal("0")


def test_negative_return_works() -> None:
    pct = daily_return_pct(Decimal("90"), Decimal("100"))
    assert pct == Decimal("-10")
