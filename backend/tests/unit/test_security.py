from uuid import uuid4

import pytest

from app.auth.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.errors import AuthError


def test_hash_password_round_trips() -> None:
    h = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", h)
    assert not verify_password("wrong password", h)


def test_hash_password_distinct_each_call() -> None:
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b


def test_access_token_round_trips() -> None:
    user_id = uuid4()
    org_id = uuid4()
    token = create_access_token(user_id=user_id, org_id=org_id, role="admin")
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["org_id"] == str(org_id)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_decode_rejects_garbage() -> None:
    with pytest.raises(AuthError):
        decode_token("not.a.token")


def test_decode_rejects_empty() -> None:
    with pytest.raises(AuthError):
        decode_token("")
