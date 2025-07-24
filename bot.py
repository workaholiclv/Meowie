import logging
import os
import json
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
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

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
if not TG_BOT_TOKEN:
    raise ValueError("TG_BOT_TOKEN nav norādīts Railway vai .env failā")

CHOOSE_PEOPLE, CHOOSE_GENRE, CHOOSE_TIME = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANGUAGES = ["Latviešu", "English"]
DEFAULT_LANGUAGE = "Latviešu"

GENRE_EMOJIS = {
    "🎭": "drama",
    "😂": "comedy",
    "😱": "horror",
    "🚀": "science-fiction",
    "🔫": "action",
    "💖": "romance",
}

TIME_EMOJIS = ["🌅", "🌇", "🌃"]

HISTORY_FILE = "user_history.json"

if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump({}, f)

def load_history():
    with open(HISTORY_FILE, 'r') as f:
        return json.load(f)

def save_history(data):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_text(key, lang):
    texts = {
        "start": {
            "Latviešu": "Čau, esmu Meowie!🎬\nEs palīdzēšu atrast filmu vakaram.\nNorādi, vai Tu skaties vienatnē vai divatā.\nIzvēlies žanru un laiku, kad plāno skatīties 🐾\n\nVai skatīsies viens vai kopā?",
            "English": "Hi, I'm Meowie!🎬\nI'll help you find a movie for tonight.\nTell me if you're watching alone or together.\nChoose a genre and time 🐾\n\nAre you watching alone or with someone?"
        },
        "genre_prompt": {
            "Latviešu": "Kādu žanru vēlies? Izvēlies:",
            "English": "What genre do you want? Choose:"
        },
        "time_prompt": {
            "Latviešu": "Cikos skatīsieties filmu?",
            "English": "When will you watch the movie?"
        },
        "not_found": {
            "Latviešu": "Neizdevās atrast filmu. Pamēģini vēlāk.",
            "English": "Couldn't find a movie. Try again later."
        },
        "cancel": {
            "Latviešu": "Filmas meklēšana atcelta.",
            "English": "Movie search cancelled."
        },
        "choose_language": {
            "Latviešu": "Izvēlies valodu / Choose a language:",
            "English": "Izvēlies valodu / Choose a language:"
        }
    }
    return texts[key].get(lang, texts[key][DEFAULT_LANGUAGE])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["lang"] = DEFAULT_LANGUAGE
    await update.message.reply_text(
        get_text("start", context.user_data["lang"]),
        reply_markup=ReplyKeyboardMarkup(
            [["Viens", "Kopā"]] if context.user_data["lang"] == "Latviešu" else [["Alone", "Together"]],
            one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_PEOPLE

async def choose_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["people"] = update.message.text
    lang = context.user_data["lang"]
    await update.message.reply_text(
        get_text("genre_prompt", lang),
        reply_markup=ReplyKeyboardMarkup(
            [[e] for e in GENRE_EMOJIS.keys()], one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_GENRE

async def choose_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji = update.message.text
    genre = GENRE_EMOJIS.get(emoji)
    if not genre:
        await update.message.reply_text("Lūdzu, izvēlies no piedāvātajām opcijām.")
        return CHOOSE_GENRE

    context.user_data["genre"] = genre
    await update.message.reply_text(
        get_text("time_prompt", context.user_data["lang"]),
        reply_markup=ReplyKeyboardMarkup(
            [[e] for e in TIME_EMOJIS], one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_TIME

async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = update.message.text
    genre = context.user_data.get("genre")
    people = context.user_data.get("people")
    lang = context.user_data.get("lang")

    try:
        movie = get_random_movie_by_genre(genre, people)
        if not movie:
            await update.message.reply_text(get_text("not_found", lang))
            return ConversationHandler.END

        user_id = str(update.effective_user.id)
        history = load_history()
        history.setdefault(user_id, []).append({
            "title": movie["title"],
            "year": movie["year"],
            "url": movie["trakt_url"],
            "people": people,
            "genre": genre,
            "time": context.user_data["time"]
        })
        save_history(history)

        reply_text = (
            f"🎬 *[{movie['title']}]({movie['trakt_url']})* ({movie['year']})\n\n"
            f"Žanri: {movie['genres']}\n\n"
            f"{movie['overview']}"
        )

        buttons = []
        if movie.get("youtube_trailer"):
            buttons.append([InlineKeyboardButton("🎞️ Trailer", url=movie["youtube_trailer"])])

        await update.message.reply_text(reply_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)

    except Exception as e:
        logger.error(f"Kļūda: {e}")
        await update.message.reply_text(get_text("not_found", lang))

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text("cancel", context.user_data["lang"]))
    return ConversationHandler.END

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        get_text("choose_language", DEFAULT_LANGUAGE),
        reply_markup=ReplyKeyboardMarkup(
            [[lang] for lang in LANGUAGES], one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_PEOPLE

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    lang = context.user_data.get("lang", DEFAULT_LANGUAGE)
    history = load_history().get(user_id, [])

    if not history:
        await update.message.reply_text("Vēsture ir tukša." if lang == "Latviešu" else "History is empty.")
        return

    lines = []
    for item in history[-5:]:
        lines.append(f"{item['title']} ({item['year']}) - {item['genre']} - {item['people']} - {item['time']}")
    await update.message.reply_text("\n".join(lines))

def main():
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()

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
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("language", set_language))
    app.add_handler(CommandHandler("history", history))

    print("Meowie ieskrējis čatā!")
    app.run_polling()

if __name__ == "__main__":
    main()
