import os
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError, PyJWTError

from app.database import get_connection


KEYCLOAK_ISSUER = os.getenv(
    "KEYCLOAK_ISSUER",
    "https://auth.sniper541.com/realms/finops",
)

KEYCLOAK_JWKS_URL = os.getenv(
    "KEYCLOAK_JWKS_URL",
    "http://keycloak.keycloak.svc.cluster.local/realms/finops/protocol/openid-connect/certs",
)
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "finops-api")
BOT_CLIENT_ID = os.getenv("KEYCLOAK_BOT_CLIENT_ID", "finops-bot")

bearer_scheme = HTTPBearer(auto_error=False)
jwks_client = PyJWKClient(KEYCLOAK_JWKS_URL)


def verify_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=KEYCLOAK_ISSUER,
            audience=KEYCLOAK_AUDIENCE,
            options={
                "require": ["exp", "iss", "aud", "sub"],
            },
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except (PyJWTError, PyJWKClientError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")

    if not isinstance(sub, str) or not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain sub",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid subject", headers={"WWW-Authenticate": "Bearer"})
    return payload


def realm_roles(payload: dict[str, Any]) -> frozenset[str]:
    access = payload.get("realm_access")
    roles = access.get("roles", []) if isinstance(access, dict) else []
    return frozenset(role for role in roles if isinstance(role, str)) if isinstance(roles, list) else frozenset()


def require_roles(*required: str):
    """Require every named finops realm role; this does not grant master administration."""
    def check(payload: dict = Depends(verify_access_token), current_user: dict = Depends(get_current_user)):
        if not set(required).issubset(realm_roles(payload)):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current_user
    return check


def require_bot(payload: dict = Depends(verify_access_token)):
    access = payload.get("resource_access", {})
    client = access.get(KEYCLOAK_AUDIENCE, {}) if isinstance(access, dict) else {}
    roles = client.get("roles", []) if isinstance(client, dict) else []
    if payload.get("azp") != BOT_CLIENT_ID or not isinstance(roles, list) or "telegram-bot" not in roles:
        raise HTTPException(status_code=403, detail="Bot service identity required")
    return payload


def bot_telegram_id(
    payload: dict = Depends(require_bot),
    telegram_id: int = Header(alias="X-Telegram-User-ID", gt=0),
) -> int:
    # Only the authenticated polling service may assert an identity from Telegram updates.
    return telegram_id


def get_bot_user(telegram_id: int = Depends(bot_telegram_id)) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE telegram_id = %s AND is_active = TRUE", (telegram_id,))
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="Telegram user is not registered or inactive")
    return {"id": row[0]}


def get_current_user(
    token_payload: dict[str, Any] = Depends(verify_access_token),
) -> dict[str, Any]:
    if token_payload.get("azp") == BOT_CLIENT_ID:
        raise HTTPException(status_code=403, detail="User session required")
    sub = token_payload["sub"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    telegram_id,
                    telegram_username,
                    first_name,
                    keycloak_sub
                FROM users
                WHERE keycloak_sub = %s
                  AND is_active = TRUE
                """,
                (sub,),
            )
            row = cur.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not linked to FinOps",
        )

    return {
        "id": row[0],
        "telegram_id": row[1],
        "telegram_username": row[2],
        "first_name": row[3],
        "keycloak_sub": row[4],
    }
