import logging
import os
import random
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

load_dotenv()

MEOWVIE_BOT_TOKEN = os.getenv("MEOWVIE_BOT_TOKEN")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

CHOOSE_PEOPLE, CHOOSE_GENRE, CHOOSE_TIME = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENRE_EMOJIS = {
    "🎭": "drama",
    "😂": "comedy",
    "😱": "horror",
    "🚀": "science-fiction",
    "🔫": "action",
    "💖": "romance",
}

TIME_EMOJIS = {
    "🌅": "rīts",
    "🌇": "vakars",
    "🌃": "nakts",
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Čau, esmu Meowie! 🎬 Palīdzēšu atrast filmu vakaram.\n"
        "Norādi, vai Tu skaties viens vai kopā:",
        reply_markup=ReplyKeyboardMarkup(
            [["Viens", "Kopā"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CHOOSE_PEOPLE

async def choose_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"people": update.message.text}
    await update.message.reply_text(
        "Izvēlies filmu žanru:",
        reply_markup=ReplyKeyboardMarkup(
            [[e for e in GENRE_EMOJIS.keys()]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CHOOSE_GENRE

async def choose_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji = update.message.text
    genre = GENRE_EMOJIS.get(emoji)
    if not genre:
        await update.message.reply_text("Lūdzu, izvēlies no saraksta.")
        return CHOOSE_GENRE

    user_data[update.effective_chat.id]["genre"] = genre
    await update.message.reply_text(
        "Kad plāno skatīties filmu?",
        reply_markup=ReplyKeyboardMarkup(
            [[e for e in TIME_EMOJIS.keys()]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return CHOOSE_TIME

async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_data[user_id]["time"] = TIME_EMOJIS.get(update.message.text, "—")
    genre = user_data[user_id]["genre"]

    try:
        headers = {
            "Content-Type": "application/json",
            "trakt-api-key": TRAKT_CLIENT_ID,
            "trakt-api-version": "2"
        }
        url = f"https://api.trakt.tv/movies/popular?genres={genre}&limit=10"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        movies = response.json()

        if not movies:
            await update.message.reply_text("Neizdevās atrast filmu ar šo žanru.")
            return ConversationHandler.END

        movie = random.choice(movies)
        title = movie.get("title", "Filma")
        year = movie.get("year", "")
        trakt_url = f"https://trakt.tv/movies/{movie.get('ids', {}).get('slug', '')}"

        await update.message.reply_text(
            f"🎬 *[{title} ({year})]({trakt_url})*",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Kļūda: {e}")
        await update.message.reply_text("Neizdevās iegūt filmu. Pamēģini vēlāk.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Meklēšana atcelta.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_PEOPLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_people)],
            CHOOSE_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_genre)],
            CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
