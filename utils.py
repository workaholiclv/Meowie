import random

GENRE_MAP = {
    "😂": "Komēdija",
    "🔪": "Trilleris",
    "💘": "Romantika",
    "🛸": "Zinātniskā fantastika",
    "🎭": "Drāma",
    "👻": "Šausmu",
    "🧙‍♂️": "Fantāzija",
    "🎸": "Mūzikls"
}

def get_movie_suggestion(user_data):
    genre = GENRE_MAP.get(user_data["genre"], "Filma")
    dummy_movies = [
        {
            "title": "Interstellar",
            "desc": "Zinātniskās fantastikas ceļojums laikā un telpā.",
            "link": "https://www.netflix.com/title/70305903"
        },
        {
            "title": "La La Land",
            "desc": "Romantisks mūzikls ar spilgtu estētiku.",
            "link": "https://www.viaplay.lv"
        },
        {
            "title": "Get Out",
            "desc": "Šausmu un psiholoģiskais trilleris ar negaidītiem pavērsieniem.",
            "link": "https://www.justwatch.com/lv"
        }
    ]
    selected = random.choice(dummy_movies)
    return f"📌 *{selected['title']}* ({genre})
_{selected['desc']}_
🔗 {selected['link']}"
