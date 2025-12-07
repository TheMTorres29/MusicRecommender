"""
Music Recommendation System using Spotify API
This program asks what you're currently listening to and recommends similar songs.
"""

import os
import warnings
import logging
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
    SEARCH_LIMIT = 5
    GENRE_ARTIST_LIMIT = 50
    MAX_GENRES = 3
    COUNTRY_CODE = 'US'
    
    def __init__(self) -> None:
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
    
    def search_track(self, query: str):
        """Search for a track on Spotify and let user select from results"""
        results = self.sp.search(q=query, type='track', limit=self.SEARCH_LIMIT)
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
    
    def _get_user_track_choice(self, tracks: list):
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
    
    def get_recommendations(self, track_id: str, limit: int = 10, exclude_track_ids: set = None) -> list:
        """Get recommendations based on a seed track with fallback strategies"""
        if exclude_track_ids is None:
            exclude_track_ids = set()
        
        track_info = self._fetch_track_with_retry(track_id)
        
        if not track_info:
            raise Exception("Failed to fetch track info")
        
        # Get the original artist to filter duplicates
        original_artist_ids = [artist['id'] for artist in track_info.get('artists', [])]
        
        # First, try to get any recommendations at all
        all_tracks = []
        strategies = [
            ('related-artists', self._try_related_artists_tracks),  # Try this FIRST for diversity
            ('track-based', self._try_track_recommendations),
            ('artist-based', self._try_artist_recommendations)
        ]
        
        for strategy_name, strategy in strategies:
            try:
                tracks = strategy(track_info, track_id, 50)  # Request 50 tracks for better filtering
                if tracks and len(tracks) >= limit:
                    all_tracks = tracks
                    break  # Use first successful strategy with enough tracks
            except Exception as e:
                continue
        
        if not all_tracks:
            return []
        
        # Filter out tracks we've already shown
        all_tracks = [t for t in all_tracks if t['id'] not in exclude_track_ids]
        
        if not all_tracks:
            return []
        
        # Filter to get one track per artist, excluding original artist
        filtered = self._filter_diverse_artists(
            all_tracks, 
            original_artist_ids, 
            limit,
            max_per_artist=1
        )
        
        # Return whatever we got (should be 10 diverse tracks)
        return filtered[:limit] if len(filtered) >= limit else filtered
    
    def _fetch_track_with_retry(self, track_id: str):
        """Fetch track info with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                return self.sp.track(track_id)
            except Exception as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
        return None
    
    def _try_track_recommendations(self, track_info, track_id, limit):
        """Try getting recommendations using track as seed"""
        try:
            return self.sp.recommendations(seed_tracks=[track_id], limit=min(limit, 20)).get('tracks', [])
        except Exception:
            # If recommendations endpoint fails, use artist's top tracks instead
            return []
    
    def _try_artist_recommendations(self, track_info, track_id, limit):
        """Try getting recommendations using artist as seed"""
        artists = track_info.get('artists', [])
        if artists:
            artist_id = artists[0].get('id')
            try:
                return self.sp.recommendations(seed_artists=[artist_id], limit=min(limit, 20)).get('tracks', [])
            except Exception:
                # Fallback to artist top tracks if recommendations fail
                try:
                    top = self.sp.artist_top_tracks(artist_id, country=self.COUNTRY_CODE)
                    return top.get('tracks', [])[:limit]
                except Exception:
                    return []
        return []
    
    def _try_related_artists_tracks(self, track_info: dict, track_id: str, limit: int) -> list:
        """Get tracks from related artists for more diversity"""
        artists = track_info.get('artists', [])
        if not artists:
            return []
        
        artist_id = artists[0]['id']
        
        try:
            artist_info = self.sp.artist(artist_id)
            genres = artist_info.get('genres', [])
            
            # Try the related-artists endpoint first
            try:
                related = self.sp.artist_related_artists(artist_id)
                related_artists = related.get('artists', [])
            except Exception:
                # Fallback: Search for artists in the same genre(s)
                related_artists = self._find_artists_by_genres(genres, artist_id, limit)
            
            # Get top track from each related artist
            return self._collect_tracks_from_artists(related_artists, limit)
        except Exception:
            return []
    
    def _find_artists_by_genres(self, genres: list, exclude_artist_id: str, limit: int) -> list:
        """Search for artists by genre"""
        if not genres:
            return []
        
        related_artists = []
        seen_artist_ids = {exclude_artist_id}
        
        for genre in genres[:self.MAX_GENRES]:
            try:
                results = self.sp.search(q=genre, type='artist', limit=self.GENRE_ARTIST_LIMIT)
                found_artists = results.get('artists', {}).get('items', [])
                
                for artist in found_artists:
                    if artist['id'] not in seen_artist_ids:
                        related_artists.append(artist)
                        seen_artist_ids.add(artist['id'])
                
                if len(related_artists) >= limit * 2:
                    break
            except Exception:
                continue
        
        return related_artists
    
    def _collect_tracks_from_artists(self, artists: list, limit: int) -> list:
        """Collect one top track from each artist"""
        tracks = []
        for artist in artists[:limit]:
            try:
                top_tracks = self.sp.artist_top_tracks(artist['id'], country=self.COUNTRY_CODE)
                artist_tracks = top_tracks.get('tracks', [])
                if artist_tracks:
                    tracks.append(artist_tracks[0])
                if len(tracks) >= limit:
                    break
            except Exception:
                continue
        return tracks
    
    def _filter_diverse_artists(self, tracks: list, original_artist_ids: list, limit: int, max_per_artist: int = 2) -> list:
        """Filter tracks to ensure artist diversity"""
        filtered = []
        artist_count = {}
        original_artist_names = set()
        
        # Track original artist names to exclude them
        for track in tracks:
            for artist in track.get('artists', []):
                if artist['id'] in original_artist_ids:
                    original_artist_names.add(artist['name'])
        
        for track in tracks:
            # Get all artist names for this track
            track_artist_names = {artist['name'] for artist in track.get('artists', [])}
            track_artist_ids = [artist['id'] for artist in track.get('artists', [])]
            
            # Skip if this is the original artist(s)
            if any(artist_id in original_artist_ids for artist_id in track_artist_ids):
                continue
            
            # Check if any artist has reached the limit
            can_add = True
            for artist in track.get('artists', []):
                artist_name = artist['name']
                if artist_count.get(artist_name, 0) >= max_per_artist:
                    can_add = False
                    break
            
            if can_add:
                filtered.append(track)
                # Increment count for all artists on this track
                for artist in track.get('artists', []):
                    artist_name = artist['name']
                    artist_count[artist_name] = artist_count.get(artist_name, 0) + 1
                
                if len(filtered) >= limit:
                    break
        
        return filtered
    
    def display_recommendations(self, recommendations: list) -> None:
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
            
            # Track shown recommendations to avoid duplicates
            shown_track_ids = set()
            
            # Get and display recommendations
            while True:
                print("\nFinding similar tracks...")
                recommendations = self.get_recommendations(
                    track['id'], 
                    limit=10,
                    exclude_track_ids=shown_track_ids
                )
                
                if recommendations:
                    self.display_recommendations(recommendations)
                    # Track what we've shown
                    shown_track_ids.update(rec['id'] for rec in recommendations)
                else:
                    print("Sorry, couldn't find recommendations for this track.")
                    break
                
                # Ask if they want 10 more
                print("\n" + "-" * 60)
                choice = input("\nWould you like 10 MORE recommendations? (yes/no): ").strip().lower()
                if choice not in {'yes', 'y', 'yeah', 'yep'}:
                    break
            
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