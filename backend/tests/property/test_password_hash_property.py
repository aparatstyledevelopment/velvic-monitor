"""Property tests around password hashing.

Demonstrates the Hypothesis harness; expanded with engine calculations in
Phase 1.
"""
from hypothesis import given, settings
from hypothesis import strategies as st

from app.auth.security import hash_password, verify_password


@given(password=st.text(min_size=12, max_size=128))
@settings(max_examples=25, deadline=None)
def test_verify_accepts_correct_password(password: str) -> None:
    h = hash_password(password)
    assert verify_password(password, h)


@given(
    password=st.text(min_size=12, max_size=128),
    other=st.text(min_size=1, max_size=128),
)
@settings(max_examples=25, deadline=None)
def test_verify_rejects_different_password(password: str, other: str) -> None:
    if other == password:
        return
    h = hash_password(password)
    assert not verify_password(other, h)
