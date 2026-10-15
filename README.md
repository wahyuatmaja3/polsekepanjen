# polsekepanjen — Instagram Music to Spotify & YouTube Music Playlist

Aplikasi desktop cerdas untuk mengekstrak lagu dari postingan/Reels Instagram dan menghasilkan playlist **Spotify** serta **YouTube Music** **tanpa mewajibkan pengguna untuk login ke akun Spotify atau YouTube Music mereka!**

---

## 🎯 Masalah & Solusi Arsitektur (Zero-Login)

### Masalah Utama
Pengguna umum sering enggan atau ragu untuk login / menghubungkan akun Spotify atau Google/YouTube pribadi mereka ke aplikasi desktop pihak ketiga karena faktor privasi dan kerumitan izin OAuth.

### Solusi yang Diimplementasikan

| Platform | Solusi Tanpa Login Pengguna | Cara Kerja |
|---|---|---|
| **YouTube Music** | **Instant Multi-Track Queue (`watch_videos`)** | Aplikasi mencari video ID setiap lagu menggunakan katalog YouTube Music (tanpa login & tanpa API key), lalu mengompilasi semua ID lagu ke endpoint antrean multi-video instan. Pengguna cukup klik link untuk langsung memutar seluruh lagu secara berurutan di YouTube Music, dan dapat menyimpannya ke library mereka dengan 1 klik. |
| **Spotify (Mode A)** | **Bot / Curator Host Account** | Jika pengembang/admin mengisi token Bot Spotify di `.env`, aplikasi membuat playlist **publik** menggunakan akun Bot tersebut. Pengguna menerima URL publik (`open.spotify.com/playlist/...`), membukanya, dan langsung dapat mendengarkan serta mem-follow playlist tanpa perlu login di dalam aplikasi. |
| **Spotify (Mode B)** | **Direct Search & Web Player** | Jika tanpa token Bot, aplikasi menggunakan resolver metadata (Spotify Client Credentials / iTunes Search API) untuk menyusun link pencarian instan dan pemutar web mandiri. |
| **Universal** | **Interactive Web Player & Export** | Menghasilkan file player HTML mandiri (`playlist_username.html`) lengkap dengan pemutar audio 30 detik & cover art, serta file export `.m3u8` dan `.csv`. |

---

## 🚀 Fitur Unggulan

1. **100% Zero-Cookie & Zero-Login Mode (Default)**: Masukkan username Instagram apa saja, aplikasi langsung mencarikan musik dan lagu terkait secara otomatis lewat katalog terbuka tanpa meminta login atau cookie apa pun dari pengguna!
2. **Urutan Postingan & Rilis Paling Baru (Newest First)**: Lagu-lagu diurutkan secara kronologis mulai dari yang paling baru (#1 = postingan/rilis paling baru). Begitu jumlah target lagu terpenuhi (misal 10 lagu), pemindaian langsung berhenti seketika.
3. **Dual Output Playlist**:
   - ▶ **YouTube Music Playlist**: Antrean instan multi-track siap putar (0 login).
   - 🎧 **Spotify Playlist**: Playlist publik / tautan lagu langsung (0 login).
4. **Web Player Interaktif 🌐**: Buka hasil playlist dalam tampilan web HTML modern yang memutar sampel lagu dan menampilkan cover album.
5. **Dukungan Ekspor**: Simpan daftar lagu ke format `.csv` atau `.m3u8`.
6. **Input Lagu Manual 📝 & Cookie IG 🔑 (Opsional)**: Tersedia opsi input manual atau upload `cookies.txt` jika Anda ingin scraping live postingan secara spesifik.

---

## 💻 Cara Menjalankan

### 1. Prasyarat
- Python 3.10+
- Virtual environment sudah disiapkan di folder `.venv`

### 2. Instalasi Dependensi
```bash
.\.venv\Scripts\pip install -r requirements.txt
```

### 3. Menjalankan Aplikasi
```bash
.\.venv\Scripts\python.exe main.py
```

---

## ⚙️ Konfigurasi Opsional (`.env`)

Aplikasi dapat langsung digunakan **tanpa konfigurasi apa pun**. Namun jika Anda ingin mengaktifkan pembuatan playlist publik Spotify otomatis via akun Bot:

1. Salin `.env.example` menjadi `.env`
2. Isi nilai berikut:
   ```env
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   SPOTIFY_BOT_REFRESH_TOKEN=your_bot_refresh_token
   ```
