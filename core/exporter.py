from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Iterable

from core.models import Song


def export_csv(output_path: str | Path, songs: Iterable[Song], username: str) -> None:
    """Export songs to CSV format."""
    path = Path(output_path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Title", "Artist", "Occurrences", "Spotify URL", "YouTube Music URL", "Cover Art"])
        for song in songs:
            writer.writerow([
                song.title,
                song.artist,
                song.occurrence_count,
                song.spotify_url or "",
                song.yt_music_url or "",
                song.cover_url or "",
            ])


def export_m3u(output_path: str | Path, songs: Iterable[Song], username: str) -> None:
    """Export songs to standard M3U8 playlist format."""
    path = Path(output_path)
    with path.open("w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"#PLAYLIST:Music of @{username} (polsekepanjen)\n\n")
        for song in songs:
            link = song.yt_music_url or song.spotify_url or ""
            f.write(f"#EXTINF:-1,{song.artist} - {song.title}\n")
            f.write(f"{link}\n")


def generate_html_player(
    output_path: str | Path,
    username: str,
    songs: Iterable[Song],
    yt_music_playlist_url: str | None = None,
    spotify_playlist_url: str | None = None,
) -> str:
    """Generate a sleek, standalone interactive HTML Web Player for the playlist.

    Users can preview audio, click directly into YouTube Music & Spotify without logging in!
    """
    path = Path(output_path)
    song_list = list(songs)

    cards_html = []
    for idx, song in enumerate(song_list, start=1):
        cover = song.cover_url or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=200&h=200&fit=crop"
        preview_audio = ""
        if song.preview_url:
            preview_audio = f"""
            <audio controls preload="none" class="audio-player">
                <source src="{html.escape(song.preview_url)}" type="audio/mpeg">
                Browser Anda tidak mendukung pemutar audio.
            </audio>
            """

        yt_btn = ""
        if song.yt_music_url:
            yt_btn = f"""<a href="{html.escape(song.yt_music_url)}" target="_blank" class="btn btn-yt">YT Music</a>"""

        sp_btn = ""
        if song.spotify_url:
            sp_btn = f"""<a href="{html.escape(song.spotify_url)}" target="_blank" class="btn btn-sp">Spotify</a>"""

        badge_text = song.release_tag or f"Post Terbaru #{idx}"
        count_info = f" • Dipakai {song.occurrence_count}x" if song.occurrence_count > 1 else ""

        card = f"""
        <div class="song-card">
            <div class="song-index">#{idx}</div>
            <img class="song-cover" src="{html.escape(cover)}" alt="cover" loading="lazy" />
            <div class="song-info">
                <div class="song-title">{html.escape(song.title)}</div>
                <div class="song-artist">{html.escape(song.artist)}</div>
                <div class="song-badge">{html.escape(badge_text)}{count_info}</div>
                {preview_audio}
            </div>
            <div class="song-actions">
                {yt_btn}
                {sp_btn}
            </div>
        </div>
        """
        cards_html.append(card)

    yt_main_btn = ""
    if yt_music_playlist_url:
        yt_main_btn = f"""
        <a href="{html.escape(yt_music_playlist_url)}" target="_blank" class="btn-hero btn-hero-yt">
            ▶ Putar Semua di YouTube Music
        </a>
        """

    sp_main_btn = ""
    if spotify_playlist_url:
        sp_main_btn = f"""
        <a href="{html.escape(spotify_playlist_url)}" target="_blank" class="btn-hero btn-hero-sp">
            🎧 Buka Playlist Spotify
        </a>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playlist Music of @{html.escape(username)} — polsekepanjen</title>
    <style>
        :root {{
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --primary: #6366f1;
            --spotify: #1db954;
            --ytmusic: #ff0000;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --radius: 12px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            padding: 24px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            width: 100%;
            max-width: 860px;
        }}
        header {{
            text-align: center;
            margin-bottom: 28px;
            padding: 24px;
            background: linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(29,185,84,0.1) 100%);
            border-radius: var(--radius);
            border: 1px solid rgba(255,255,255,0.08);
        }}
        header h1 {{
            font-size: 26px;
            margin-bottom: 8px;
            background: linear-gradient(to right, #6366f1, #10b981);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        header p {{
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 18px;
        }}
        .hero-actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: center;
            margin-top: 12px;
        }}
        .btn-hero {{
            display: inline-flex;
            align-items: center;
            padding: 12px 22px;
            font-weight: 600;
            font-size: 14px;
            border-radius: 9999px;
            text-decoration: none;
            color: white;
            box-shadow: 0 4px 14px rgba(0,0,0,0.3);
            transition: transform 0.2s, opacity 0.2s;
        }}
        .btn-hero:hover {{
            transform: translateY(-2px);
            opacity: 0.95;
        }}
        .btn-hero-yt {{ background: linear-gradient(135deg, #ff0000, #cc0000); }}
        .btn-hero-sp {{ background: linear-gradient(135deg, #1db954, #1aa34a); }}
        .song-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .song-card {{
            display: flex;
            align-items: center;
            background: var(--surface);
            padding: 12px 16px;
            border-radius: var(--radius);
            gap: 16px;
            transition: background 0.2s;
            border: 1px solid rgba(255,255,255,0.04);
        }}
        .song-card:hover {{
            background: var(--surface-hover);
        }}
        .song-index {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 600;
            width: 28px;
        }}
        .song-cover {{
            width: 56px;
            height: 56px;
            border-radius: 8px;
            object-fit: cover;
            background: #2d3748;
        }}
        .song-info {{
            flex: 1;
            min-width: 0;
        }}
        .song-title {{
            font-weight: 600;
            font-size: 15px;
            color: var(--text);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .song-artist {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        .song-badge {{
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 6px;
            background: rgba(99,102,241,0.2);
            color: #a5b4fc;
            margin-top: 4px;
        }}
        .audio-player {{
            height: 28px;
            margin-top: 6px;
            max-width: 240px;
        }}
        .song-actions {{
            display: flex;
            gap: 8px;
        }}
        .btn {{
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
            color: white;
            transition: opacity 0.2s;
        }}
        .btn:hover {{ opacity: 0.85; }}
        .btn-yt {{ background: #ff0000; }}
        .btn-sp {{ background: #1db954; }}
        footer {{
            text-align: center;
            margin-top: 36px;
            color: var(--text-muted);
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Playlist Instagram @{html.escape(username)}</h1>
            <p>Ditemukan {len(song_list)} lagu unik dari postingan Instagram • Dibuat dengan polsekepanjen</p>
            <div class="hero-actions">
                {yt_main_btn}
                {sp_main_btn}
            </div>
        </header>

        <div class="song-list">
            {"".join(cards_html)}
        </div>

        <footer>
            Dibuat secara otomatis oleh polsekepanjen (Tanpa perlu login akun).
        </footer>
    </div>
</body>
</html>
"""
    path.write_text(html_content, encoding="utf-8")
    return str(path.resolve())
