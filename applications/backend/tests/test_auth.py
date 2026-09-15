"""Exercise real RS256 verification after the PyJWT security upgrade, without network access."""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app import auth
from app.main import app


@pytest.fixture
def signing_key(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    public_jwk.update(kid="test-only", use="sig", alg="RS256")
    monkeypatch.setattr(auth.jwks_client, "fetch_data", lambda: {"keys": [public_jwk]})
    return key


def token(key, **claims):
    payload = {"iss": auth.KEYCLOAK_ISSUER, "sub": "test-subject", "exp": int(time.time()) + 60}
    payload.update(claims)
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt.encode(
        payload, key, algorithm="RS256", headers={"kid": "test-only"}))


def test_valid_rs256_token(signing_key):
    assert auth.verify_access_token(token(signing_key))["sub"] == "test-subject"


@pytest.mark.parametrize("claims", [{"iss": "https://invalid.example/realm"}, {"exp": 1}, {"sub": ""}])
def test_invalid_claims_rejected(signing_key, claims):
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(token(signing_key, **claims))
    assert error.value.status_code == 401


def test_forged_signature_rejected(signing_key):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as error:
        auth.verify_access_token(token(other_key))
    assert error.value.status_code == 401


def test_auth_me_requires_bearer():
    response = TestClient(app).get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
