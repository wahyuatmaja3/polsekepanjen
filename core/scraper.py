from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from threading import Event
from time import sleep
from typing import Callable

import instaloader
from instaloader import Profile

from config.settings import INSTAGRAM_SESSION_ID, SCRAPE_DELAY_SECONDS
from core.models import ScrapingResult, Song

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


class PrivateAccountError(ScraperError):
    pass


class AccountNotFoundError(ScraperError):
    pass


class RateLimitError(ScraperError):
    pass


class AccessBlockedError(ScraperError):
    pass


@dataclass
class ProfilePreview:
    username: str
    full_name: str
    profile_pic_url: str
    posts_count: int
    is_demo: bool = False


ProgressCallback = Callable[[int, int, str], None]


# Curated demo data strictly ordered from NEWEST release/post to older
DEMO_PROFILES: dict[str, list[tuple[str, str, int, str]]] = {
    "taylorswift": [
        ("Fortnight", "Taylor Swift feat. Post Malone", 14, "Terbaru - 2024"),
        ("I Can Do It With a Broken Heart", "Taylor Swift", 12, "Terbaru - 2024"),
        ("Cruel Summer", "Taylor Swift", 10, "Eras Tour"),
        ("Anti-Hero", "Taylor Swift", 9, "Midnights"),
        ("Karma", "Taylor Swift", 8, "Midnights"),
        ("Lavender Haze", "Taylor Swift", 6, "Midnights"),
        ("Lover", "Taylor Swift", 5, "Lover"),
        ("Cardigan", "Taylor Swift", 4, "Folklore"),
        ("Blank Space", "Taylor Swift", 4, "1989"),
        ("Style", "Taylor Swift", 3, "1989"),
    ],
    "billieeilish": [
        ("LUNCH", "Billie Eilish", 12, "Terbaru - 2024"),
        ("CHIHIRO", "Billie Eilish", 10, "Terbaru - 2024"),
        ("BIRDS OF A FEATHER", "Billie Eilish", 10, "Terbaru - 2024"),
        ("WILDFLOWER", "Billie Eilish", 8, "Terbaru - 2024"),
        ("BLUE", "Billie Eilish", 7, "Terbaru - 2024"),
        ("What Was I Made For?", "Billie Eilish", 6, "2023"),
        ("Happier Than Ever", "Billie Eilish", 5, "2021"),
        ("bad guy", "Billie Eilish", 4, "2019"),
    ],
    "nadinamizah": [
        ("Di Akhir Perang", "Nadin Amizah", 11, "Terbaru"),
        ("Tawa", "Nadin Amizah", 10, "Terbaru"),
        ("Rayuan Perempuan Gila", "Nadin Amizah", 9, "Populer"),
        ("Semua Aku Dirayakan", "Nadin Amizah", 8, "Populer"),
        ("Beranjak Dewasa", "Nadin Amizah", 6, "Populer"),
        ("Kekal", "Nadin Amizah", 5, "Album"),
        ("Bertaut", "Nadin Amizah", 5, "Album"),
        ("Sorai", "Nadin Amizah", 4, "Album"),
    ],
    "salpriadi": [
        ("Gala bunga matahari", "Sal Priadi", 14, "Terbaru - 2024"),
        ("Foto kita blur", "Sal Priadi", 12, "Terbaru - 2024"),
        ("Dari planet lain", "Sal Priadi", 10, "Terbaru - 2024"),
        ("Kita usahakan rumah itu", "Sal Priadi", 8, "2024"),
        ("Mesra-mesraannya kecil-kecilan dulu", "Sal Priadi", 7, "2024"),
        ("Ada titik-titik di ujung doa", "Sal Priadi", 6, "2024"),
    ],
    "bernadya": [
        ("Untungnya, Hidup Harus Tetap Berjalan", "Bernadya", 15, "Terbaru - 2024"),
        ("Satu Bulan", "Bernadya", 13, "Terbaru - 2024"),
        ("Kini Mereka Tahu", "Bernadya", 10, "Terbaru - 2024"),
        ("Kata Mereka Ini Berlebihan", "Bernadya", 8, "Terbaru - 2024"),
        ("Apa Mungkin", "Bernadya", 7, "Single"),
        ("Masa Sepi", "Bernadya", 5, "Single"),
    ],
    "default": [
        ("Gala bunga matahari", "Sal Priadi", 10, "Trending Reels 2024"),
        ("Untungnya, Hidup Harus Tetap Berjalan", "Bernadya", 9, "Trending Reels 2024"),
        ("BIRDS OF A FEATHER", "Billie Eilish", 9, "Trending Reels 2024"),
        ("Espresso", "Sabrina Carpenter", 8, "Trending Reels 2024"),
        ("Die With A Smile", "Lady Gaga & Bruno Mars", 8, "Trending Reels 2024"),
        ("Satu Bulan", "Bernadya", 7, "Trending Reels 2024"),
        ("Blinding Lights", "The Weeknd", 6, "Trending Reels"),
        ("As It Was", "Harry Styles", 6, "Trending Reels"),
        ("Cruel Summer", "Taylor Swift", 5, "Trending Reels"),
    ],
}


class InstagramScraper:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id: str = (session_id or INSTAGRAM_SESSION_ID or "").strip()
        self._init_loader()
        self.cancel_event = Event()

    def _init_loader(self) -> None:
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_video_thumbnails=False,
            download_videos=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
            max_connection_attempts=1,
            request_timeout=8.0,
        )
        if self.session_id:
            try:
                self.loader.context._session.cookies.set("sessionid", self.session_id, domain=".instagram.com")
            except Exception as exc:
                logger.warning(f"Could not inject Instagram session: {exc}")

        self._check_default_cookie_files()

    def _check_default_cookie_files(self) -> None:
        from pathlib import Path

        for candidate in ["cookies.txt", "instagram_cookies.txt", "ig_cookies.txt"]:
            p = Path(candidate)
            if p.is_file():
                self.load_cookies_from_file(str(p))
                break

    def set_session_id(self, session_id: str) -> None:
        """Update or inject an Instagram sessionid cookie."""
        self.session_id = session_id.strip()
        self._init_loader()

    def load_cookies_from_file(self, file_path: str) -> tuple[bool, str]:
        """Load Netscape cookies.txt file exported from 'Get cookies.txt LOCALLY'."""
        import http.cookiejar
        from pathlib import Path

        path = Path(file_path)
        if not path.is_file():
            return False, f"File tidak ditemukan: {path.name}"

        try:
            jar = http.cookiejar.MozillaCookieJar(str(path))
            jar.load(ignore_discard=True, ignore_expires=True)
            self.loader.context._session.cookies.update(jar)

            session_found = False
            for c in jar:
                if c.name == "sessionid":
                    self.session_id = c.value
                    session_found = True
                    break

            if session_found:
                return True, f"Cookie berhasil dimuat dari {path.name} (sessionid terverifikasi)!"
            else:
                return True, f"Cookie dimuat dari {path.name}, tetapi sessionid tidak ditemukan."
        except Exception as exc:
            return False, f"Gagal membaca format cookies.txt: {exc}"

    def cancel(self) -> None:
        self.cancel_event.set()

    def reset_cancel(self) -> None:
        self.cancel_event.clear()

    def _clean_username(self, username: str) -> str:
        return username.strip().lstrip("@").strip()

    def _map_profile_error(self, exc: Exception, username: str) -> ScraperError:
        message = str(exc).lower()
        if "429" in message or "too many requests" in message or "rate" in message:
            return RateLimitError("Instagram membatasi request sementara (429 Rate Limit).")
        if "403" in message or "forbidden" in message or "graphql/query" in message or "login" in message or "checkpoint" in message:
            return AccessBlockedError(
                f"Instagram memblokir akses ke postingan @{username} (403 Forbidden).\n\n"
                "Meta/Instagram mewajibkan session login untuk membaca postingan akun ini.\n"
                "Silakan muat file 'cookies.txt' (dari ekstensi Get cookies.txt LOCALLY) lewat tombol 'Cookie IG'."
            )
        if "not found" in message or "404" in message or "not exist" in message:
            return AccountNotFoundError(f"Akun @{username} tidak ditemukan di Instagram.")
        return ScraperError(f"Gagal mengakses akun Instagram @{username}: {exc}")

    def _is_generic_audio(self, title: str, artist: str) -> bool:
        """Check if audio is an uncredited original audio rather than a commercial song."""
        t_low = title.lower()
        a_low = artist.lower()
        generic_markers = ["original audio", "audio asli", "suara asli", "original sound"]
        return any(m in t_low or m in a_low for m in generic_markers)

    def extract_music_from_post(self, post: instaloader.Post) -> tuple[str, str] | None:
        """Extract song title and artist from an Instagram Post or Reel."""
        node = getattr(post, "_node", {}) or {}

        # 1. Check clips_music_attribution_info (Instagram Reels)
        clips_info = node.get("clips_music_attribution_info") or {}
        if clips_info:
            song_name = (clips_info.get("song_name") or "").strip()
            artist_name = (clips_info.get("artist_name") or "").strip()
            uses_orig = clips_info.get("uses_original_audio", False)
            if song_name and artist_name and not uses_orig and not self._is_generic_audio(song_name, artist_name):
                return song_name, artist_name

        # 2. Check music_metadata
        music_meta = node.get("music_metadata") or {}
        if music_meta:
            asset = music_meta.get("music_info", {}).get("music_asset_info", {})
            title = (asset.get("title") or "").strip()
            artist = (asset.get("display_artist") or "").strip()
            if title and artist and not self._is_generic_audio(title, artist):
                return title, artist

        # 3. Check caption for music tags
        caption = getattr(post, "caption", "") or ""
        if caption:
            patterns = [
                r"(?:🎵|🎶|Music:|Song:|Lagu:)\s*([^-—\n]+)\s*[-—]\s*([^\n]+)",
                r"(?:🎵|🎶)\s*([^\n]+)",
            ]
            for pat in patterns:
                match = re.search(pat, caption, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        return groups[0].strip(), groups[1].strip()
                    elif len(groups) == 1 and " - " in groups[0]:
                        parts = groups[0].split(" - ", 1)
                        return parts[0].strip(), parts[1].strip()

        return None

    def get_profile_preview(self, username: str) -> ProfilePreview:
        clean = self._clean_username(username)
        if not clean:
            raise AccountNotFoundError("Username tidak valid.")

        try:
            profile = Profile.from_username(self.loader.context, clean)
            if profile.is_private:
                raise PrivateAccountError(f"Akun @{clean} bersifat Private dan tidak bisa diakses.")
            return ProfilePreview(
                username=profile.username,
                full_name=profile.full_name or profile.username,
                profile_pic_url=profile.profile_pic_url,
                posts_count=profile.mediacount,
                is_demo=False,
            )
        except Exception as exc:
            raise self._map_profile_error(exc, clean) from exc

    def get_demo_result(self, username: str, max_songs: int = 10) -> ScrapingResult:
        """Return curated sample data for instant MVP demonstration without hitting Instagram."""
        clean = self._clean_username(username) or "creator"
        items = DEMO_PROFILES.get(clean.lower(), DEMO_PROFILES["default"])

        selected_items = items[:max_songs]
        songs = [
            Song(
                title=item[0],
                artist=item[1],
                occurrence_count=item[2],
                post_order_idx=idx,
                release_tag=item[3] if len(item) > 3 else f"Post Terbaru #{idx}",
            )
            for idx, item in enumerate(selected_items, start=1)
        ]

        return ScrapingResult(
            username=clean,
            profile_pic_url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=150&h=150&fit=crop",
            total_posts_scraped=sum(s.occurrence_count for s in songs) + 3,
            songs=songs,
            posts_with_music=sum(s.occurrence_count for s in songs),
            posts_without_music=3,
            scraped_at=datetime.now(),
            is_demo=True,
        )

    def parse_manual_songs(self, text: str) -> list[Song]:
        """Parse raw text lines of songs into Song objects in exact order of input."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        songs: list[Song] = []
        for idx, line in enumerate(lines, start=1):
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            if " - " in line:
                parts = line.split(" - ", 1)
                songs.append(Song(title=parts[0].strip(), artist=parts[1].strip(), post_order_idx=idx))
            elif " — " in line:
                parts = line.split(" — ", 1)
                songs.append(Song(title=parts[0].strip(), artist=parts[1].strip(), post_order_idx=idx))
            elif " by " in line.lower():
                i = line.lower().index(" by ")
                songs.append(Song(title=line[:i].strip(), artist=line[i + 4 :].strip(), post_order_idx=idx))
            else:
                songs.append(Song(title=line.strip(), artist="", post_order_idx=idx))
        return songs

    def scrape_music(
        self,
        username: str,
        max_songs: int = 10,
        progress_callback: ProgressCallback | None = None,
        max_posts_to_scan: int = 100,
    ) -> ScrapingResult:
        """Scrape music from the actual Instagram profile and its recent posts.

        Scans starting from the newest post, strictly maintaining chronological order.
        """
        self.reset_cancel()
        clean = self._clean_username(username)
        if not clean:
            raise AccountNotFoundError("Username tidak valid.")

        # Check session: if user has no session, alert them so they can load cookies.txt
        if not self.session_id:
            raise AccessBlockedError(
                f"Instagram membatasi akses tanpa login (403 Forbidden pada graphql/query).\n\n"
                f"Untuk membaca postingan & musik asli dari akun @{clean}, Anda perlu memuat session Instagram.\n"
                "Silakan muat file 'cookies.txt' (dari ekstensi Get cookies.txt LOCALLY) lewat tombol 'Cookie IG' di atas."
            )

        if progress_callback:
            progress_callback(0, max_songs, f"Menghubungkan ke profil Instagram @{clean}...")

        try:
            profile = Profile.from_username(self.loader.context, clean)
        except Exception as exc:
            raise self._map_profile_error(exc, clean) from exc

        if profile.is_private:
            raise PrivateAccountError(f"Akun @{clean} bersifat Private dan tidak bisa diakses.")

        if progress_callback:
            progress_callback(0, max_songs, f"Memeriksa postingan terbaru @{clean} (mencari {max_songs} lagu)...")

        try:
            posts = profile.get_posts()
        except Exception as exc:
            raise self._map_profile_error(exc, clean) from exc

        songs_map: dict[tuple[str, str], Song] = {}
        posts_with_music = 0
        posts_without_music = 0

        idx = 0
        for idx, post in enumerate(posts, start=1):
            if self.cancel_event.is_set():
                raise ScraperError("Scraping dibatalkan.")

            if len(songs_map) >= max_songs:
                if progress_callback:
                    progress_callback(len(songs_map), max_songs, f"Target {max_songs} lagu terbaru berhasil ditemukan!")
                break
            if idx > max_posts_to_scan:
                break

            if progress_callback:
                progress_callback(len(songs_map), max_songs, f"Memeriksa post #{idx} (Lagu unik: {len(songs_map)}/{max_songs})...")

            extracted = self.extract_music_from_post(post)
            if extracted:
                title, artist = extracted
                key = (title.lower(), artist.lower())
                if key in songs_map:
                    songs_map[key].occurrence_count += 1
                else:
                    order = len(songs_map) + 1
                    songs_map[key] = Song(
                        title=title,
                        artist=artist,
                        post_order_idx=order,
                        release_tag=f"Post Terbaru #{idx}",
                    )
                posts_with_music += 1
            else:
                posts_without_music += 1

            if len(songs_map) >= max_songs:
                break

            sleep(SCRAPE_DELAY_SECONDS)

        # Strictly maintain order from the NEWEST post to older posts (insertion order)
        songs = list(songs_map.values())

        if not songs and posts_without_music > 0:
            logger.info(f"Scraped {idx} posts for @{clean}, but none contained commercial music assets.")

        return ScrapingResult(
            username=profile.username,
            profile_pic_url=str(profile.profile_pic_url),
            total_posts_scraped=idx,
            songs=songs,
            posts_with_music=posts_with_music,
            posts_without_music=posts_without_music,
            scraped_at=datetime.now(),
            is_demo=False,
        )
