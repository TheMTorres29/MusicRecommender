# 🎵 Music Recommendation System

A Python CLI app that discovers new music based on what you're currently listening to, powered by Spotify's API.

## Features

- 🔍 Search for tracks by song name or artist
- 🎯 Get 10 personalized recommendations instantly
- 🎵 Direct Spotify links to listen immediately
- ⚡ Smart fallback system (always returns results)
- 🔄 Automatic retry on network issues

## Setup

### Prerequisites
- Python 3.8+
- Spotify Developer Account (free)

### Installation

1. **Clone and install dependencies**
   ```bash
   git clone https://github.com/yourusername/music-recommender.git
   cd music-recommender
   pip install -r requirements.txt
   ```

2. **Get Spotify API credentials**
   - Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create an app and copy your Client ID & Client Secret

3. **Configure credentials**
   ```bash
   cp .env.example .env
   # Edit .env and add your Spotify credentials
   ```

4. **Run**
   ```bash
   python music_recommender.py
   ```

## Usage

```
What are you listening to right now? bohemian rhapsody

Search Results:
1. Bohemian Rhapsody by Queen
2. Bohemian Rhapsody - Remastered by Queen

Select a track number: 1

✓ Selected: Bohemian Rhapsody by Queen

Finding similar tracks...

🎵 RECOMMENDED TRACKS FOR YOU 🎵
1. Don't Stop Me Now - Queen
2. We Will Rock You - Queen
[... 8 more tracks with Spotify links ...]
```

## Tech Stack

- **[Spotipy](https://spotipy.readthedocs.io/)** - Spotify API wrapper
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** - Environment management

## Troubleshooting

**"No module named 'spotipy'"**  
→ Run `pip install -r requirements.txt`

**"Please set SPOTIFY_CLIENT_ID..."**  
→ Check your `.env` file has correct credentials

**Timeout errors**  
→ Check internet connection; app auto-retries 3 times

## License

MIT License - feel free to use and modify!

---

⭐ Made with Python and Spotify API
