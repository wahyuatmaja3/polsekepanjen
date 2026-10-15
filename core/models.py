from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Song:
    title: str
    artist: str
    spotify_uri: str | None = None
    spotify_url: str | None = None
    yt_music_id: str | None = None
    yt_music_url: str | None = None
    cover_url: str | None = None
    preview_url: str | None = None
    occurrence_count: int = 1
    found_on_spotify: bool = False
    found_on_yt_music: bool = False
    post_order_idx: int = 1  # 1 = Newest / latest post
    release_tag: str | None = None

    @property
    def display_text(self) -> str:
        count_str = f" (dipakai {self.occurrence_count}x)" if self.occurrence_count > 1 else ""
        badge = f"#{self.post_order_idx} " if self.post_order_idx else ""
        tag_str = f" [{self.release_tag}]" if self.release_tag else ""
        return f"{badge}{self.title} — {self.artist}{tag_str}{count_str}"


@dataclass
class ScrapingResult:
    username: str
    profile_pic_url: str
    total_posts_scraped: int
    songs: list[Song]
    posts_with_music: int
    posts_without_music: int
    scraped_at: datetime
    is_demo: bool = False
