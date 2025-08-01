import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plex_utils import normalize_title, calculate_similarity, movie_exists, get_plex_server
from config import Config

class TestPlexUtils(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables for testing
        self.env_patcher = patch.dict(os.environ, {
            'PLEX_URL': 'http://test.plex.server',
            'PLEX_TOKEN': 'test_token',
            'PLEX_LIBRARY_NAME': 'Test Library'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    def test_normalize_title(self):
        """Test title normalization"""
        test_cases = [
            ("The Dark Knight", "the dark knight"),
            ("Iron Man 2", "iron man 2"),
            ("Spider-Man: Homecoming", "spiderman homecoming"),
            ("   Avengers: Endgame   ", "avengers endgame"),
            ("Mission: Impossible - Fallout", "mission impossible fallout"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = normalize_title(input_title)
                self.assertEqual(result, expected)
    
    def test_calculate_similarity_exact_match(self):
        """Test exact match similarity"""
        similarity = calculate_similarity("The Dark Knight", "The Dark Knight")
        self.assertEqual(similarity, 1.0)
    
    def test_calculate_similarity_first_word_match(self):
        """Test first word match similarity"""
        similarity = calculate_similarity("Home", "Home Alone")
        self.assertEqual(similarity, 0.9)
    
    def test_calculate_similarity_word_in_title(self):
        """Test word contained in title"""
        similarity = calculate_similarity("Batman", "The Dark Knight Batman")
        self.assertEqual(similarity, 0.6)
    
    def test_calculate_similarity_phrase_match(self):
        """Test phrase matching"""
        similarity = calculate_similarity("Dark Knight", "The Dark Knight")
        self.assertEqual(similarity, 0.8)
    
    def test_calculate_similarity_no_match(self):
        """Test no similarity"""
        similarity = calculate_similarity("Batman", "Iron Man")
        self.assertLess(similarity, 0.5)
    
    def test_calculate_similarity_jaccard(self):
        """Test Jaccard similarity calculation"""
        similarity = calculate_similarity("Iron Man", "Iron Man 2")
        self.assertGreater(similarity, 0.0)
        self.assertLessEqual(similarity, 1.0)
    
    @patch('plex_utils.PlexServer')
    def test_get_plex_server_caching(self, mock_plex_server):
        """Test that Plex server connection is cached"""
        # Reset the global variable
        import plex_utils
        plex_utils.plex_server = None
        
        # First call should create connection
        server1 = get_plex_server()
        mock_plex_server.assert_called_once()
        
        # Second call should return cached connection
        server2 = get_plex_server()
        mock_plex_server.assert_called_once()  # Should not be called again
        
        self.assertEqual(server1, server2)
    
    @patch('plex_utils.get_plex_server')
    def test_movie_exists_success(self, mock_get_server):
        """Test successful movie search"""
        # Mock the Plex server and library
        mock_server = Mock()
        mock_library = Mock()
        mock_movie = Mock()
        mock_movie.title = "The Dark Knight"
        mock_movie.year = 2008
        mock_movie.summary = "A test movie"
        
        mock_library.search.return_value = [mock_movie]
        mock_server.library.section.return_value = mock_library
        mock_get_server.return_value = mock_server
        
        # Test the function
        results = movie_exists("Dark Knight")
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "The Dark Knight")
        self.assertEqual(results[0]['year'], 2008)
        self.assertEqual(results[0]['summary'], "A test movie")
        self.assertIn('similarity', results[0])
    
    @patch('plex_utils.get_plex_server')
    def test_movie_exists_no_results(self, mock_get_server):
        """Test movie search with no results"""
        # Mock empty results
        mock_server = Mock()
        mock_library = Mock()
        mock_library.search.return_value = []
        mock_server.library.section.return_value = mock_library
        mock_get_server.return_value = mock_server
        
        results = movie_exists("Non Existent Movie")
        self.assertEqual(results, [])
    
    @patch('plex_utils.get_plex_server')
    def test_movie_exists_exception_handling(self, mock_get_server):
        """Test exception handling in movie_exists"""
        # Mock an exception
        mock_get_server.side_effect = Exception("Connection failed")
        
        results = movie_exists("Test Movie")
        self.assertEqual(results, [])

class TestConfig(unittest.TestCase):
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test with missing environment variables
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(Config.validate())
            missing_vars = Config.get_missing_vars()
            self.assertIn("DISCORD_TOKEN", missing_vars)
            self.assertIn("PLEX_URL", missing_vars)
    
    def test_config_with_valid_env(self):
        """Test configuration with valid environment variables"""
        with patch.dict(os.environ, {
            'DISCORD_TOKEN': 'test_token',
            'GUILD_ID': '123456789',
            'USER_ID': '987654321',
            'PLEX_URL': 'http://test.plex.server',
            'PLEX_TOKEN': 'test_plex_token'
        }):
            self.assertTrue(Config.validate())
            missing_vars = Config.get_missing_vars()
            self.assertEqual(len(missing_vars), 0)

if __name__ == '__main__':
    unittest.main() 