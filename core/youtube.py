from __future__ import annotations

import logging
import urllib.parse as up
from typing import Callable, Iterable
import requests
from ytmusicapi import YTMusic

from core.models import Song

logger = logging.getLogger(__name__)


class YouTubeMusicError(Exception):
    pass


class YouTubeMusicClient:
    """Client for YouTube Music operations that requires NO user login and NO API keys.

    Uses ytmusicapi for song catalog search and YouTube's watch_videos endpoint
    for instant multi-track playlist queue generation.
    """

    def __init__(self) -> None:
        try:
            self.yt = YTMusic()
        except Exception as exc:
            logger.warning(f"Could not init YTMusic with default settings: {exc}")
            self.yt = None

    def search_track(self, song: Song) -> Song:
        """Search a song on YouTube Music and populate videoId, URL, and thumbnail."""
        if not self.yt:
            return song

        queries = [f"{song.title} {song.artist}", song.title]
        for query in queries:
            try:
                results = self.yt.search(query, filter="songs")
                if results:
                    best = results[0]
                    song.yt_music_id = best.get("videoId")
                    if song.yt_music_id:
                        song.yt_music_url = f"https://music.youtube.com/watch?v={song.yt_music_id}"
                        song.found_on_yt_music = True

                        if not song.cover_url:
                            thumbs = best.get("thumbnails", [])
                            if thumbs:
                                song.cover_url = thumbs[-1].get("url")
                        return song
            except Exception as exc:
                logger.debug(f"YTMusic search error for query '{query}': {exc}")

        song.found_on_yt_music = False
        return song

    def resolve_tracks(
        self,
        songs: Iterable[Song],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[Song]:
        """Resolve YouTube Music video IDs for a list of songs."""
        song_list = list(songs)
        total = len(song_list)
        for idx, song in enumerate(song_list, start=1):
            if not song.yt_music_id:
                if progress_callback:
                    progress_callback(idx, total, f"Mencari '{song.title}' di YouTube Music...")
                self.search_track(song)
        return song_list

    def create_instant_playlist(self, username: str, songs: Iterable[Song]) -> str:
        """Generate an instant multi-track playlist queue on YouTube Music without user login.

        Uses the official YouTube watch_videos endpoint, which automatically compiles
        the video IDs into an active multi-video playback queue (list=TLGG...)
        playable directly on YouTube Music.
        """
        song_list = list(songs)
        # Ensure tracks are resolved
        video_ids = [s.yt_music_id for s in song_list if s.yt_music_id]
        if not video_ids:
            # Try resolving them now
            self.resolve_tracks(song_list)
            video_ids = [s.yt_music_id for s in song_list if s.yt_music_id]

        if not video_ids:
            raise YouTubeMusicError("Tidak ada lagu yang berhasil ditemukan di YouTube Music.")

        # Limit to 50 tracks per instant queue to prevent URL overflow
        selected_ids = video_ids[:50]
        ids_str = ",".join(selected_ids)
        watch_url = f"https://www.youtube.com/watch_videos?video_ids={ids_str}"

        try:
            resp = requests.get(
                watch_url,
                allow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=8,
            )
            redirect_url = resp.headers.get("Location")
            if redirect_url:
                parsed = up.urlparse(redirect_url)
                qs = up.parse_qs(parsed.query)
                playlist_id = qs.get("list", [None])[0]
                first_video = qs.get("v", [selected_ids[0]])[0]
                if playlist_id:
                    # Construct direct YouTube Music playlist queue URL
                    return f"https://music.youtube.com/watch?v={first_video}&list={playlist_id}"
        except Exception as exc:
            logger.warning(f"Redirect resolution failed: {exc}, using watch_videos directly")

        # Fallback to direct watch_videos URL which automatically redirects when opened in browser
        return watch_url
