from plexapi.server import PlexServer
import os
import re
from functools import lru_cache
from config import Config

# Cache the Plex connection
plex_server = None

def get_plex_server():
    """Get cached Plex server connection"""
    global plex_server
    if plex_server is None:
        plex_server = PlexServer(Config.PLEX_URL, Config.PLEX_TOKEN)
    return plex_server

def normalize_title(title):
    """Normalize title for better matching"""
    # Remove special characters and convert to lowercase
    normalized = re.sub(r'[^\w\s]', '', title.lower())
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    return normalized

def calculate_similarity(search_title, movie_title):
    """Calculate similarity between search title and movie title"""
    search_norm = normalize_title(search_title)
    movie_norm = normalize_title(movie_title)
    
    # Exact match gets highest priority
    if search_norm == movie_norm:
        return 1.0
    
    # Check if search title is a complete word/phrase within movie title
    # This handles cases like "Home" matching "Home Alone" but not "Homeward Bound"
    search_words = search_norm.split()
    movie_words = movie_norm.split()
    
    # If search is a single word, check if it's the first word of the movie
    if len(search_words) == 1:
        if movie_words and search_words[0] == movie_words[0]:
            # Bonus for being the first word
            return 0.9
        elif search_words[0] in movie_words:
            # Word exists but not first - lower score
            return 0.6
    
    # If search is multiple words, check for phrase matching
    if len(search_words) > 1:
        search_phrase = ' '.join(search_words)
        if search_phrase in movie_norm:
            return 0.8
    
    # Check for word overlap with Jaccard similarity
    search_word_set = set(search_words)
    movie_word_set = set(movie_words)
    
    if not search_word_set or not movie_word_set:
        return 0.0
    
    intersection = search_word_set.intersection(movie_word_set)
    union = search_word_set.union(movie_word_set)
    
    # Calculate Jaccard similarity
    jaccard = len(intersection) / len(union) if union else 0.0
    
    # Apply penalties for partial matches
    if jaccard > 0:
        # Penalize if movie title is much longer than search
        length_ratio = len(search_words) / len(movie_words)
        if length_ratio < 0.5:  # Search is much shorter than movie title
            jaccard *= 0.7
        
        # Penalize if search words are not at the beginning
        if search_words[0] not in movie_words[:2]:
            jaccard *= 0.8
    
    return jaccard

def movie_exists(title):
    try:
        plex = get_plex_server()
        library = plex.library.section(Config.PLEX_LIBRARY_NAME)
        results = library.search(title, libtype='movie')

        if not results:
            return []

        # Score and filter results
        scored_movies = []

        for movie in results:
            # Calculate similarity score
            similarity = calculate_similarity(title, movie.title)

            # Only include movies with reasonable similarity
            if similarity >= Config.MIN_SIMILARITY_THRESHOLD:
                scored_movies.append({
                    'movie': movie,
                    'similarity': similarity,
                    'title': movie.title,
                    'year': movie.year,
                    'summary': movie.summary
                })

        # Sort by similarity score (highest first)
        scored_movies.sort(key=lambda x: x['similarity'], reverse=True)

        # Return top matches
        return [item for item in scored_movies[:Config.MAX_SEARCH_RESULTS]]

    except Exception as e:
        print(f"[PLEX ERROR] {e}")
        return []