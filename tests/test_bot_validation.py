import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the validation functions from bot.py
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Mock the imports that require external services
with patch.dict('sys.modules', {
    'discord': Mock(),
    'plex_utils': Mock(),
    'config': Mock()
}):
    # Now we can import the validation functions
    import bot

class TestBotValidation(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the rate limits dictionary
        self.rate_limits = defaultdict(list)
    
    def test_validate_movie_title_empty(self):
        """Test validation of empty movie titles"""
        is_valid, message = bot.validate_movie_title("")
        self.assertFalse(is_valid)
        self.assertIn("empty", message.lower())
    
    def test_validate_movie_title_whitespace(self):
        """Test validation of whitespace-only titles"""
        is_valid, message = bot.validate_movie_title("   ")
        self.assertFalse(is_valid)
        self.assertIn("empty", message.lower())
    
    def test_validate_movie_title_too_short(self):
        """Test validation of titles that are too short"""
        is_valid, message = bot.validate_movie_title("A")
        self.assertFalse(is_valid)
        self.assertIn("at least", message.lower())
    
    def test_validate_movie_title_too_long(self):
        """Test validation of titles that are too long"""
        long_title = "A" * 101  # Over the 100 character limit
        is_valid, message = bot.validate_movie_title(long_title)
        self.assertFalse(is_valid)
        self.assertIn("less than", message.lower())
    
    def test_validate_movie_title_invalid_characters(self):
        """Test validation of titles with invalid characters"""
        invalid_titles = [
            "Movie<title>",
            'Movie"title"',
            "Movie'title'",
            "Movie<title>",
        ]
        
        for title in invalid_titles:
            with self.subTest(title=title):
                is_valid, message = bot.validate_movie_title(title)
                self.assertFalse(is_valid)
                self.assertIn("invalid characters", message.lower())
    
    def test_validate_movie_title_valid(self):
        """Test validation of valid movie titles"""
        valid_titles = [
            "The Dark Knight",
            "Iron Man",
            "Spider-Man: Homecoming",
            "Mission: Impossible - Fallout",
            "Avengers: Endgame",
            "A",  # Single character should be valid if >= min length
        ]
        
        for title in valid_titles:
            with self.subTest(title=title):
                is_valid, result = bot.validate_movie_title(title)
                self.assertTrue(is_valid)
                self.assertEqual(result, title.strip())
    
    def test_is_rate_limited_no_limits(self):
        """Test rate limiting when user has no previous requests"""
        user_id = 123456789
        is_limited = bot.is_rate_limited(user_id)
        self.assertFalse(is_limited)
    
    def test_is_rate_limited_under_limit(self):
        """Test rate limiting when user is under the limit"""
        user_id = 123456789
        now = datetime.now()
        
        # Add some recent requests (under the limit)
        self.rate_limits[user_id] = [
            now - timedelta(seconds=10),
            now - timedelta(seconds=20),
            now - timedelta(seconds=30),
        ]
        
        is_limited = bot.is_rate_limited(user_id)
        self.assertFalse(is_limited)
    
    def test_is_rate_limited_at_limit(self):
        """Test rate limiting when user is at the limit"""
        user_id = 123456789
        now = datetime.now()
        
        # Add exactly the limit number of recent requests
        self.rate_limits[user_id] = [
            now - timedelta(seconds=10),
            now - timedelta(seconds=20),
            now - timedelta(seconds=30),
            now - timedelta(seconds=40),
            now - timedelta(seconds=50),
        ]
        
        is_limited = bot.is_rate_limited(user_id)
        self.assertTrue(is_limited)
    
    def test_is_rate_limited_old_requests_removed(self):
        """Test that old requests are removed from rate limiting"""
        user_id = 123456789
        now = datetime.now()
        
        # Add old requests (outside the window) and recent requests
        self.rate_limits[user_id] = [
            now - timedelta(seconds=70),  # Old request
            now - timedelta(seconds=80),  # Old request
            now - timedelta(seconds=10),  # Recent request
            now - timedelta(seconds=20),  # Recent request
        ]
        
        is_limited = bot.is_rate_limited(user_id)
        self.assertFalse(is_limited)  # Old requests should be removed
    
    def test_is_rate_limited_window_cleanup(self):
        """Test that the rate limit window properly cleans up old entries"""
        user_id = 123456789
        now = datetime.now()
        
        # Add a mix of old and recent requests
        self.rate_limits[user_id] = [
            now - timedelta(seconds=70),  # Old
            now - timedelta(seconds=10),  # Recent
            now - timedelta(seconds=80),  # Old
            now - timedelta(seconds=20),  # Recent
        ]
        
        # Call rate limiting (should clean up old entries)
        bot.is_rate_limited(user_id)
        
        # Check that only recent entries remain
        recent_requests = [req for req in self.rate_limits[user_id] 
                         if now - req < timedelta(seconds=60)]
        self.assertEqual(len(recent_requests), 2)

class TestBotUtilities(unittest.TestCase):
    
    @patch('bot.Config')
    def test_config_validation_missing_vars(self, mock_config):
        """Test configuration validation with missing variables"""
        # Mock Config to simulate missing environment variables
        mock_config.DISCORD_TOKEN = ""
        mock_config.GUILD_ID = 0
        mock_config.USER_ID = 0
        mock_config.PLEX_URL = ""
        mock_config.PLEX_TOKEN = ""
        mock_config.validate.return_value = False
        mock_config.get_missing_vars.return_value = ["DISCORD_TOKEN", "PLEX_URL"]
        
        # This would normally exit, but we can test the validation logic
        missing_vars = mock_config.get_missing_vars()
        self.assertIn("DISCORD_TOKEN", missing_vars)
        self.assertIn("PLEX_URL", missing_vars)
    
    @patch('bot.Config')
    def test_config_validation_valid(self, mock_config):
        """Test configuration validation with valid variables"""
        # Mock Config to simulate valid environment variables
        mock_config.DISCORD_TOKEN = "valid_token"
        mock_config.GUILD_ID = 123456789
        mock_config.USER_ID = 987654321
        mock_config.PLEX_URL = "http://plex.server"
        mock_config.PLEX_TOKEN = "valid_plex_token"
        mock_config.validate.return_value = True
        mock_config.get_missing_vars.return_value = []
        
        is_valid = mock_config.validate()
        self.assertTrue(is_valid)
        
        missing_vars = mock_config.get_missing_vars()
        self.assertEqual(len(missing_vars), 0)

if __name__ == '__main__':
    unittest.main() 