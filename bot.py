import logging
import os
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
from trakt_recommendation import get_random_movie_by_genre

load_dotenv()

MEOWVIE_BOT_TOKEN = os.getenv("MEOWVIE_BOT_TOKEN")

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

TIME_EMOJIS = ["🌅", "🌇", "🌃"]

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Čau, esmu Meowie!🎬\n"
        "Es palīdzēšu atrast filmu vakaram.\n"
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
    await update.message.reply_text(
        "Kādu žanru vēlies? Izvēlies:",
        reply_markup=ReplyKeyboardMarkup(
            [[e for e in GENRE_EMOJIS.keys()]], one_time_keyboard=True, resize_keyboard=True
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
    await update.message.reply_text(
        "Cikos skatīsieties filmu?",
        reply_markup=ReplyKeyboardMarkup(
            [[e] for e in TIME_EMOJIS], one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_TIME

async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_data[user_id]["time"] = update.message.text
    genre = user_data[user_id]["genre"]
    people = user_data[user_id]["people"]

    try:
        movie = get_random_movie_by_genre(genre, people)

        if not movie:
            await update.message.reply_text("Neizdevās atrast filmu. Pamēģini vēlāk.")
            return ConversationHandler.END

        reply_text = (
            f"🎬 *[{movie['title']}]({movie['trakt_url']})* ({movie['year']})
"
            f"Žanri: {movie['genres']}

"
            f"{movie['overview']}"
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
