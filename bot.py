import logging
import requests
from dotenv import load_dotenv
import os
import random

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
    "🎭 Drama": "Drama",
    "😂 Comedy": "Comedy",
    "😱 Horror": "Horror",
    "🚀 Sci-Fi": "Sci-Fi",
    "🔫 Action": "Action",
    "💖 Romance": "Romance",
}

TIME_EMOJIS = {
    "🌅 Rīts": "rīts",
    "🌇 Vakars": "vakars",
    "🌃 Nakts": "nakts",
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Čau, esmu Meowie! 🎬 Es palīdzēšu atrast filmu vakaram.\n"
        "Norādi, vai Tu skaties vienatnē vai divatā.\n"
        "Izvēlies žanru un laiku, kad plāno skatīties 🐾\n\n"
        "Vai skatīsies viens vai kopā?",
        reply_markup=ReplyKeyboardMarkup(
            [["Viens", "Kopā"]], one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_PEOPLE

async def choose_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"people": update.message.text}
    genre_buttons = list(GENRE_EMOJIS.keys())
    keyboard = [genre_buttons[i:i+3] for i in range(0, len(genre_buttons), 3)]
    await update.message.reply_text(
        "Kādu žanru vēlies? Izvēlies no saraksta:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSE_GENRE

async def choose_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    genre = GENRE_EMOJIS.get(choice)
    if not genre:
        await update.message.reply_text("Lūdzu, izvēlies no pogām zemāk.")
        return CHOOSE_GENRE

    user_data[update.effective_chat.id]["genre"] = genre
    time_buttons = list(TIME_EMOJIS.keys())
    await update.message.reply_text(
        "Cikos skatīsieties filmu?",
        reply_markup=ReplyKeyboardMarkup([[b] for b in time_buttons], one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSE_TIME

async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    choice = update.message.text
    time = TIME_EMOJIS.get(choice)
    if not time:
        await update.message.reply_text("Lūdzu, izvēlies no piedāvātajām opcijām.")
        return CHOOSE_TIME

    user_data[user_id]["time"] = time
    genre = user_data[user_id]["genre"]

    try:
        params = {
            "apikey": OMDB_API_KEY,
            "type": "movie",
            "s": genre,
        }
        response = requests.get("http://www.omdbapi.com/", params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("Response") == "False" or "Search" not in data:
            await update.message.reply_text("Neizdevās atrast filmu ar šo žanru. Pamēģini vēlreiz!")
            return ConversationHandler.END

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
