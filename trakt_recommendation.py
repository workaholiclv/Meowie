import os
import logging
import httpx
import random

logger = logging.getLogger("trakt_recommendation")

TRAKT_CLIENT_ID = os.getenv("TRAKT_CLIENT_ID")
if not TRAKT_CLIENT_ID:
    raise ValueError("TRAKT_CLIENT_ID nav definēts Railway vidē")

HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-version": "2",
    "trakt-api-key": TRAKT_CLIENT_ID,
}

async def get_movies_by_genre_and_people(genre, people_type="Viens"):
    """
    Получаем список популярных фильмов по жанру.
    people_type — пока не используется, но можно расширить логику.
    Возвращаем список словарей с ключами: title, year, genres, overview, trakt_url, rating
    """
    try:
        url = f"https://api.trakt.tv/movies/popular?genres={genre}&limit=50&extended=full"
        response = httpx.get(url, headers=HEADERS)
        response.raise_for_status()

        movies = response.json()
        if not movies:
            return []

        result = []
        for movie in movies:
            trakt_url = f"https://trakt.tv/movies/{movie['ids']['slug']}"
            genres_list = movie.get("genres", [])
            genres = ', '.join([g['name'] if isinstance(g, dict) else g for g in genres_list]) or genre.capitalize()

            # Некоторые фильмы могут не иметь рейтинга, поставим 0
            rating = movie.get("rating", 0)

            result.append({
                "title": movie.get("title"),
                "year": movie.get("year"),
                "genres": genres,
                "overview": movie.get("overview", "Apraksts nav pieejams."),
                "trakt_url": trakt_url,
                "rating": rating,
                # Можно добавить и другие поля, если нужно
            })

        return result

    except Exception as e:
        logger.error(f"Kļūda trakt API: {e}")
        return []
