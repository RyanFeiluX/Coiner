@echo off
cd /d "%~dp0"
set IMAGEIO_FFMPEG_EXE=%~dp0ffmpeg.exe
set IMAGEMAGICK_BINARY=%~dp0magick.exe
echo Starting Coiner...
start "" http://localhost:8000
main.exe
