from __future__ import annotations

import logging
import urllib.parse as up
from typing import Iterable
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from config.settings import (
    PLAYLIST_DESCRIPTION,
    PLAYLIST_NAME_TEMPLATE,
    SPOTIFY_BOT_REFRESH_TOKEN,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPE,
)
from core.models import Song

logger = logging.getLogger(__name__)


class SpotifyClientError(Exception):
    pass


class SpotifyManager:
    """Manages Spotify track discovery and playlist generation WITHOUT requiring the end-user to log in.

    Modes:
    1. Bot/Curator Account Mode: If SPOTIFY_BOT_REFRESH_TOKEN + SPOTIFY_CLIENT_SECRET are set,
       the app automatically creates a real public Spotify playlist using a backend/curator bot account.
       The end user receives a public playlist link and does not need to log in!
    2. Client Credentials Flow: If only Client ID + Secret are set, searches Spotify's catalog (0 user login).
    3. Universal Free Metadata Fallback: Uses iTunes Search API (0 credentials, 0 login) for covers & audio previews,
       and builds direct Spotify search and playback links.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        bot_refresh_token: str | None = None,
    ) -> None:
        self.client_id = (client_id or SPOTIFY_CLIENT_ID or "").strip()
        self.client_secret = (client_secret or SPOTIFY_CLIENT_SECRET or "").strip()
        self.bot_refresh_token = (bot_refresh_token or SPOTIFY_BOT_REFRESH_TOKEN or "").strip()

        self.sp_client: spotipy.Spotify | None = None
        self.sp_bot: spotipy.Spotify | None = None

        self._init_spotify_clients()

    def _init_spotify_clients(self) -> None:
        # Initialize Client Credentials client if credentials are provided (App-to-App, no user login)
        if self.client_id and self.client_secret:
            try:
                auth_creds = SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
                self.sp_client = spotipy.Spotify(auth_manager=auth_creds)
            except Exception as exc:
                logger.warning(f"Could not init Spotify Client Credentials: {exc}")

        # Initialize Bot/Curator client if bot refresh token is provided
        if self.client_id and self.client_secret and self.bot_refresh_token:
            try:
                auth_oauth = SpotifyOAuth(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri=SPOTIFY_REDIRECT_URI,
                    scope=SPOTIFY_SCOPE,
                )
                # Refresh token directly
                token_info = auth_oauth.refresh_access_token(self.bot_refresh_token)
                if token_info:
                    self.sp_bot = spotipy.Spotify(auth=token_info["access_token"])
            except Exception as exc:
                logger.warning(f"Could not init Spotify Bot client: {exc}")

    def find_track(self, song: Song) -> Song:
        """Find track metadata on Spotify or fallback without requiring user login."""
        # Method 1: If Spotify Client Credentials available, use Spotify Web API
        if self.sp_client:
            queries = [f"{song.title} {song.artist}", song.title]
            for query in queries:
                try:
                    data = self.sp_client.search(q=query, type="track", limit=1)
                    items = data.get("tracks", {}).get("items", [])
                    if items:
                        track = items[0]
                        song.spotify_uri = track.get("uri")
                        song.spotify_url = track.get("external_urls", {}).get("spotify")
                        images = track.get("album", {}).get("images", [])
                        if images and not song.cover_url:
                            song.cover_url = images[0]["url"]
                        song.preview_url = track.get("preview_url")
                        song.found_on_spotify = True
                        return song
                except Exception as exc:
                    logger.debug(f"Spotify search error for '{query}': {exc}")

        # Method 2: Fallback to iTunes Search API (0 credentials, high-res covers, 30s audio previews)
        try:
            itunes_resp = requests.get(
                "https://itunes.apple.com/search",
                params={"term": f"{song.title} {song.artist}", "entity": "song", "limit": 1},
                timeout=5,
            )
            if itunes_resp.status_code == 200:
                results = itunes_resp.json().get("results", [])
                if results:
                    item = results[0]
                    if not song.cover_url:
                        song.cover_url = item.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                    if not song.preview_url:
                        song.preview_url = item.get("previewUrl")
        except Exception as exc:
            logger.debug(f"iTunes metadata lookup error: {exc}")

        # Fallback Spotify URL to direct search link
        encoded_query = up.quote(f"{song.title} {song.artist}")
        song.spotify_url = f"https://open.spotify.com/search/{encoded_query}"
        song.found_on_spotify = False
        return song

    def can_create_bot_playlist(self) -> bool:
        """Check whether Bot/Curator mode is ready to create a public Spotify playlist."""
        return self.sp_bot is not None

    def create_playlist_from_songs(self, username: str, songs: Iterable[Song]) -> tuple[str, str]:
        """Create a public Spotify playlist or generate a Spotify playback collection without user login.

        Returns (url, mode_description).
        """
        song_list = list(songs)
        # Ensure all songs have been queried
        for song in song_list:
            if not song.spotify_url:
                self.find_track(song)

        # Mode A: If Bot Account is active, create real public Spotify playlist!
        if self.sp_bot:
            try:
                me = self.sp_bot.current_user()
                playlist_name = PLAYLIST_NAME_TEMPLATE.format(username=username)
                playlist = self.sp_bot.user_playlist_create(
                    user=me["id"],
                    name=playlist_name,
                    public=True,
                    description=PLAYLIST_DESCRIPTION,
                )

                track_uris = [s.spotify_uri for s in song_list if s.spotify_uri]
                for start in range(0, len(track_uris), 100):
                    self.sp_bot.playlist_add_items(
                        playlist_id=playlist["id"],
                        items=track_uris[start : start + 100],
                    )

                playlist_url = playlist["external_urls"]["spotify"]
                return playlist_url, "Playlist Spotify Publik Berhasil Dibuat (Via Bot Curator)"
            except Exception as exc:
                logger.error(f"Failed creating bot playlist: {exc}")

        # Mode B: If no bot account, build a direct Spotify Search / Web Collection link
        first_song = song_list[0] if song_list else None
        if first_song and first_song.spotify_url and "track" in first_song.spotify_url:
            return first_song.spotify_url, "Membuka lagu pertama di Spotify (Daftar lengkap ada di Web Player)"

        search_query = up.quote(f"{song_list[0].title} {song_list[0].artist}" if song_list else username)
        return f"https://open.spotify.com/search/{search_query}", "Link Pencarian Spotify Siap Digunakan"
