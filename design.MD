# PRD — polsekepanjen Desktop App
**Instagram Music → Spotify Playlist Generator**

---

## Metadata

| Field | Value |
|---|---|
| Versi | 0.1 (Draft) |
| Dibuat | 2025 |
| Platform | Windows / macOS / Linux (distribusi `.exe` / `.app` / binary) |
| Bahasa utama | Python 3.11+ |
| Status | Pre-development |

---

## 1. Ringkasan Produk

polsekepanjen adalah aplikasi desktop yang memungkinkan pengguna menemukan semua lagu yang dipakai di postingan dan Reels Instagram seseorang, lalu secara otomatis membuat playlist Spotify berisi lagu-lagu tersebut — semuanya dari satu klik, tanpa perlu membuka browser atau server eksternal.

### Masalah yang Diselesaikan

Ketika seseorang ingin tahu musik apa yang sering dipakai oleh akun Instagram tertentu (idola, teman, content creator), tidak ada cara mudah untuk melakukannya. Saat ini proses manual melibatkan membuka satu per satu postingan, mencatat nama lagu, lalu mencarinya di Spotify — proses yang menyita waktu berjam-jam untuk akun dengan ratusan postingan.

### Solusi

Aplikasi desktop Python yang:
1. Mengambil semua metadata musik dari postingan publik sebuah akun Instagram
2. Menampilkan daftar lagu yang ditemukan beserta frekuensinya
3. Mencari setiap lagu di Spotify dan membuat playlist otomatis di akun Spotify pengguna

---

## 2. Tujuan & Sasaran

### Tujuan Utama
- Mempersingkat proses "temukan musik dari IG seseorang" dari berjam-jam menjadi kurang dari 5 menit
- Menghasilkan playlist Spotify yang dapat langsung digunakan tanpa langkah tambahan

### Non-Goals (Sengaja Tidak Dikerjakan)
- Tidak mendukung akun Instagram private
- Tidak men-download video atau audio dari Instagram
- Tidak menyimpan data pengguna ke server manapun (100% lokal)
- Tidak mendukung platform musik selain Spotify di versi pertama

---

## 3. Target Pengguna

### Persona Utama: "The Music Follower"
- Penggemar yang ingin mendengarkan musik yang sama dengan idola/content creator favoritnya
- Umur 18–35 tahun, familiar dengan Spotify dan Instagram
- Tidak perlu pemahaman teknis; ekspektasinya: install, buka, masukkan username, dapat playlist

### Persona Sekunder: "The Curator"
- Seseorang yang ingin menganalisis taste musik dari beberapa akun sekaligus
- Mungkin seorang DJ, music blogger, atau social media analyst
- Menghargai fitur export dan detail frekuensi kemunculan lagu

---

## 4. Alur Pengguna (User Flow)

```
[Buka App]
    │
    ▼
[Masukkan @username Instagram]
    │
    ├── Akun private? ──► [Tampilkan error: akun tidak bisa diakses]
    │
    ▼
[Preview profil: foto, nama, jumlah post]
    │
    ▼
[Klik "Mulai Scraping"]
    │
    ▼
[Progress bar real-time: "Mengambil post 45 dari 230..."]
    │
    ▼
[Tampilkan daftar lagu]
    │   - Nama lagu + artis
    │   - Cover art (dari Spotify)
    │   - Jumlah kemunculan di postingan
    │   - Checkbox untuk include/exclude
    │
    ▼
[Login Spotify via browser (sekali saja, token disimpan lokal)]
    │
    ▼
[Klik "Buat Playlist Spotify"]
    │
    ▼
[Sistem: search setiap lagu → create playlist → add tracks]
    │
    ▼
[Sukses: tampilkan link playlist + tombol "Buka di Spotify"]
```

---

## 5. Arsitektur Teknis

### 5.1 Ringkasan Arsitektur

Seluruh aplikasi berjalan dalam **satu proses Python** di komputer pengguna. Tidak ada server eksternal, tidak ada database cloud, tidak ada proxy. Semua komunikasi jaringan dilakukan langsung dari aplikasi ke Instagram dan Spotify API.

```
┌─────────────────────────────────────────────────────┐
│                  polsekepanjen.exe                     │
│                                                     │
│  ┌─────────────┐   ┌──────────────┐  ┌──────────┐  │
│  │  GUI Layer  │──►│  Scraping    │  │ Spotify  │  │
│  │ (CTk/PyQt) │   │  Engine      │  │ Module   │  │
│  │            │   │ (Instaloader)│  │(Spotipy) │  │
│  └─────────────┘   └──────┬───────┘  └────┬─────┘  │
│                           │               │        │
│              ┌────────────▼───────────────▼──────┐ │
│              │     Threading / Queue Manager     │ │
│              │  (background thread, GUI tetap    │ │
│              │   responsif selama scraping)      │ │
│              └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
        │                          │
        ▼                          ▼
  Instagram.com            api.spotify.com
  (HTTP scraping)          (REST API + OAuth)
```

### 5.2 Tech Stack

| Komponen | Library | Alasan Dipilih |
|---|---|---|
| GUI | `customtkinter` | Modern look, mudah dipakai, pure Python |
| IG Scraping | `instaloader` | Open source, aktif dimaintain, handle session |
| Spotify API | `spotipy` | Wrapper resmi, support PKCE OAuth |
| Background tasks | `threading` + `queue.Queue` | Standar library, cukup untuk use case ini |
| Config/token | `keyring` + JSON lokal | Simpan token Spotify dengan aman di OS credential store |
| Packaging | `PyInstaller` | Single-file `.exe`, proven, support semua OS |
| HTTP | `requests` (sudah include di instaloader) | — |

### 5.3 Struktur Direktori

```
polsekepanjen/
│
├── main.py                  # Entry point, inisialisasi app
│
├── gui/
│   ├── __init__.py
│   ├── app_window.py        # Window utama
│   ├── components/
│   │   ├── search_panel.py  # Input username + tombol scrape
│   │   ├── song_list.py     # Daftar lagu dengan checkbox
│   │   ├── progress_bar.py  # Progress scraping real-time
│   │   └── result_panel.py  # Link playlist + tombol open Spotify
│   └── assets/
│       └── icon.ico
│
├── core/
│   ├── __init__.py
│   ├── scraper.py           # Wrapper Instaloader, ekstrak music_info
│   ├── spotify.py           # Auth, search, create playlist
│   ├── models.py            # Dataclass: Song, PostMusic, ScrapingResult
│   └── cache.py             # Cache hasil scraping (JSON lokal, TTL 24 jam)
│
├── config/
│   ├── settings.py          # Spotify client_id, redirect URI, konstanta
│   └── .spotify_token.json  # Token OAuth (di-gitignore, disimpan lokal)
│
├── requirements.txt
├── build.spec               # PyInstaller spec file
└── README.md
```

### 5.4 Model Data

```python
# core/models.py

@dataclass
class Song:
    title: str
    artist: str
    spotify_uri: str | None = None      # Diisi setelah Spotify search
    cover_url: str | None = None
    occurrence_count: int = 1
    found_on_spotify: bool = False

@dataclass
class ScrapingResult:
    username: str
    profile_pic_url: str
    total_posts_scraped: int
    songs: list[Song]                   # Sudah deduplikasi + diurutkan
    posts_with_music: int
    posts_without_music: int
    scraped_at: datetime
```

---

## 6. Fitur & Prioritas (MVP)

### P1 — Harus Ada di Versi Pertama

| ID | Fitur | Deskripsi |
|---|---|---|
| F01 | Input username IG | Input field dengan validasi format `@username`. Auto-strip `@` jika user ketik dengan prefix. |
| F02 | Cek akun public/private | Sebelum scraping, validasi apakah akun bisa diakses. Tampilkan error yang jelas jika private. |
| F03 | Preview profil | Tampilkan foto profil, nama display, dan jumlah total post sebelum user konfirmasi scraping. |
| F04 | Scraping dengan progress | Ambil semua post publik. Update progress bar setiap post diproses. Bisa di-cancel di tengah jalan. |
| F05 | Daftar lagu hasil scraping | Tampilkan lagu unik, urut berdasarkan frekuensi tertinggi. Setiap item ada checkbox include/exclude. |
| F06 | Spotify OAuth login | Buka browser untuk login Spotify. Setelah auth, simpan token secara lokal. Tidak perlu login ulang di sesi berikutnya selama token masih valid. |
| F07 | Buat playlist Spotify | Search setiap lagu di Spotify → tambahkan ke playlist baru. Nama playlist: `Music of @username`. Deskripsi: `Generated by polsekepanjen`. |
| F08 | Link hasil playlist | Setelah berhasil, tampilkan URL playlist dan tombol untuk membuka langsung di Spotify app/browser. |

### P2 — Penting, Tapi Bisa Masuk Versi Berikutnya

| ID | Fitur | Deskripsi |
|---|---|---|
| F09 | Cover art lagu | Ambil dari Spotify search result, tampilkan thumbnail di daftar lagu. |
| F10 | Cache hasil scraping | Simpan hasil scraping per username di JSON lokal dengan TTL 24 jam. Saat username yang sama dicari lagi, tawari opsi "gunakan data kemarin" atau "scrape ulang". |
| F11 | Export daftar lagu | Tombol export ke `.csv` atau `.txt` berisi nama lagu + artis + jumlah kemunculan. |
| F12 | Batas jumlah post | Opsi untuk membatasi scraping ke N post terbaru (default: semua, pilihan: 50 / 100 / 200 / semua). |
| F13 | Lagu tidak ditemukan | Tampilkan secara terpisah lagu yang tidak berhasil dicocokkan di Spotify, beserta nama aslinya dari Instagram. |

### P3 — Nice to Have

| ID | Fitur | Deskripsi |
|---|---|---|
| F14 | History pencarian | Simpan riwayat username yang pernah dicari di sidebar. Klik untuk load ulang. |
| F15 | Dark / light mode | Toggle tema. Default ikut setting OS. |
| F16 | Multi-akun scraping | Scrape 2–3 username sekaligus, gabungkan hasil jadi satu playlist. |

---

## 7. Kendala Teknis & Mitigasi

### 7.1 Instagram Tidak Punya Official Music API

**Masalah:** Meta tidak menyediakan endpoint publik untuk metadata musik dari Reels/post. Data diambil dari field `music_info` yang tersedia di response HTML/GraphQL Instagram.

**Mitigasi:**
- Gunakan `instaloader` yang secara aktif dimaintain dan update mengikuti perubahan Instagram
- Siapkan fallback: jika `music_info` tidak tersedia di suatu post, skip dan lanjut ke post berikutnya
- Implementasi delay acak (1–3 detik) antar request untuk hindari rate limiting

### 7.2 Instagram Bisa Throttle / Block IP

**Masalah:** Scraping agresif dapat memicu temporary block dari Instagram.

**Mitigasi:**
- Default delay 1.5 detik antar post (bisa dikonfigurasi)
- Cache hasil scraping selama 24 jam — tidak perlu scrape ulang jika data masih fresh
- Tampilkan pesan yang jelas jika Instagram mengembalikan error 429 atau redirect ke login page

### 7.3 Banyak Lagu di Instagram Adalah "Original Audio"

**Masalah:** Banyak konten Instagram menggunakan audio original creator, bukan lagu berlisensi dari Spotify. Lagu jenis ini tidak akan ditemukan di Spotify.

**Mitigasi:**
- Filter hanya item yang memiliki field `artist_name` yang valid (bukan string kosong atau generic)
- Tampilkan statistik: "X lagu ditemukan di Spotify, Y lagu original audio (tidak ditambahkan)"
- Untuk lagu yang tidak ditemukan, coba fuzzy search dengan nama yang dipotong/dibersihkan

### 7.4 Mismatch Antara Nama Lagu di IG dan Spotify

**Masalah:** Judul lagu di Instagram kadang tidak identik dengan judul di Spotify (ada versi remix, feat., dll.).

**Mitigasi:**
- Search query: `{title} {artist}` → ambil result pertama jika confidence cukup tinggi
- Jika tidak ketemu, coba search hanya dengan `{title}` saja
- Tandai lagu yang "mungkin tidak akurat" jika hasil search sangat berbeda dari query

### 7.5 Spotify OAuth Membutuhkan Redirect URI

**Masalah:** OAuth membutuhkan callback URL. Di desktop app, tidak ada web server yang berjalan.

**Solusi:** Gunakan `localhost` sebagai redirect URI:
- Redirect URI: `http://localhost:8888/callback`
- Spotipy menjalankan temporary HTTP server lokal hanya saat proses auth berlangsung
- Setelah token didapat, server lokal langsung dimatikan
- Token disimpan di OS keyring (Windows Credential Manager / macOS Keychain)

---

## 8. Setup Spotify Developer App

Langkah yang perlu dilakukan developer (sekali, sebelum build):

1. Buka [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create App → isi nama "polsekepanjen"
3. Di Settings → Redirect URIs → tambahkan: `http://localhost:8888/callback`
4. Copy `Client ID` (tidak perlu Client Secret untuk PKCE flow)
5. Masukkan ke `config/settings.py`:

```python
SPOTIFY_CLIENT_ID = "your_client_id_here"
SPOTIFY_REDIRECT_URI = "http://localhost:8888/callback"
SPOTIFY_SCOPE = "playlist-modify-public playlist-modify-private"
```

> **Catatan:** Aplikasi ini menggunakan Authorization Code dengan PKCE, sehingga `client_secret` tidak diperlukan dan tidak perlu disimpan di kode — aman untuk distribusi publik.

---

## 9. Cara Build ke .exe

### Requirements

```
customtkinter>=5.2.0
instaloader>=4.10
spotipy>=2.23.0
keyring>=24.0.0
Pillow>=10.0.0
requests>=2.31.0
pyinstaller>=6.0.0
```

### Build Command

```bash
# Install dependencies
pip install -r requirements.txt

# Build single-file executable
pyinstaller --onefile --windowed --icon=gui/assets/icon.ico \
  --name "polsekepanjen" \
  --add-data "gui/assets:gui/assets" \
  main.py
```

### Output

File `.exe` (Windows) atau binary (macOS/Linux) akan tersedia di folder `dist/`. Ukuran estimasi: 40–80 MB (termasuk Python runtime dan semua dependency).

### Build per Platform

| Platform | Perintah tambahan | Output |
|---|---|---|
| Windows | Jalankan di Windows, tambah `--version-file` | `dist/polsekepanjen.exe` |
| macOS | Jalankan di macOS, tambah `--osx-bundle-identifier` | `dist/polsekepanjen.app` |
| Linux | Jalankan di Linux | `dist/polsekepanjen` (binary) |

> PyInstaller tidak mendukung cross-compile. Build untuk Windows harus dilakukan di Windows, dst.

---

## 10. Estimasi Pengerjaan

| Fase | Scope | Estimasi |
|---|---|---|
| **Setup & Boilerplate** | Struktur project, requirements, config Spotify | 1–2 hari |
| **Core Scraping** | Instaloader wrapper, ekstrak music_info, deduplication | 3–4 hari |
| **GUI Dasar** | Window utama, input, progress bar, song list | 3–4 hari |
| **Spotify Integration** | OAuth, search, create playlist | 2–3 hari |
| **Polish & Error Handling** | Edge cases, pesan error, UX refinement | 2–3 hari |
| **Packaging & Testing** | PyInstaller build, test di OS target | 1–2 hari |
| **Total** | | **~2–3 minggu** |

---

## 11. Risiko Utama

| Risiko | Probabilitas | Dampak | Mitigasi |
|---|---|---|---|
| Instagram mengubah struktur response dan instaloader belum update | Sedang | Tinggi | Monitor GitHub instaloader, siapkan fallback manual parsing |
| Banyak lagu tidak ditemukan di Spotify | Tinggi | Sedang | Tampilkan transparansi data, tidak merusak UX keseluruhan |
| Akun yang dicari punya ribuan post → scraping lambat | Sedang | Sedang | Tambah opsi batas jumlah post, tampilkan estimasi waktu |
| Instagram block IP user saat scraping | Rendah | Tinggi | Delay antar request, instruksi jelas di README jika terjadi |
| Token Spotify expired dan flow refresh gagal | Rendah | Rendah | Tangkap error, minta user login ulang dengan satu klik |

---

## 12. Referensi

- [Instaloader Documentation](https://instaloader.github.io/)
- [Spotipy Documentation](https://spotipy.readthedocs.io/)
- [Spotify Web API — Create Playlist](https://developer.spotify.com/documentation/web-api/reference/create-playlist)
- [Spotify Authorization Guide (PKCE)](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
- [CustomTkinter GitHub](https://github.com/TomSchimansky/CustomTkinter)
- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)

---

*PRD ini dibuat sebagai panduan implementasi untuk LLM atau developer yang akan membangun polsekepanjen dari awal. Setiap bagian dirancang untuk dapat langsung dieksekusi tanpa perlu klarifikasi lebih lanjut.*
