import os
import httpx
import logging

logger = logging.getLogger(__name__)

TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")

def get_random_movie_by_genre(genre, people):
    url = f"https://api.trakt.tv/movies/popular?genres={genre}&limit=50&extended=full"

    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID
    }

    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        movies = response.json()

        # тут выбираем фильм, форматируем и возвращаем
        if not movies:
            return None

        chosen = random.choice(movies)
        return {
            "title": chosen.get("title"),
            "year": chosen.get("year"),
            "overview": chosen.get("overview", ""),
            "genres": genre,
            "trakt_url": f"https://trakt.tv/movies/{chosen.get('ids', {}).get('slug', '')}"
        }

    except Exception as e:
        logger.error(f"Kļūda trakt API: {e}")
        return None
