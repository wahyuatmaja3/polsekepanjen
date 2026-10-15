from __future__ import annotations

import os

# Spotify Config
# SPOTIFY_CLIENT_ID & SPOTIFY_CLIENT_SECRET are used for Client Credentials Flow (App-to-App, NO user login!)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "1adea15807d4408d873742491b8a021d")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
# Optional: Bot / Master account refresh token for auto-creating public Spotify playlists without user login
SPOTIFY_BOT_REFRESH_TOKEN = os.getenv("SPOTIFY_BOT_REFRESH_TOKEN", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SPOTIFY_SCOPE = os.getenv("SPOTIFY_SCOPE", "playlist-modify-public playlist-modify-private")

# YouTube Music Config (No credentials needed for instant playlists / queue)
YTMUSIC_PLAYLIST_NAME_TEMPLATE = "Music of @{username}"
YTMUSIC_PLAYLIST_DESCRIPTION = "Generated automatically by polsekepanjen"

# Instagram Config
INSTAGRAM_SESSION_ID = os.getenv("INSTAGRAM_SESSION_ID", "")
SCRAPE_DELAY_SECONDS = float(os.getenv("SCRAPE_DELAY_SECONDS", "1.5"))

# General App Config
PLAYLIST_NAME_TEMPLATE = "Music of @{username}"
PLAYLIST_DESCRIPTION = "Curated from Instagram by polsekepanjen"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
