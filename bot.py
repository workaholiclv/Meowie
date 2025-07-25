import logging
import os
import json
from dotenv import load_dotenv
import random
import aiohttp  # обязательно!

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    Filter,
)

from trakt_recommendation import get_movies_by_genre_and_people  # твоя функция
load_dotenv()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")


if not TG_BOT_TOKEN:
    raise ValueError("TG_BOT_TOKEN nav norādīts Railway vai .env failā")


CHOOSE_PEOPLE, CHOOSE_GENRE, CHOOSE_TIME, CHOOSE_RATING, CHOOSE_REPEAT, WAITING_QUESTION = range(6)

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

RATING_OPTIONS = ["5+", "6+", "7+", "8+", "9+"]

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
        "rating_prompt": {
            "Latviešu": "Izvēlies minimālo filmas vērtējumu:",
            "English": "Choose minimum movie rating:"
        },
        "invalid_rating": {
            "Latviešu": "Lūdzu, ievadi derīgu vērtējumu no 0 līdz 10.",
            "English": "Please enter a valid rating from 0 to 10."
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
        },
        "repeat_prompt": {
            "Latviešu": "Izvēlies, ko darīt tālāk:",
            "English": "Choose what to do next:"
        },
        "repeat_option": {
            "Latviešu": "🔄 Vēl filmu",
            "English": "🔄 Another movie"
        },
        "restart_option": {
            "Latviešu": "🔁 Sākt no jauna",
            "English": "🔁 Restart"
        },
        "choose_repeat_invalid": {
            "Latviešu": "Lūdzu, izvēlies no piedāvātajām opcijām.",
            "English": "Please choose from the offered options."
        },
        "history_empty": {
            "Latviešu": "Vēsture ir tukša.",
            "English": "History is empty."
        }
    }
    return texts[key].get(lang, texts[key][DEFAULT_LANGUAGE])

def get_random_movie_by_genre(genre, people, min_rating=0):
    movies = get_movies_by_genre_and_people(genre, people)
    
    if not movies:
        logger.warning(f"No movies found for genre={genre}, people={people}")
        return None

    filtered = [m for m in movies if m.get("rating", 0) >= min_rating]
    
    logger.info(f"Found {len(filtered)} movies after filtering with min_rating={min_rating} "
                f"out of {len(movies)} total.")

    if not filtered and min_rating > 0:
        logger.info(f"No movies found with rating >= {min_rating}. Trying without rating filter.")
        return random.choice(movies)

    return random.choice(filtered) if filtered else None

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
        await update.message.reply_text(get_text("choose_repeat_invalid", context.user_data["lang"]))
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
    lang = context.user_data.get("lang")

    await update.message.reply_text(
        get_text("rating_prompt", lang),
        reply_markup=ReplyKeyboardMarkup(
            [[r] for r in RATING_OPTIONS], one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_RATING

async def choose_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", DEFAULT_LANGUAGE)
    text = update.message.text.strip()

    try:
        rating = int(text.rstrip("+"))  # убираем плюс, если есть
        if rating < 0 or rating > 10:
            raise ValueError("Invalid rating range")
    except ValueError:
        await update.message.reply_text(get_text("invalid_rating", lang))
        return CHOOSE_RATING

    min_rating = rating
    if rating >= 9:
        min_rating = 8.5

    context.user_data["min_rating"] = min_rating

    genre = context.user_data.get("genre")
    people = context.user_data.get("people")

    try:
        movie = get_random_movie_by_genre(genre, people, min_rating=min_rating)
        if not movie:
            await update.message.reply_text(get_text("not_found", lang))
            return CHOOSE_RATING

        context.user_data["last_movie"] = movie

        user_id = str(update.effective_user.id)
        history = load_history()
        history.setdefault(user_id, []).append({
            "title": movie["title"],
            "year": movie["year"],
            "url": movie["trakt_url"],
            "people": people,
            "genre": genre,
            "time": context.user_data.get("time", ""),
            "min_rating": min_rating
        })
        save_history(history)

        await send_movie_with_buttons(update.message, context, movie, lang)
        return CHOOSE_REPEAT

    except Exception as e:
        logger.error(f"Kļūda izvēloties filmu pēc reitinga: {e}")
        await update.message.reply_text(get_text("not_found", lang))
        return CHOOSE_RATING

async def send_movie_with_buttons(update_or_query_message, context, movie, lang):
    reply_text = (
        f"🎬 *[{movie['title']}]({movie['trakt_url']})* ({movie['year']})\n\n"
        f"Žanri: {movie['genres']}\n\n"
        f"Vērtējums: {movie.get('rating', 'nav')}\n\n"
        f"{movie['overview']}"
    )

    buttons = []
    if movie.get("youtube_trailer"):
        buttons.append([InlineKeyboardButton("🎞️ Trailer", url=movie["youtube_trailer"])])

    buttons.append([
        InlineKeyboardButton("🤖", callback_data="ask_ai"),
        InlineKeyboardButton(get_text("repeat_option", lang), callback_data="repeat_movie"),
        InlineKeyboardButton(get_text("restart_option", lang), callback_data="restart")
    ])

    await update_or_query_message.reply_text(
        reply_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def choose_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip().lower()
    lang = context.user_data.get("lang", DEFAULT_LANGUAGE)

    repeat_text = get_text("repeat_option", lang).lower()
    restart_text = get_text("restart_option", lang).lower()

    if choice == repeat_text:
        genre = context.user_data.get("genre")
        people = context.user_data.get("people")
        min_rating = context.user_data.get("min_rating", 0)
        try:
            movie = get_random_movie_by_genre(genre, people, min_rating=min_rating)
            if not movie:
                await update.message.reply_text(get_text("not_found", lang))
                return ConversationHandler.END

            context.user_data["last_movie"] = movie

            user_id = str(update.effective_user.id)
            history = load_history()
            history.setdefault(user_id, []).append({
                "title": movie["title"],
                "year": movie["year"],
                "url": movie["trakt_url"],
                "people": people,
                "genre": genre,
                "time": context.user_data.get("time", ""),
                "min_rating": min_rating
            })
            save_history(history)

            await send_movie_with_buttons(update.message, context, movie, lang)

            return CHOOSE_REPEAT

        except Exception as e:
            logger.error(f"Kļūda: {e}")
            await update.message.reply_text(get_text("not_found", lang))
            return ConversationHandler.END

    elif choice == restart_text:
        return await start(update, context)

    else:
        await update.message.reply_text(get_text("choose_repeat_invalid", lang))
        return CHOOSE_REPEAT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text("cancel", context.user_data.get("lang", DEFAULT_LANGUAGE)))
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
        await update.message.reply_text(get_text("history_empty", lang))
        return

    lines = []
    for item in history[-5:]:
        lines.append(f"{item['title']} ({item['year']}) - {item['genre']} - {item['people']} - {item['time']}")
    await update.message.reply_text("\n".join(lines))

# --- Кастомный фильтр для WAITING_QUESTION ---
class WaitingForAiFilter(filters.Filter):
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        return context.user_data.get("waiting_for_ai_question", False)

waiting_for_ai_filter = WaitingForAiFilter()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get("lang", DEFAULT_LANGUAGE)

    if data == "ask_ai":
        await query.message.reply_text(
            "Lūdzu, uzraksti savu jautājumu par filmu. Es gaidīšu tavu ziņu."
        )
        context.user_data["waiting_for_ai_question"] = True
        # Не возвращаем состояние!
        return

    elif data == "repeat_movie":
        genre = context.user_data.get("genre")
        people = context.user_data.get("people")
        min_rating = context.user_data.get("min_rating", 0)
        try:
            movie = get_random_movie_by_genre(genre, people, min_rating=min_rating)
            if not movie:
                await query.message.reply_text(get_text("not_found", lang))
                return ConversationHandler.END

            context.user_data["last_movie"] = movie

            user_id = str(query.from_user.id)
            history = load_history()
            history.setdefault(user_id, []).append({
                "title": movie["title"],
                "year": movie["year"],
                "url": movie["trakt_url"],
                "people": people,
                "genre": genre,
                "time": context.user_data.get("time", ""),
                "min_rating": min_rating
            })
            save_history(history)

            await send_movie_with_buttons(query.message, context, movie, lang)
            return CHOOSE_REPEAT

        except Exception as e:
            logger.error(f"Kļūda: {e}")
            await query.message.reply_text(get_text("not_found", lang))
            return ConversationHandler.END

    elif data == "restart":
        await query.message.reply_text(get_text("cancel", lang))
        return await start(update, context)

    else:
        await query.message.reply_text("Nezināma izvēle. Lūdzu, mēģini vēlreiz.")
        return CHOOSE_REPEAT

async def handle_ai_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", DEFAULT_LANGUAGE)

    if not context.user_data.get("waiting_for_ai_question"):
        await update.message.reply_text("Lūdzu, izmanto izvēlnes pogas.")
        return CHOOSE_REPEAT

    context.user_data["waiting_for_ai_question"] = False
    user_question = update.message.text

    movie = context.user_data.get("last_movie", {})
    prompt = f"Film: {movie.get('title', 'unknown')}\nQuestion: {user_question}\nAnswer:"

    logger.info(f"User asked AI: {user_question}")

    # Твоя функция для Hugging Face 
    async def ask_hf_model(prompt_text):
        async with aiohttp.ClientSession() as session:
            API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"  # Поставь свою модель
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            payload = {"inputs": prompt_text}
            async with session.post(API_URL, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"Hugging Face API error: {resp.status}")
                data = await resp.json()
                # Формат ответа зависит от модели
                if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                    return data[0]["generated_text"]
                return str(data)

    try:
        response = await ask_hf_model(prompt)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Kļūda AI atbildē: {e}")
        await update.message.reply_text(get_text("not_found", lang))

    return CHOOSE_REPEAT

def main():
    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_PEOPLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_people)],
            CHOOSE_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_genre)],
            CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            CHOOSE_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_rating)],
            CHOOSE_REPEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_repeat)],
            WAITING_QUESTION: [MessageHandler(filters.TEXT & waiting_for_ai_filter, handle_ai_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("language", set_language))
    app.add_handler(CommandHandler("history", history))

    app.add_handler(CallbackQueryHandler(button_callback))

    print("Meowie ieskrējis čatā!")
    app.run_polling()

if __name__ == "__main__":
    main()
