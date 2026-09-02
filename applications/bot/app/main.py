import os

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_URL = os.getenv("FINOPS_API_URL", "https://api.sniper541.com")
TELEGRAM_PROXY_URL = os.getenv(
    "TELEGRAM_PROXY_URL",
    "socks5://127.0.0.1:1080",
)

AMOUNT, CATEGORY, DESCRIPTION = range(3)


def main_menu():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Доход", callback_data="add_income"),
                InlineKeyboardButton("💸 Расход", callback_data="add_expense"),
            ],
            [
                InlineKeyboardButton("📂 Категории", callback_data="categories"),
                InlineKeyboardButton("📊 Отчёт", callback_data="report"),
            ],
            [
                InlineKeyboardButton("🧾 Операции", callback_data="transactions"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
            ],
        ]
    )


async def api_request(method: str, path: str, **kwargs):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.request(
            method,
            f"{API_URL}{path}",
            **kwargs,
        )
        response.raise_for_status()
        return response.json()


async def get_or_create_user(telegram_user):
    return await api_request(
        "POST",
        "/users/register",
        json={
            "telegram_id": telegram_user.id,
            "telegram_username": telegram_user.username,
            "first_name": telegram_user.first_name,
        },
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = await get_or_create_user(update.effective_user)
        context.user_data["user_id"] = user["id"]

        await update.message.reply_text(
            f"Привет, {update.effective_user.first_name}! 👋\n\n"
            "FinOps поможет учитывать доходы и расходы.",
            reply_markup=main_menu(),
        )
    except Exception:
        await update.message.reply_text(
            "Не удалось подключиться к FinOps API. Попробуй позже."
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_or_create_user(update.effective_user)
    context.user_data["user_id"] = user["id"]

    await update.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu(),
    )


async def ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "user_id" not in context.user_data:
        user = await get_or_create_user(update.effective_user)
        context.user_data["user_id"] = user["id"]

    return context.user_data["user_id"]


async def begin_transaction(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    await ensure_user(update, context)

    context.user_data["transaction_type"] = (
        "income" if query.data == "add_income" else "expense"
    )

    await query.message.reply_text(
        "Введите сумму:"
    )

    return AMOUNT


async def receive_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        amount = float(update.message.text.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Введите положительное число, например: 1500"
        )
        return AMOUNT

    context.user_data["amount"] = amount

    user_id = await ensure_user(update, context)
    transaction_type = context.user_data["transaction_type"]

    categories = await api_request(
        "GET",
        "/categories",
        params={
            "user_id": user_id,
            "type": transaction_type,
        },
    )

    if not categories:
        await update.message.reply_text(
            "Для этого типа операций пока нет категорий.\n"
            "Создай категорию через API/Swagger, "
            "а позже добавим создание прямо в боте.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    keyboard = []

    for category in categories:
        title = f"{category.get('icon') or '📁'} {category['name']}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    title,
                    callback_data=f"category:{category['id']}",
                )
            ]
        )

    await update.message.reply_text(
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return CATEGORY


async def receive_category(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split(":")[1])
    context.user_data["category_id"] = category_id

    await query.message.reply_text(
        "Введите комментарий к операции.\n"
        "Если комментарий не нужен — отправьте -"
    )

    return DESCRIPTION


async def receive_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    description = update.message.text.strip()

    if description == "-":
        description = None

    user_id = await ensure_user(update, context)

    try:
        transaction = await api_request(
            "POST",
            "/transactions",
            json={
                "user_id": user_id,
                "category_id": context.user_data["category_id"],
                "amount": context.user_data["amount"],
                "description": description,
            },
        )

        transaction_type = context.user_data["transaction_type"]

        icon = "💰" if transaction_type == "income" else "💸"
        operation = "Доход" if transaction_type == "income" else "Расход"

        await update.message.reply_text(
            f"{icon} {operation} добавлен\n"
            f"Сумма: {transaction['amount']}",
            reply_markup=main_menu(),
        )

    except Exception:
        await update.message.reply_text(
            "Не удалось сохранить операцию.",
            reply_markup=main_menu(),
        )

    return ConversationHandler.END


async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = await ensure_user(update, context)

    try:
        result = await api_request(
            "GET",
            "/categories",
            params={"user_id": user_id},
        )

        if not result:
            text = "Категорий пока нет."
        else:
            income = []
            expense = []

            for category in result:
                line = (
                    f"{category.get('icon') or '📁'} "
                    f"{category['name']}"
                )

                if category["type"] == "income":
                    income.append(line)
                else:
                    expense.append(line)

            text = "📂 Категории\n\n"

            text += "💰 Доходы:\n"
            text += "\n".join(income) if income else "—"
            text += "\n\n💸 Расходы:\n"
            text += "\n".join(expense) if expense else "—"

        await query.message.reply_text(
            text,
            reply_markup=main_menu(),
        )

    except Exception:
        await query.message.reply_text(
            "Не удалось получить категории.",
            reply_markup=main_menu(),
        )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = await ensure_user(update, context)

    try:
        result = await api_request(
            "GET",
            "/reports/summary",
            params={"user_id": user_id},
        )

        await query.message.reply_text(
            "📊 Общий отчёт\n\n"
            f"💰 Доходы: {result['income']}\n"
            f"💸 Расходы: {result['expense']}\n"
            f"💳 Баланс: {result['balance']}",
            reply_markup=main_menu(),
        )

    except Exception:
        await query.message.reply_text(
            "Не удалось получить отчёт.",
            reply_markup=main_menu(),
        )


async def transactions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    user_id = await ensure_user(update, context)

    try:
        result = await api_request(
            "GET",
            "/transactions",
            params={
                "user_id": user_id,
                "limit": 10,
            },
        )

        if not result:
            text = "🧾 Операций пока нет."
        else:
            lines = ["🧾 Последние операции\n"]

            for item in result:
                category = item.get("category") or {}
                category_type = category.get("type")

                icon = "💰" if category_type == "income" else "💸"

                category_name = category.get("name", "Без категории")

                lines.append(
                    f"{icon} {item['amount']} — {category_name}"
                )

            text = "\n".join(lines)

        await query.message.reply_text(
            text,
            reply_markup=main_menu(),
        )

    except Exception:
        await query.message.reply_text(
            "Не удалось получить операции.",
            reply_markup=main_menu(),
        )


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "⚙️ Настройки\n\n"
        "В MVP используются:\n"
        "• валюта: RUB\n"
        "• язык: RU\n"
        "• часовой пояс: Europe/Moscow\n\n"
        "Полноценные настройки добавим позже.",
        reply_markup=main_menu(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Операция отменена.",
        reply_markup=main_menu(),
    )

    return ConversationHandler.END


def main():
    telegram_request = HTTPXRequest(
        proxy=TELEGRAM_PROXY_URL,
    )

    telegram_updates_request = HTTPXRequest(
        proxy=TELEGRAM_PROXY_URL,
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(telegram_request)
        .get_updates_request(telegram_updates_request)
        .build()
    )

    transaction_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                begin_transaction,
                pattern="^(add_income|add_expense)$",
            ),
        ],
        states={
            AMOUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_amount,
                )
            ],
            CATEGORY: [
                CallbackQueryHandler(
                    receive_category,
                    pattern=r"^category:\d+$",
                )
            ],
            DESCRIPTION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_description,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))

    application.add_handler(transaction_handler)

    application.add_handler(
        CallbackQueryHandler(categories, pattern="^categories$")
    )
    application.add_handler(
        CallbackQueryHandler(report, pattern="^report$")
    )
    application.add_handler(
        CallbackQueryHandler(transactions, pattern="^transactions$")
    )
    application.add_handler(
        CallbackQueryHandler(settings, pattern="^settings$")
    )

    application.run_polling()


if __name__ == "__main__":
    main()