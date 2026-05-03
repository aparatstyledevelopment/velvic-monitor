"""Property tests around password hashing.

Demonstrates the Hypothesis harness; expanded with engine calculations in
Phase 1.

bcrypt has two structural constraints we have to honour in the strategy:
- it rejects NULL bytes,
- it rejects passwords longer than 72 bytes after UTF-8 encoding.
The API layer's Pydantic schema enforces 12-128 chars; we bound the
strategy to what bcrypt itself accepts.
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.auth.security import hash_password, verify_password

# Printable ASCII keeps the byte length predictable and avoids NULLs.
_ALPHA = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E),
    min_size=12,
    max_size=64,
)


@given(password=_ALPHA)
@settings(max_examples=25, deadline=None)
def test_verify_accepts_correct_password(password: str) -> None:
    h = hash_password(password)
    assert verify_password(password, h)


@given(password=_ALPHA, other=_ALPHA)
@settings(max_examples=25, deadline=None)
def test_verify_rejects_different_password(password: str, other: str) -> None:
    assume(other != password)
    h = hash_password(password)
    assert not verify_password(other, h)
