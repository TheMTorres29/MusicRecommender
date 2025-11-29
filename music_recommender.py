"""
Music Recommendation System using Spotify API
This program asks what you're currently listening to and recommends similar songs.
"""

import os
import warnings
import logging
import time
from dotenv import load_dotenv

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    import requests
except ModuleNotFoundError:
    print("❌ The 'spotipy' package is not installed in the Python interpreter you're using.")
    print()
    print("If you use the project's virtual environment, activate it in PowerShell:")
    print(r"    .\\venv\\Scripts\\Activate.ps1")
    print()
    print("Or run the script directly with the project's Python executable:")
    print(r"    E:/Projects/2025/Python/MusicRecommender/.venv/Scripts/python.exe music_recommender.py")
    print()
    print("After activating the venv, install dependencies if needed:")
    print(r"    pip install -r requirements.txt")
    raise

# Load environment variables from .env file
load_dotenv()

# Suppress warnings and excessive logging
warnings.filterwarnings('ignore', category=DeprecationWarning)
logging.getLogger('spotipy').setLevel(logging.CRITICAL)


class MusicRecommender:
    """Spotify-based music recommendation system"""
    
    MAX_RETRIES = 3
    TIMEOUT = 30
    
    def __init__(self):
        """Initialize Spotify client with credentials"""
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError(
                "Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.\n"
                "Get credentials at: https://developer.spotify.com/dashboard"
            )
        
        # Authenticate with Spotify
        auth_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        self.sp = spotipy.Spotify(
            client_credentials_manager=auth_manager,
            requests_timeout=self.TIMEOUT,
            retries=self.MAX_RETRIES
        )
    
    def search_track(self, query):
        """Search for a track on Spotify and let user select from results"""
        results = self.sp.search(q=query, type='track', limit=5)
        tracks = results['tracks']['items']
        
        if not tracks:
            return None
        
        # Display search results
        print("\nSearch Results:")
        for i, track in enumerate(tracks, 1):
            artists = ', '.join(artist['name'] for artist in track['artists'])
            print(f"{i}. {track['name']} by {artists}")
        
        # Let user choose
        return self._get_user_track_choice(tracks)
    
    def _get_user_track_choice(self, tracks):
        """Get user's track selection from search results"""
        while True:
            try:
                choice = input("\nSelect a track number (or 0 to search again): ")
                choice = int(choice)
                if choice == 0:
                    return None
                if 1 <= choice <= len(tracks):
                    return tracks[choice - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
            except (KeyboardInterrupt, EOFError):
                return None
    
    def get_recommendations(self, track_id, limit=10):
        """Get recommendations based on a seed track with fallback strategies"""
        track_info = self._fetch_track_with_retry(track_id)
        
        if not track_info:
            raise Exception("Failed to fetch track info")
        
        # Try multiple strategies to get recommendations
        strategies = [
            self._try_track_recommendations,
            self._try_artist_recommendations,
            self._try_artist_top_tracks
        ]
        
        for strategy in strategies:
            try:
                tracks = strategy(track_info, track_id, limit)
                if tracks:
                    return tracks
            except Exception:
                continue
        
        return []
    
    def _fetch_track_with_retry(self, track_id):
        """Fetch track info with exponential backoff retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return self.sp.track(track_id)
            except Exception as e:
                if 'timeout' in str(e).lower() and attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # exponential backoff: 1s, 2s, 4s
                elif attempt == self.MAX_RETRIES - 1:
                    raise
                else:
                    raise
        return None
    
    def _try_track_recommendations(self, track_info, track_id, limit):
        """Try getting recommendations using track as seed"""
        return self.sp.recommendations(seed_tracks=[track_id], limit=limit).get('tracks', [])
    
    def _try_artist_recommendations(self, track_info, track_id, limit):
        """Try getting recommendations using artist as seed"""
        artists = track_info.get('artists', [])
        if artists:
            artist_id = artists[0].get('id')
            return self.sp.recommendations(seed_artists=[artist_id], limit=limit).get('tracks', [])
        return []
    
    def _try_artist_top_tracks(self, track_info, track_id, limit):
        """Fallback to artist's top tracks"""
        artists = track_info.get('artists', [])
        if artists:
            artist_id = artists[0].get('id')
            top_tracks = self.sp.artist_top_tracks(artist_id, country='US')
            return top_tracks.get('tracks', [])[:limit]
        return []
    
    def display_recommendations(self, recommendations):
        """Display recommended tracks in a formatted list"""
        print("\n" + "=" * 60)
        print("🎵 RECOMMENDED TRACKS FOR YOU 🎵")
        print("=" * 60)
        
        for i, track in enumerate(recommendations, 1):
            artists = ', '.join(artist['name'] for artist in track['artists'])
            album = track['album']['name']
            external_url = track['external_urls']['spotify']
            
            print(f"\n{i}. {track['name']}")
            print(f"   Artist(s): {artists}")
            print(f"   Album: {album}")
            print(f"   Listen: {external_url}")
    
    def run(self):
        """Main program loop"""
        self._print_welcome()
        
        while True:
            query = self._get_user_query()
            if not query:
                continue
            
            track = self.search_track(query)
            if not track:
                continue
            
            self._display_selected_track(track)
            
            print("\nFinding similar tracks...")
            recommendations = self.get_recommendations(track['id'], limit=10)
            
            if recommendations:
                self.display_recommendations(recommendations)
            else:
                print("Sorry, couldn't find recommendations for this track.")
            
            if not self._should_continue():
                print("\nThanks for using Music Recommender! 🎵")
                break
    
    def _print_welcome(self):
        """Print welcome message"""
        print("=" * 60)
        print("🎵 MUSIC RECOMMENDATION SYSTEM 🎵")
        print("=" * 60)
        print("Get personalized music recommendations based on what you're listening to!")
    
    def _get_user_query(self):
        """Get search query from user"""
        print("\n" + "-" * 60)
        query = input("\nWhat are you listening to right now? (song name and/or artist): ").strip()
        if not query:
            print("Please enter a song or artist name.")
        return query
    
    def _display_selected_track(self, track):
        """Display the selected track"""
        artists = ', '.join(artist['name'] for artist in track['artists'])
        print(f"\n✓ Selected: {track['name']} by {artists}")
    
    def _should_continue(self):
        """Ask user if they want another recommendation"""
        print("\n" + "-" * 60)
        choice = input("\nWould you like another recommendation? (yes/no): ").strip().lower()
        return choice in {'yes', 'y', 'yeah', 'yep'}


def main():
    """Entry point for the music recommender application"""
    try:
        recommender = MusicRecommender()
        recommender.run()
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
    except KeyboardInterrupt:
        print("\n\nThanks for using Music Recommender! 🎵")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")


if __name__ == "__main__":
    main()