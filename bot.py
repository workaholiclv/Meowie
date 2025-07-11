import logging
import os
import random
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

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
    "🎭": "Drama",
    "😂": "Comedy",
    "😱": "Horror",
    "🚀": "Sci-Fi",
    "🔫": "Action",
    "💖": "Romance",
}

TIME_EMOJIS = ["🌅", "🌇", "🌃"]  # rīts, vakars, nakts

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Čau, esmu Meowie! 🎬 Es palīdzēšu atrast filmu vakaram.\n"
        "Norādi, vai Tu skaties vienatnē vai divatā.\n\n"
        "Vai skatīsies viens vai kopā?",
        reply_markup=ReplyKeyboardMarkup(
            [["Viens"], ["Kopā"]],  # кнопки в столбик по одной
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return CHOOSE_PEOPLE

async def choose_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"people": update.message.text}
    keyboard = [[emoji] for emoji in GENRE_EMOJIS.keys()]  # кнопки в столбик, каждая — свой эмодзи

    await update.message.reply_text(
        "Kādu žanru vēlies? Izvēlies emoji:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return CHOOSE_GENRE

async def choose_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji = update.message.text
    genre = GENRE_EMOJIS.get(emoji)
    if not genre:
        await update.message.reply_text("Lūdzu, izvēlies no piedāvātajām opcijām.")
        return CHOOSE_GENRE

    user_data[update.effective_chat.id]["genre"] = genre
    time_keyboard = [[e] for e in TIME_EMOJIS]  # кнопки по одному в строке

    await update.message.reply_text(
        "Cikos skatīsieties filmu? 🌅 - rīts, 🌇 - vakars, 🌃 - nakts",
        reply_markup=ReplyKeyboardMarkup(
            time_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
    )
    return CHOOSE_TIME

async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_data[user_id]["time"] = update.message.text
    genre = user_data[user_id]["genre"]

    try:
        params = {
            "apikey": OMDB_API_KEY,
            "type": "movie",
            "s": genre,  # поиск по жанру
        }
        response = requests.get("http://www.omdbapi.com/", params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "False" or "Search" not in data:
            await update.message.reply_text(
                "Neizdevās atrast filmu ar šo žanru. Pamēģini vēlreiz!"
            )
            return ConversationHandler.END

        import random
        film = random.choice(data["Search"])
        imdb_id = film.get("imdbID")

        details_params = {"apikey": OMDB_API_KEY, "i": imdb_id, "plot": "short"}
        details_resp = requests.get("http://www.omdbapi.com/", params=details_params)
        details_resp.raise_for_status()
        details = details_resp.json()

        title = details.get("Title", "Filma")
        imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
        genres = details.get("Genre", "Nav pieejams")
        plot = details.get("Plot", "Apraksts nav pieejams.")

        reply_text = (
            f"🎬 *[{title}]({imdb_url})*\n"
            f"Žanri: {genres}\n\n"
            f"{plot}"
        )
        await update.message.reply_text(reply_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Kļūda: {e}")
        await update.message.reply_text("Neizdevās iegūt filmu. Pamēģini vēlāk.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Filmas meklēšana atcelta.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(MEOWVIE_BOT_TOKEN).build()

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
    print("Meowie ieskrējis čatā!")
    app.run_polling()

if __name__ == "__main__":
    main()
