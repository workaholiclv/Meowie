import logging
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

IMDB_API_KEY = "TAVS_IMDB_API_KEY"
MEOWVIE_BOT_TOKEN = "TAVS_BOT_TOKEN"

CHOOSE_PEOPLE, CHOOSE_GENRE, CHOOSE_TIME = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Emojis uz žanriem
GENRE_EMOJIS = {
    "🎭": "Drama",
    "😂": "Comedy",
    "😱": "Horror",
    "🚀": "Sci-Fi",
    "🔫": "Action",
    "💖": "Romance"
}

# Laiks diennakts
TIME_EMOJIS = ["🌅", "🌇", "🌃"]  # rīts, vakars, nakts

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Sveiki! 🎬 Es palīdzēšu atrast filmu vakaram.

Vai skatīsies viens vai kopā?",
        reply_markup=ReplyKeyboardMarkup([["Viens", "Kopā"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSE_PEOPLE

async def choose_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"people": update.message.text}
    await update.message.reply_text(
        "Kādu žanru vēlies? Izvēlies emoji:",
        reply_markup=ReplyKeyboardMarkup([[k for k in GENRE_EMOJIS]], one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSE_GENRE

async def choose_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji = update.message.text
    genre = GENRE_EMOJIS.get(emoji, "Drama")
    user_data[update.effective_chat.id]["genre"] = genre
    await update.message.reply_text(
        "Cikos skatīsieties filmu? 🌅 - rīts, 🌇 - vakars, 🌃 - nakts",
        reply_markup=ReplyKeyboardMarkup([[e] for e in TIME_EMOJIS], one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOOSE_TIME

async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["time"] = update.message.text
    genre = user_data[update.effective_chat.id]["genre"]

    imdb_url = f"https://imdb-api.com/API/AdvancedSearch/{IMDB_API_KEY}?genres={genre.lower()}&sort=user_rating,desc"
    try:
        response = requests.get(imdb_url)
        data = response.json()
        results = data.get("results", [])
        if not results:
            await update.message.reply_text("Neizdevās atrast filmu. Pamēģini vēlreiz!")
        else:
            top = results[0]
            title = top.get("title", "Filma")
            link = top.get("link", "")
            description = top.get("plot", "")
            await update.message.reply_text(f"🎬 [{title}]({link})

{description}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Kļūda: {e}")
        await update.message.reply_text("Neizdevās iegūt filmu. Pamēģini vēlāk.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Filmas meklēšana atcelta.")
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
