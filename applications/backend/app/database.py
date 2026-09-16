import json
import os
from pathlib import Path

import psycopg


def get_connection():
    credentials_file = os.getenv("POSTGRES_CREDENTIALS_FILE")
    if credentials_file:
        # Agent atomically replaces this file when the dynamic lease rotates.
        # Read on every connection; never freeze a lease in process environment.
        try:
            credentials = json.loads(Path(credentials_file).read_text())
            username, password = credentials["username"], credentials["password"]
            if not all(isinstance(value, str) and value for value in (username, password)):
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError):
            # No fallback to bootstrap credentials and no secret-bearing parse error.
            raise RuntimeError("Database credentials are unavailable") from None
    else:
        # Explicit environment mode remains for local development and CI.
        username = os.getenv("POSTGRES_USER", "finops")
        password = os.environ["POSTGRES_PASSWORD"]
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres.finops.svc.cluster.local"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "finops"),
        user=username,
        password=password,
        connect_timeout=5,
    )
