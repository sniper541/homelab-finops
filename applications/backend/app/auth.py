import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
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
            options={
                # Temporary until finops-api audience is configured in Keycloak.
                "verify_aud": False,
            },
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except (PyJWTError, PyJWKClientError):
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

    return payload


def get_current_user(
    token_payload: dict[str, Any] = Depends(verify_access_token),
) -> dict[str, Any]:
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