import os
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FinOps API")

class UserRegisterRequest(BaseModel):
    telegram_id: int
    telegram_username: str | None = None
    first_name: str | None = None

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

@app.get("/health/live")
def liveness():
    return {"status": "alive"}

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
@app.post("/users/register")
def register_user(payload: UserRegisterRequest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    telegram_id,
                    telegram_username,
                    first_name
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    telegram_username = EXCLUDED.telegram_username,
                    first_name = EXCLUDED.first_name,
                    updated_at = now()
                RETURNING
                    id,
                    telegram_id,
                    telegram_username,
                    first_name,
                    is_active,
                    created_at,
                    updated_at
                """,
                (
                    payload.telegram_id,
                    payload.telegram_username,
                    payload.first_name,
                ),
            )

            row = cur.fetchone()

            cur.execute(
                """
                INSERT INTO user_settings (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (row[0],),
            )

    return {
        "id": row[0],
        "telegram_id": row[1],
        "telegram_username": row[2],
        "first_name": row[3],
        "is_active": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }
