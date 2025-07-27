from plexapi.server import PlexServer
import os
import re

PLEX_URL = os.getenv("PLEX_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")

def movie_exists(title):
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN)
        library = plex.library.section("Library of Congress")
        results = library.search(title, libtype='movie')

        # Filter movies for exact titles matches
        matching_movies = [
            {
                'title': movie.title,
                'year': movie.year,
                'summary': movie.summary
            }
            for movie, in results if movie.title.lower() == title.lower()
        ]
        return matching_movies
    except Exception as e:
        print(f"[PLEX ERROR] {e}")
        return []