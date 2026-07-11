@echo off
title Coiner - Backend API (:8000)
cd /d "%~dp0"
echo Starting Coiner...
start "" http://localhost:8000
main.exe
