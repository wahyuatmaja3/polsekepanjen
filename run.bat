@echo off
title polsekepanjen - Instagram to Playlist
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe main.py
) else (
    python main.py
)
if errorlevel 1 pause
