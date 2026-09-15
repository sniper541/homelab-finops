"""OAuth client credentials for the trusted Telegram polling service."""
import asyncio
import os
import time

import httpx

_token = None
_expires = 0.0
_lock = asyncio.Lock()


async def access_token():
    global _token, _expires
    async with _lock:
        if _token and time.monotonic() < _expires:
            return _token
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                os.environ["KEYCLOAK_TOKEN_URL"],
                data={"grant_type": "client_credentials", "client_id": "finops-bot",
                      "client_secret": os.environ["KEYCLOAK_CLIENT_SECRET"]},
            )
            response.raise_for_status()
            result = response.json()
        _token = result["access_token"]
        _expires = time.monotonic() + max(0, int(result["expires_in"]) - 30)
        return _token
