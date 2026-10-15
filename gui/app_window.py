from __future__ import annotations

import csv
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.exporter import export_csv, export_m3u, generate_html_player
from core.models import ScrapingResult, Song
from core.scraper import (
    AccessBlockedError,
    AccountNotFoundError,
    InstagramScraper,
    PrivateAccountError,
    RateLimitError,
    ScraperError,
)
from core.spotify import SpotifyManager
from core.youtube import YouTubeMusicClient, YouTubeMusicError

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AppWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("polsekepanjen — Instagram to Spotify & YouTube Music Playlist")
        self.geometry("1020x760")
        self.minsize(860, 640)

        # Core Engines (Zero User Login Required)
        self.scraper = InstagramScraper()
        self.yt_client = YouTubeMusicClient()
        self.spotify_mgr = SpotifyManager()

        self.scrape_result: ScrapingResult | None = None
        self.song_vars: list[tuple[Song, tk.BooleanVar]] = []
        self.queue: Queue = Queue()

        self._build_ui()
        self.after(100, self._process_queue)

    def _build_ui(self) -> None:
        self.username_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Masukkan username Instagram lalu klik 'Mulai Scraping' (Tanpa login Spotify / YouTube Music).")
        self.profile_var = tk.StringVar(value="")
        self.yt_playlist_url_var = tk.StringVar(value="")
        self.spotify_playlist_url_var = tk.StringVar(value="")

        # ----------------- TOP HEADER & INPUT -----------------
        top_card = ctk.CTkFrame(self, corner_radius=10)
        top_card.pack(fill="x", padx=16, pady=(16, 8))

        title_lbl = ctk.CTkLabel(
            top_card,
            text="🎵 polsekepanjen — Generator Playlist Musik Instagram",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_lbl.pack(anchor="w", padx=14, pady=(12, 4))

        sub_lbl = ctk.CTkLabel(
            top_card,
            text="Ekstrak musik akun Instagram → Buat playlist Spotify & YouTube Music (100% Tanpa Login Spotify & YouTube Music!)",
            font=ctk.CTkFont(size=12),
            text_color="#10b981",
        )
        sub_lbl.pack(anchor="w", padx=14, pady=(0, 10))

        # Input Row
        input_row = ctk.CTkFrame(top_card, fg_color="transparent")
        input_row.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(input_row, text="Username:", font=ctk.CTkFont(size=13, weight="bold")).pack(
            side="left", padx=(0, 6)
        )
        self.username_entry = ctk.CTkEntry(
            input_row,
            textvariable=self.username_var,
            placeholder_text="Contoh: billieeilish atau nadinamizah",
            width=220,
        )
        self.username_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(input_row, text="Jumlah Lagu:", font=ctk.CTkFont(size=13, weight="bold")).pack(
            side="left", padx=(0, 6)
        )
        self.max_songs_var = tk.StringVar(value="10")
        self.max_songs_box = ctk.CTkComboBox(
            input_row,
            variable=self.max_songs_var,
            values=["5", "10", "15", "20", "30", "50"],
            width=75,
        )
        self.max_songs_box.pack(side="left", padx=(0, 10))

        self.scrape_btn = ctk.CTkButton(
            input_row,
            text="🔍 Mulai Scraping",
            command=self.on_scrape,
            font=ctk.CTkFont(weight="bold"),
        )
        self.scrape_btn.pack(side="left", padx=(0, 8))

        self.demo_btn = ctk.CTkButton(
            input_row,
            text="⚡ Demo Mode",
            command=self.on_load_demo,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            width=90,
        )
        self.demo_btn.pack(side="left", padx=(0, 6))

        self.manual_btn = ctk.CTkButton(
            input_row,
            text="📝 Input Manual",
            command=self.on_open_manual_input,
            fg_color="gray30",
            hover_color="gray40",
            width=95,
        )
        self.manual_btn.pack(side="left", padx=(0, 6))

        self.cookie_btn = ctk.CTkButton(
            input_row,
            text="🔑 Cookie IG",
            command=self.on_set_cookie,
            fg_color="gray30",
            hover_color="gray40",
            width=80,
        )
        self.cookie_btn.pack(side="left", padx=(0, 6))

        self.cancel_btn = ctk.CTkButton(
            input_row,
            text="Batal",
            command=self.on_cancel_scrape,
            state="disabled",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            width=65,
        )
        self.cancel_btn.pack(side="left")

        # Profile status text
        self.profile_lbl = ctk.CTkLabel(
            top_card,
            textvariable=self.profile_var,
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8",
        )
        self.profile_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        # ----------------- PROGRESS & STATUS -----------------
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=16, pady=(4, 4))
        self.progress.set(0)

        status_bar = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        status_bar.pack(fill="x", padx=18, pady=(2, 6))

        # ----------------- MIDDLE: SONG LIST -----------------
        list_header_row = ctk.CTkFrame(self, fg_color="transparent")
        list_header_row.pack(fill="x", padx=16, pady=(4, 2))

        ctk.CTkLabel(
            list_header_row,
            text="Daftar Lagu Terdeteksi",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        self.select_all_btn = ctk.CTkButton(
            list_header_row,
            text="Pilih Semua",
            width=90,
            height=26,
            command=self.on_select_all,
            fg_color="gray30",
            hover_color="gray40",
        )
        self.select_all_btn.pack(side="right", padx=(6, 0))

        self.deselect_all_btn = ctk.CTkButton(
            list_header_row,
            text="Batal Pilih",
            width=90,
            height=26,
            command=self.on_deselect_all,
            fg_color="gray30",
            hover_color="gray40",
        )
        self.deselect_all_btn.pack(side="right")

        self.song_container = ctk.CTkScrollableFrame(
            self, label_text="Daftar Lagu (Diurutkan dari Postingan / Rilis Paling Baru)"
        )
        self.song_container.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        # ----------------- GENERATED PLAYLIST RESULT BANNER -----------------
        self.result_card = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        self.result_card.pack(fill="x", padx=16, pady=(4, 8))

        res_inner = ctk.CTkFrame(self.result_card, fg_color="transparent")
        res_inner.pack(fill="x", padx=12, pady=10)

        # YT Music Link row
        yt_row = ctk.CTkFrame(res_inner, fg_color="transparent")
        yt_row.pack(fill="x", pady=2)
        ctk.CTkLabel(yt_row, text="YouTube Music Playlist:", font=ctk.CTkFont(size=12, weight="bold")).pack(
            side="left", padx=(0, 8)
        )
        self.yt_url_entry = ctk.CTkEntry(yt_row, textvariable=self.yt_playlist_url_var, state="readonly", height=28)
        self.yt_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.open_yt_btn = ctk.CTkButton(
            yt_row,
            text="▶ Buka YT Music",
            width=130,
            height=28,
            fg_color="#ff0000",
            hover_color="#cc0000",
            command=self.on_open_yt_playlist,
            state="disabled",
        )
        self.open_yt_btn.pack(side="left")

        # Spotify Link row
        sp_row = ctk.CTkFrame(res_inner, fg_color="transparent")
        sp_row.pack(fill="x", pady=2)
        ctk.CTkLabel(sp_row, text="Spotify Playlist:", font=ctk.CTkFont(size=12, weight="bold")).pack(
            side="left", padx=(0, 48)
        )
        self.sp_url_entry = ctk.CTkEntry(
            sp_row, textvariable=self.spotify_playlist_url_var, state="readonly", height=28
        )
        self.sp_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.open_sp_btn = ctk.CTkButton(
            sp_row,
            text="🎧 Buka Spotify",
            width=130,
            height=28,
            fg_color="#1db954",
            hover_color="#1aa34a",
            command=self.on_open_spotify_playlist,
            state="disabled",
        )
        self.open_sp_btn.pack(side="left")

        # ----------------- BOTTOM ACTIONS -----------------
        bottom = ctk.CTkFrame(self, corner_radius=10)
        bottom.pack(fill="x", padx=16, pady=(0, 16))

        btn_box = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_box.pack(fill="x", padx=12, pady=10)

        # Primary Generate Button (Both)
        self.create_both_btn = ctk.CTkButton(
            btn_box,
            text="⚡ Buat Playlist Keduanya",
            font=ctk.CTkFont(weight="bold"),
            command=self.on_create_both_playlists,
            fg_color="#10b981",
            hover_color="#059669",
            height=34,
        )
        self.create_both_btn.pack(side="left", padx=(0, 8))

        # YT Music Only
        self.create_yt_btn = ctk.CTkButton(
            btn_box,
            text="▶ Playlist YT Music",
            command=self.on_create_yt_playlist,
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=34,
        )
        self.create_yt_btn.pack(side="left", padx=(0, 8))

        # Spotify Only
        self.create_sp_btn = ctk.CTkButton(
            btn_box,
            text="🎧 Playlist Spotify",
            command=self.on_create_spotify_playlist,
            fg_color="#1db954",
            hover_color="#1aa34a",
            height=34,
        )
        self.create_sp_btn.pack(side="left", padx=(0, 8))

        # HTML Web Player
        self.web_player_btn = ctk.CTkButton(
            btn_box,
            text="🌐 Buka Web Player",
            command=self.on_open_html_player,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            height=34,
        )
        self.web_player_btn.pack(side="left", padx=(0, 8))

        # Export Files
        self.export_csv_btn = ctk.CTkButton(
            btn_box,
            text="📄 Export CSV",
            command=self.on_export_csv,
            fg_color="gray30",
            hover_color="gray40",
            height=34,
            width=100,
        )
        self.export_csv_btn.pack(side="right", padx=(8, 0))

        self.export_m3u_btn = ctk.CTkButton(
            btn_box,
            text="🎵 Export M3U8",
            command=self.on_export_m3u,
            fg_color="gray30",
            hover_color="gray40",
            height=34,
            width=110,
        )
        self.export_m3u_btn.pack(side="right")

    def _clean_username(self) -> str:
        return self.username_var.get().strip().lstrip("@").strip()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.scrape_btn.configure(state=state)
        self.demo_btn.configure(state=state)
        self.create_both_btn.configure(state=state)
        self.create_yt_btn.configure(state=state)
        self.create_sp_btn.configure(state=state)
        self.web_player_btn.configure(state=state)
        self.cancel_btn.configure(state="normal" if busy else "disabled")

    def _get_selected_songs(self) -> list[Song]:
        return [song for song, var in self.song_vars if var.get()]

    def on_select_all(self) -> None:
        for _, var in self.song_vars:
            var.set(True)

    def on_deselect_all(self) -> None:
        for _, var in self.song_vars:
            var.set(False)

    def _get_max_songs(self) -> int:
        try:
            val = int(self.max_songs_var.get().strip())
            return max(1, min(val, 100))
        except ValueError:
            return 10

    def on_load_demo(self) -> None:
        username = self._clean_username() or "taylorswift"
        self.username_var.set(username)
        max_songs = self._get_max_songs()
        self.status_var.set(f"Memuat {max_songs} data lagu contoh untuk @{username}...")
        result = self.scraper.get_demo_result(username, max_songs=max_songs)
        self._on_scrape_completed(result)
        self.status_var.set(
            f"Mode Demo aktif: {len(result.songs)} lagu dimuat untuk @{result.username}. "
            "Anda dapat langsung klik 'Buat Playlist Keduanya' tanpa login!"
        )

    def on_open_manual_input(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Input / Tempel Daftar Lagu Manual")
        dialog.geometry("520x440")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Tempel Daftar Lagu (Satu lagu per baris)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            dialog,
            text="Format yang didukung: 'Judul Lagu - Artis' atau 'Judul Lagu'",
            font=ctk.CTkFont(size=12),
            text_color="gray70",
        ).pack(anchor="w", padx=16, pady=(0, 8))

        textbox = ctk.CTkTextbox(dialog, height=220)
        textbox.pack(fill="both", expand=True, padx=16, pady=4)
        textbox.insert(
            "1.0",
            "Rayuan Perempuan Gila - Nadin Amizah\n"
            "Cruel Summer - Taylor Swift\n"
            "BIRDS OF A FEATHER - Billie Eilish\n"
            "As It Was - Harry Styles\n"
            "Stay - The Kid LAROI\n",
        )

        def on_import() -> None:
            content = textbox.get("1.0", "end").strip()
            if not content:
                return
            songs = self.scraper.parse_manual_songs(content)
            if not songs:
                return
            username = self._clean_username() or "custom_music"
            res = ScrapingResult(
                username=username,
                profile_pic_url="https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=150&h=150&fit=crop",
                total_posts_scraped=len(songs),
                songs=songs,
                posts_with_music=len(songs),
                posts_without_music=0,
                scraped_at=datetime.now(),
                is_demo=False,
            )
            self._on_scrape_completed(res)
            self.status_var.set(f"{len(songs)} lagu manual berhasil dimuat! Siap dibuatkan playlist.")
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=12)
        ctk.CTkButton(
            btn_row,
            text="Impor ke Daftar Lagu",
            command=on_import,
            fg_color="#10b981",
            hover_color="#059669",
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Tutup", command=dialog.destroy, fg_color="gray30").pack(side="left")

    def on_set_cookie(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Pengaturan Cookie Session Instagram")
        dialog.geometry("520x380")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Session Cookie Instagram (Bypass 403 Forbidden)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))

        status_txt = "✓ Session Terpasang" if self.scraper.session_id else "Belum ada session aktif"
        status_color = "#10b981" if self.scraper.session_id else "gray60"
        status_lbl = ctk.CTkLabel(dialog, text=f"Status: {status_txt}", text_color=status_color, font=ctk.CTkFont(size=12))
        status_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        # Option 1: File cookies.txt from Get cookies.txt LOCALLY
        opt1_frame = ctk.CTkFrame(dialog, fg_color="gray20", corner_radius=8)
        opt1_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            opt1_frame,
            text="Metode 1: Muat File 'cookies.txt' (Rekomendasi)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            opt1_frame,
            text="Hasil export dari ekstensi browser 'Get cookies.txt LOCALLY' (Chrome/Edge/Firefox)",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        def on_browse_cookie_file() -> None:
            file_path = filedialog.askopenfilename(
                parent=dialog,
                title="Pilih File cookies.txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile="cookies.txt",
            )
            if not file_path:
                return
            ok, msg = self.scraper.load_cookies_from_file(file_path)
            if ok:
                messagebox.showinfo("Sukses", msg, parent=dialog)
                self.status_var.set(msg)
                dialog.destroy()
            else:
                messagebox.showerror("Gagal", msg, parent=dialog)

        ctk.CTkButton(
            opt1_frame,
            text="📂 Pilih File cookies.txt",
            command=on_browse_cookie_file,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=30,
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # Option 2: Paste sessionid
        opt2_frame = ctk.CTkFrame(dialog, fg_color="gray20", corner_radius=8)
        opt2_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            opt2_frame,
            text="Metode 2: Tempel Nilai 'sessionid' Manual",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 2))

        entry_val = tk.StringVar(value=self.scraper.session_id)
        entry = ctk.CTkEntry(opt2_frame, textvariable=entry_val, placeholder_text="Tempel sessionid di sini...", show="*")
        entry.pack(fill="x", padx=12, pady=(0, 8))

        def on_save_text() -> None:
            val = entry_val.get().strip()
            if val:
                self.scraper.set_session_id(val)
                self.status_var.set("Session Instagram berhasil diperbarui!")
                messagebox.showinfo("Sukses", "Cookie sessionid berhasil disimpan!", parent=dialog)
                dialog.destroy()

        ctk.CTkButton(
            opt2_frame,
            text="Simpan sessionid",
            command=on_save_text,
            fg_color="#10b981",
            hover_color="#059669",
            height=28,
        ).pack(anchor="w", padx=12, pady=(0, 10))

    def _show_cookie_required_dialog(self, username: str, reason: str = "") -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Session Instagram Diperlukan")
        dialog.geometry("540x370")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="⚠️ Instagram Memerlukan Cookie Session",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f59e0b",
        ).pack(anchor="w", padx=20, pady=(18, 6))

        desc = (
            f"Instagram membatasi akses tanpa login (403 Forbidden pada graphql/query).\n\n"
            f"Untuk memeriksa postingan asli dari akun @{username} dan mengekstrak lagu-lagu terbarunya, "
            f"diperlukan file 'cookies.txt'.\n\n"
            f"Cara mendapatkan:\n"
            f"1. Pasang ekstensi 'Get cookies.txt LOCALLY' di browser Chrome/Edge.\n"
            f"2. Buka instagram.com (pastikan sudah login di browser).\n"
            f"3. Klik ikon ekstensi lalu klik Export cookies.txt."
        )
        ctk.CTkLabel(
            dialog,
            text=desc,
            font=ctk.CTkFont(size=12),
            text_color="gray85",
            justify="left",
            wraplength=490,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 10))

        def on_choose_file() -> None:
            file_path = filedialog.askopenfilename(
                parent=dialog,
                title="Pilih File cookies.txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile="cookies.txt",
            )
            if not file_path:
                return
            ok, msg = self.scraper.load_cookies_from_file(file_path)
            if ok:
                dialog.destroy()
                self.status_var.set(f"Cookie berhasil dimuat! Memulai scraping @{username}...")
                self.on_scrape()
            else:
                messagebox.showerror("Gagal", msg, parent=dialog)

        def on_use_demo() -> None:
            dialog.destroy()
            self.on_load_demo()

        def on_use_manual() -> None:
            dialog.destroy()
            self.on_open_manual_input()

        ctk.CTkButton(
            btn_row,
            text="📂 Pilih cookies.txt & Lanjut",
            command=on_choose_file,
            fg_color="#10b981",
            hover_color="#059669",
            height=34,
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="⚡ Mode Demo",
            command=on_use_demo,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            height=34,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="📝 Input Manual",
            command=on_use_manual,
            fg_color="gray30",
            hover_color="gray40",
            height=34,
        ).pack(side="left")

        cancel_row = ctk.CTkFrame(dialog, fg_color="transparent")
        cancel_row.pack(fill="x", padx=20, pady=(6, 0))
        ctk.CTkButton(
            cancel_row,
            text="Tutup",
            command=dialog.destroy,
            fg_color="transparent",
            text_color="gray60",
            hover_color="gray25",
            width=70,
            height=28,
        ).pack(side="right")

    def on_scrape(self) -> None:
        username = self._clean_username()
        if not username:
            self.status_var.set("Silakan masukkan username Instagram terlebih dahulu.")
            return

        if not self.scraper.session_id:
            self._show_cookie_required_dialog(username)
            return

        max_songs = self._get_max_songs()
        self._set_busy(True)
        self.progress.set(0)
        self.status_var.set(f"Menghubungi Instagram untuk @{username} (target {max_songs} lagu terbaru)...")

        def worker() -> None:
            try:
                def progress_cb(current: int, total: int, msg: str) -> None:
                    self.queue.put(("progress", current, total, msg))

                result = self.scraper.scrape_music(
                    username=username,
                    max_songs=max_songs,
                    progress_callback=progress_cb,
                    max_posts_to_scan=100,
                )
                self.queue.put(("scrape_done", result))
            except (RateLimitError, AccessBlockedError) as exc:
                self.queue.put(("scrape_blocked", str(exc), username))
            except Exception as exc:
                self.queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def on_cancel_scrape(self) -> None:
        self.scraper.cancel()
        self.status_var.set("Membatalkan proses...")

    def _on_scrape_completed(self, result: ScrapingResult) -> None:
        self.scrape_result = result
        prefix = "[DEMO] " if result.is_demo else ""
        self.profile_var.set(
            f"{prefix}@{result.username} | Total post dianalisis: {result.total_posts_scraped} | "
            f"Post dengan musik: {result.posts_with_music}"
        )
        self._render_song_list(result.songs)
        self.progress.set(1.0)
        self._set_busy(False)

    def _render_song_list(self, songs: list[Song]) -> None:
        for child in self.song_container.winfo_children():
            child.destroy()
        self.song_vars.clear()

        if not songs:
            lbl = ctk.CTkLabel(
                self.song_container,
                text="Tidak ditemukan musik pada postingan akun ini. Gunakan 'Demo Mode' untuk melihat contoh.",
                text_color="gray60",
            )
            lbl.pack(padx=16, pady=24)
            return

        for song in songs:
            row = ctk.CTkFrame(self.song_container, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=3)

            var = tk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(
                row,
                text=song.display_text,
                variable=var,
                font=ctk.CTkFont(size=13),
            )
            chk.pack(side="left", padx=8)

            self.song_vars.append((song, var))

    # ----------------- PLAYLIST GENERATION (NO LOGIN REQUIRED) -----------------

    def on_create_yt_playlist(self) -> None:
        selected = self._get_selected_songs()
        if not selected:
            self.status_var.set("Pilih minimal satu lagu.")
            return

        username = (self.scrape_result.username if self.scrape_result else self._clean_username()) or "music"
        self._set_busy(True)
        self.status_var.set("Membuat playlist YouTube Music (tanpa login)...")

        def worker() -> None:
            try:
                def prog(cur: int, tot: int, msg: str) -> None:
                    self.queue.put(("progress", cur, tot, msg))

                self.yt_client.resolve_tracks(selected, progress_callback=prog)
                playlist_url = self.yt_client.create_instant_playlist(username=username, songs=selected)
                self.queue.put(("yt_done", playlist_url))
            except Exception as exc:
                self.queue.put(("error", f"YouTube Music Error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def on_create_spotify_playlist(self) -> None:
        selected = self._get_selected_songs()
        if not selected:
            self.status_var.set("Pilih minimal satu lagu.")
            return

        username = (self.scrape_result.username if self.scrape_result else self._clean_username()) or "music"
        self._set_busy(True)
        self.status_var.set("Mempersiapkan playlist Spotify (tanpa login)...")

        def worker() -> None:
            try:
                url, mode_info = self.spotify_mgr.create_playlist_from_songs(username=username, songs=selected)
                self.queue.put(("spotify_done", url, mode_info))
            except Exception as exc:
                self.queue.put(("error", f"Spotify Error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def on_create_both_playlists(self) -> None:
        selected = self._get_selected_songs()
        if not selected:
            self.status_var.set("Pilih minimal satu lagu.")
            return

        username = (self.scrape_result.username if self.scrape_result else self._clean_username()) or "music"
        self._set_busy(True)
        self.status_var.set("Membuat playlist YouTube Music & Spotify sekaligus...")

        def worker() -> None:
            try:
                # 1. YouTube Music
                self.queue.put(("progress", 1, 4, "Menghubungkan ke katalog YouTube Music..."))
                self.yt_client.resolve_tracks(selected)
                yt_url = self.yt_client.create_instant_playlist(username=username, songs=selected)
                self.queue.put(("yt_done", yt_url))

                # 2. Spotify
                self.queue.put(("progress", 3, 4, "Mencocokkan data ke Spotify..."))
                sp_url, sp_info = self.spotify_mgr.create_playlist_from_songs(username=username, songs=selected)
                self.queue.put(("spotify_done", sp_url, sp_info))

                self.queue.put(("both_done",))
            except Exception as exc:
                self.queue.put(("error", f"Gagal membuat playlist: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def on_open_yt_playlist(self) -> None:
        url = self.yt_playlist_url_var.get().strip()
        if url:
            webbrowser.open(url)

    def on_open_spotify_playlist(self) -> None:
        url = self.spotify_playlist_url_var.get().strip()
        if url:
            webbrowser.open(url)

    def on_open_html_player(self) -> None:
        selected = self._get_selected_songs()
        if not selected:
            self.status_var.set("Pilih minimal satu lagu untuk web player.")
            return

        username = (self.scrape_result.username if self.scrape_result else self._clean_username()) or "playlist"
        # Ensure tracks have preview/cover info
        for s in selected:
            if not s.cover_url or not s.preview_url:
                self.spotify_mgr.find_track(s)

        out_file = Path.cwd() / f"playlist_{username}.html"
        generate_html_player(
            output_path=out_file,
            username=username,
            songs=selected,
            yt_music_playlist_url=self.yt_playlist_url_var.get().strip() or None,
            spotify_playlist_url=self.spotify_playlist_url_var.get().strip() or None,
        )
        webbrowser.open(out_file.as_uri())
        self.status_var.set(f"Web Player dibuka di browser: {out_file.name}")

    def on_export_csv(self) -> None:
        selected = self._get_selected_songs()
        if not selected:
            self.status_var.set("Pilih minimal satu lagu untuk diexport.")
            return

        username = (self.scrape_result.username if self.scrape_result else self._clean_username()) or "music"
        output_path = filedialog.asksaveasfilename(
            title="Simpan Playlist CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"playlist_{username}.csv",
        )
        if not output_path:
            return

        export_csv(output_path, selected, username)
        self.status_var.set(f"Export CSV berhasil: {Path(output_path).name}")

    def on_export_m3u(self) -> None:
        selected = self._get_selected_songs()
        if not selected:
            self.status_var.set("Pilih minimal satu lagu untuk diexport.")
            return

        username = (self.scrape_result.username if self.scrape_result else self._clean_username()) or "music"
        output_path = filedialog.asksaveasfilename(
            title="Simpan Playlist M3U8",
            defaultextension=".m3u8",
            filetypes=[("M3U8 files", "*.m3u8"), ("M3U files", "*.m3u")],
            initialfile=f"playlist_{username}.m3u8",
        )
        if not output_path:
            return

        export_m3u(output_path, selected, username)
        self.status_var.set(f"Export M3U8 berhasil: {Path(output_path).name}")

    # ----------------- QUEUE EVENT PROCESSOR -----------------

    def _process_queue(self) -> None:
        try:
            while True:
                event = self.queue.get_nowait()
                kind = event[0]

                if kind == "progress":
                    _, current, total, message = event
                    ratio = 0.0 if total <= 0 else min(max(current / total, 0.0), 1.0)
                    self.progress.set(ratio)
                    self.status_var.set(message)

                elif kind == "scrape_done":
                    _, result = event
                    self._on_scrape_completed(result)
                    self.status_var.set(
                        f"Berhasil! Ditemukan {len(result.songs)} lagu untuk @{result.username}. Klik '⚡ Buat Playlist Keduanya' untuk memulai!"
                    )

                elif kind == "scrape_blocked":
                    _, reason, username = event
                    self._set_busy(False)
                    self.progress.set(0)
                    self.status_var.set("Akses Instagram dibatasi (403 Forbidden).")
                    self._show_cookie_required_dialog(username, reason)

                elif kind == "yt_done":
                    _, url = event
                    self.yt_playlist_url_var.set(url)
                    self.open_yt_btn.configure(state="normal")
                    self.status_var.set("Playlist YouTube Music siap dibuka!")
                    self._set_busy(False)

                elif kind == "spotify_done":
                    _, url, mode_info = event
                    self.spotify_playlist_url_var.set(url)
                    self.open_sp_btn.configure(state="normal")
                    self.status_var.set(f"{mode_info}: Siap dibuka!")
                    self._set_busy(False)

                elif kind == "both_done":
                    self.status_var.set("Sukses! Playlist YouTube Music & Spotify siap dibuka.")
                    self._set_busy(False)

                elif kind == "error":
                    _, message = event
                    self.status_var.set(f"Error: {message}")
                    self._set_busy(False)

        except Empty:
            pass

        self.after(100, self._process_queue)
