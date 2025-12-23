import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# Состояния для заполнения/изменения профиля
MMR, POSITION, MODE = range(3)

DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            mmr INTEGER,
            position TEXT,
            mode TEXT
        )
        """
    )
    conn.commit()
    conn.close()

init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Искать тиммейта", callback_data="search_party")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="my_profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Это бот для поиска пати в Dota 2 🔥\nВыбери действие:", reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "my_profile":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT mmr, position, mode FROM profiles WHERE user_id = ?", (user_id,))
        profile = cursor.fetchone()
        conn.close()

        if profile:
            text = (
                f"👤 Твой профиль:\n\n"
                f"📊 MMR: {profile[0]}\n"
                f"🎯 Позиция: {profile[1]}\n"
                f"🎮 Режим: {profile[2]}"
            )
            keyboard = [[InlineKeyboardButton("✏️ Изменить профиль", callback_data="edit_profile")]]
        else:
            text = "❌ Профиль ещё не заполнен.\nЗаполни его, чтобы искать тиммейтов!"
            keyboard = [[InlineKeyboardButton("📝 Заполнить профиль", callback_data="edit_profile")]]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)
        return ConversationHandler.END

    elif query.data == "edit_profile":
        await query.edit_message_text("Введи свой MMR (например: 3500):")
        return MMR

    elif query.data == "search_party":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT mmr FROM profiles WHERE user_id = ?", (user_id,))
        user_mmr_row = cursor.fetchone()
        conn.close()

        if not user_mmr_row:
            keyboard = [[InlineKeyboardButton("📝 Заполнить профиль", callback_data="edit_profile")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Чтобы искать тиммейта, сначала нужно заполнить профиль!", reply_markup=reply_markup
            )
            return ConversationHandler.END

        user_mmr = user_mmr_row[0]
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, mmr, position, mode FROM profiles
            WHERE user_id != ? AND mmr BETWEEN ? AND ?
            LIMIT 10
            """,
            (user_id, user_mmr - 500, user_mmr + 500),
        )
        matches = cursor.fetchall()
        conn.close()

        if not matches:
            await query.edit_message_text("😔 Пока никто не найден с похожим MMR. Попробуй позже!")
            return ConversationHandler.END

        text = "🔥 Найденные тиммейты:\n\n"
        for m in matches:
            text += f"👤 Игрок: t.me/userid{m[0]}\n📊 MMR: {m[1]} | 🎯 {m[2]} | 🎮 {m[3]}\n\n"

        text += "Напиши им в ЛС, чтобы договориться о игре!"
        await query.edit_message_text(text=text)
        return ConversationHandler.END

# Этапы заполнения/изменения профиля
async def get_mmr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mmr = int(update.message.text.strip())
        if mmr < 0 or mmr > 15000:
            raise ValueError
        context.user_data["mmr"] = mmr
        await update.message.reply_text("🎯 Укажи предпочитаемую позицию (например: Carry, Mid, Offlane, Soft 4, Hard 5):")
        return POSITION
    except ValueError:
        await update.message.reply_text("❌ Введи корректное число MMR (от 0 до 15000)!")
        return MMR

async def get_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["position"] = update.message.text.strip()
    await update.message.reply_text("🎮 Предпочитаемый режим (например: Ranked, Unranked, Turbo):")
    return MODE

async def get_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    mode = update.message.text.strip()
    mmr = context.user_data.get("mmr")
    position = context.user_data.get("position")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO profiles (user_id, mmr, position, mode)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, mmr, position, mode),
    )
    conn.commit
