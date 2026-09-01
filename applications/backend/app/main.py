import os

import psycopg
from fastapi import FastAPI, HTTPException

app = FastAPI(title="FinOps API")


def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "finops"),
        user=os.getenv("POSTGRES_USER", "finops"),
        password=os.environ["POSTGRES_PASSWORD"],
    )


@app.get("/")
def root():
    return {
        "service": "finops-api",
        "status": "running"
    }


@app.get("/version")
def version():
    return {"version": "auto-cd-test"}

@app.get("/health/ready")
def readiness():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return {"status": "ready"}

    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/transactions")
def transactions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, description, amount, created_at
                FROM transactions
                ORDER BY id
            """)

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "description": row[1],
            "amount": float(row[2]),
            "created_at": row[3]
        }
        for row in rows
    ]
