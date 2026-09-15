import os

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from typing import Literal

from app.auth import bot_telegram_id, get_bot_user, get_current_user
from app.database import get_connection

def reject_identity_override(request: Request):
    if "user_id" in request.query_params:
        raise HTTPException(status_code=422, detail="user_id is not a client-selectable identity")


app = FastAPI(title="FinOps API", dependencies=[Depends(reject_identity_override)])
bot = APIRouter(prefix="/bot", tags=["Telegram service"])


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "WEB_CORS_ORIGINS",
        "https://app.sniper541.com,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

class UserRegisterRequest(RequestModel):
    telegram_username: str | None = Field(default=None, max_length=64)
    first_name: str | None = Field(default=None, max_length=128)

class CategoryCreateRequest(RequestModel):
    type: Literal["income", "expense"]
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=32)


class CategoryUpdateRequest(RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = Field(default=None, max_length=32)


class TransactionCreateRequest(RequestModel):
    category_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    description: str | None = None


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
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/transactions")
def create_transaction(payload: TransactionCreateRequest, current_user: dict = Depends(get_current_user)):
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
                    current_user["id"],
                    payload.amount,
                    payload.description,
                    payload.category_id,
                    current_user["id"],
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
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
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
                JOIN categories c ON c.id = t.category_id AND c.user_id = t.user_id
                WHERE t.user_id = %s
                ORDER BY t.occurred_at DESC
                LIMIT %s
                """,
                (current_user["id"], limit),
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
def delete_transaction(transaction_id: int, current_user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM transactions
                WHERE id = %s
                  AND user_id = %s
                RETURNING id
                """,
                (transaction_id, current_user["id"]),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {"status": "deleted"}

@bot.post("/users/register")
def register_user(payload: UserRegisterRequest, telegram_id: int = Depends(bot_telegram_id)):
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
                WHERE users.is_active = TRUE
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
                    telegram_id,
                    payload.telegram_username,
                    payload.first_name,
                ),
            )

            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=403, detail="User is inactive")

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
def create_category(
    payload: CategoryCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    if payload.type not in ("income", "expense"):
        raise HTTPException(
            status_code=400,
            detail="Category type must be income or expense",
        )

    user_id = current_user["id"]

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
                    user_id,
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
def get_categories(type: str | None = None, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
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
def update_category(category_id: int, payload: CategoryUpdateRequest, current_user: dict = Depends(get_current_user)):
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
                    current_user["id"],
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
def delete_category(category_id: int, current_user: dict = Depends(get_current_user)):
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
                (category_id, current_user["id"]),
            )

            row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"status": "deleted"}

@app.get("/reports/summary")
def report_summary(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
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
                JOIN categories c ON c.id = t.category_id AND c.user_id = t.user_id
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
@app.get("/auth/me")
def auth_me(current_user: dict = Depends(get_current_user)):
    return current_user


# Separate authenticated service routes reuse the same ownership-enforcing operations.
# Neither browsers nor the bot can choose an internal FinOps user_id.
@bot.get("/categories")
def bot_categories(type: str | None = None, user: dict = Depends(get_bot_user)):
    return get_categories(type=type, current_user=user)


@bot.get("/transactions")
def bot_transactions(limit: int = 100, user: dict = Depends(get_bot_user)):
    return get_transactions(limit=limit, current_user=user)


@bot.post("/transactions")
def bot_create_transaction(payload: TransactionCreateRequest, user: dict = Depends(get_bot_user)):
    return create_transaction(payload, current_user=user)


@bot.get("/reports/summary")
def bot_summary(user: dict = Depends(get_bot_user)):
    return report_summary(current_user=user)


app.include_router(bot)
