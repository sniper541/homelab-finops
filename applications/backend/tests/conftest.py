import os
import subprocess
import sys
import time
import uuid

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import auth
from app.database import get_connection
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url="https://test.invalid") as client:
        yield client


@pytest.fixture
def issue_token(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    jwk.update(kid="test-only", use="sig", alg="RS256")
    jwks = jwt.PyJWKClient("https://jwks.example.invalid")
    monkeypatch.setattr(jwks, "fetch_data", lambda: {"keys": [jwk]})
    monkeypatch.setattr(auth, "jwks_client", jwks)
    def issue(sub=None, **overrides):
        payload = {"sub": str(uuid.uuid4()) if sub is None else sub, "iss": auth.KEYCLOAK_ISSUER,
                   "aud": auth.KEYCLOAK_AUDIENCE, "exp": int(time.time()) + 300,
                   "azp": "finops-web", "realm_access": {"roles": ["user"]}}
        payload.update(overrides)
        payload = {k:v for k,v in payload.items() if v is not None}
        return jwt.encode(payload, key, algorithm="RS256", headers={"kid": "test-only"})
    return issue


@pytest.fixture(scope="session")
def migrated_db():
    # Never permit this destructive fixture to point at the production database.
    assert os.environ.get("POSTGRES_DB") == "finops_test", "Use a disposable finops_test database"
    with get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS transactions (id BIGSERIAL PRIMARY KEY)")
    # The historical baseline represents a table that predates Alembic.
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    yield


@pytest.fixture
def users(migrated_db):
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute("TRUNCATE users CASCADE")
        ids = [row[0] for row in conn.execute("INSERT INTO users (telegram_id, keycloak_sub) VALUES (10101, %s), (20202, %s) RETURNING id", (a,b)).fetchall()]
    return [{"id": ids[0], "sub": a, "telegram_id":10101}, {"id":ids[1], "sub":b, "telegram_id":20202}]
