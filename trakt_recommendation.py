import os
import random
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("trakt_recommendation")

TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")

if not TRAKT_CLIENT_ID:
    raise ValueError("TRAKT_CLIENT_ID nav definēts .env failā")

HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
}

def get_random_movie_by_genre(genre, people_type="Viens"):
    try:
        url = f"https://api.trakt.tv/movies/popular?genres={genre}&limit=50&extended=full"
        response = httpx.get(url, headers=HEADERS)
        response.raise_for_status()

        movies = response.json()
        if not movies:
            return None

        movie = random.choice(movies)

        trakt_url = f"https://trakt.tv/movies/{movie['ids']['slug']}"
        genres = ', '.join(movie.get("genres", [])) or genre.capitalize()

        return {
            "title": movie.get("title"),
            "year": movie.get("year"),
            "genres": genres,
            "overview": movie.get("overview", "Apraksts nav pieejams."),
            "trakt_url": trakt_url,
        }

    except Exception as e:
        logger.error(f"Kļūda trakt API: {e}")
        return None
