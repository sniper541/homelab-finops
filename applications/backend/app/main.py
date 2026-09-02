import os
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FinOps API")

class UserRegisterRequest(BaseModel):
    telegram_id: int
    telegram_username: str | None = None
    first_name: str | None = None

class CategoryCreateRequest(BaseModel):
    user_id: int
    type: str
    name: str
    icon: str | None = None

class CategoryUpdateRequest(BaseModel):
    user_id: int
    name: str | None = None
    icon: str | None = None


class TransactionCreateRequest(BaseModel):
    user_id: int
    category_id: int
    amount: float
    description: str | None = None

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


@app.post("/transactions")
def create_transaction(payload: TransactionCreateRequest):
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (
                    user_id,
                    category_id,
                    amount,
                    description
                )
                SELECT %s, id, %s, %s
                FROM categories
                WHERE id = %s
                  AND user_id = %s
                  AND is_active = true
                RETURNING
                    id,
                    user_id,
                    category_id,
                    amount,
                    description,
                    occurred_at,
                    created_at
                """,
                (
                    payload.user_id,
                    payload.amount,
                    payload.description,
                    payload.category_id,
                    payload.user_id,
                ),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=400, detail="Invalid category")

    return {
        "id": row[0],
        "user_id": row[1],
        "category_id": row[2],
        "amount": float(row[3]),
        "description": row[4],
        "occurred_at": row[5],
        "created_at": row[6],
    }


@app.get("/transactions")
def get_transactions(
    user_id: int,
    limit: int = 100,
):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 500")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    t.id,
                    t.amount,
                    t.description,
                    t.occurred_at,
                    c.id,
                    c.name,
                    c.icon,
                    c.type
                FROM transactions t
                JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = %s
                ORDER BY t.occurred_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "amount": float(row[1]),
            "description": row[2],
            "occurred_at": row[3],
            "category": {
                "id": row[4],
                "name": row[5],
                "icon": row[6],
                "type": row[7],
            },
        }
        for row in rows
    ]


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM transactions
                WHERE id = %s
                  AND user_id = %s
                RETURNING id
                """,
                (transaction_id, user_id),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"status": "deleted"}

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
@app.post("/categories")
def create_category(payload: CategoryCreateRequest):
    if payload.type not in ("income", "expense"):
        raise HTTPException(
            status_code=400,
            detail="Category type must be income or expense",
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO categories (
                    user_id,
                    type,
                    name,
                    icon
                )
                VALUES (%s, %s, %s, %s)
                RETURNING
                    id,
                    user_id,
                    type,
                    name,
                    icon,
                    is_active,
                    created_at,
                    updated_at
                """,
                (
                    payload.user_id,
                    payload.type,
                    payload.name,
                    payload.icon,
                ),
            )

            row = cur.fetchone()

    return {
        "id": row[0],
        "user_id": row[1],
        "type": row[2],
        "name": row[3],
        "icon": row[4],
        "is_active": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }

@app.get("/categories")
def get_categories(user_id: int, type: str | None = None):
    if type is not None and type not in ("income", "expense"):
        raise HTTPException(status_code=400, detail="Invalid category type")

    with get_connection() as conn:
        with conn.cursor() as cur:
            if type:
                cur.execute(
                    """
                    SELECT id, user_id, type, name, icon, is_active
                    FROM categories
                    WHERE user_id = %s
                      AND type = %s
                      AND is_active = true
                    ORDER BY name
                    """,
                    (user_id, type),
                )
            else:
                cur.execute(
                    """
                    SELECT id, user_id, type, name, icon, is_active
                    FROM categories
                    WHERE user_id = %s
                      AND is_active = true
                    ORDER BY type, name
                    """,
                    (user_id,),
                )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "type": row[2],
            "name": row[3],
            "icon": row[4],
            "is_active": row[5],
        }
        for row in rows
    ]


@app.patch("/categories/{category_id}")
def update_category(category_id: int, payload: CategoryUpdateRequest):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE categories
                SET
                    name = COALESCE(%s, name),
                    icon = COALESCE(%s, icon),
                    updated_at = now()
                WHERE id = %s
                  AND user_id = %s
                  AND is_active = true
                RETURNING id, user_id, type, name, icon, is_active
                """,
                (
                    payload.name,
                    payload.icon,
                    category_id,
                    payload.user_id,
                ),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return {
        "id": row[0],
        "user_id": row[1],
        "type": row[2],
        "name": row[3],
        "icon": row[4],
        "is_active": row[5],
    }


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE categories
                SET is_active = false,
                    updated_at = now()
                WHERE id = %s
                  AND user_id = %s
                  AND is_active = true
                RETURNING id
                """,
                (category_id, user_id),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"status": "deleted"}

@app.get("/reports/summary")
def report_summary(user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(
                        CASE WHEN c.type = 'income'
                        THEN t.amount ELSE 0 END
                    ), 0),
                    COALESCE(SUM(
                        CASE WHEN c.type = 'expense'
                        THEN t.amount ELSE 0 END
                    ), 0)
                FROM transactions t
                JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = %s
                """,
                (user_id,),
            )

            row = cur.fetchone()

    income = float(row[0])
    expense = float(row[1])

    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
    }