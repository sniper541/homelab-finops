import os

import psycopg


def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres.finops.svc.cluster.local"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "finops"),
        user=os.getenv("POSTGRES_USER", "finops"),
        password=os.environ["POSTGRES_PASSWORD"],
    )
