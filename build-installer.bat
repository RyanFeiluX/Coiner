@echo off
setlocal enabledelayedexpansion

set "VERSION="
set "SKIP_VUE="
set "SKIP_PYINSTALLER="
set "SKIP_STAGE="
set "SKIP_COMPILE="

REM --- Parse arguments ---
:parse
if "%~1"=="" goto :endparse
if /i "%~1"=="-SkipVue" set "SKIP_VUE=1" & shift & goto :parse
if /i "%~1"=="-SkipPyInstaller" set "SKIP_PYINSTALLER=1" & shift & goto :parse
if /i "%~1"=="-SkipStage" set "SKIP_STAGE=1" & shift & goto :parse
if /i "%~1"=="-SkipCompile" set "SKIP_COMPILE=1" & shift & goto :parse
echo Unknown option: %~1 & exit /b 1
:endparse

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

REM --- Read version from config.toml ---
for /f "tokens=2 delims==" %%a in ('findstr /b "project_version" "%ROOT%\config.toml" 2^>nul') do set "VERSION=%%a"
set "VERSION=!VERSION: =!"
set "VERSION=!VERSION:"=!
if "!VERSION!"=="" (
    echo Error: project_version not found in config.toml
    exit /b 1
)
echo Target version: !VERSION!

REM ============================================================
REM Step 1: Build Vue frontend
REM ============================================================
if not defined SKIP_VUE (
    echo.
    echo === Build Vue frontend ===
    pushd "%ROOT%\vue-frontend"
    if not exist "node_modules" (
        echo Installing npm dependencies...
        call npm ci --no-audit --no-fund
    )
    call npm run build
    popd
)

REM ============================================================
REM Step 2: Copy Vue dist to resource/public
REM ============================================================
echo.
echo === Copy Vue dist to resource/public ===
if exist "%ROOT%\vue-frontend\dist" (
    if exist "%ROOT%\resource\public" rmdir /s /q "%ROOT%\resource\public"
    mkdir "%ROOT%\resource\public" >nul 2>&1
    xcopy /e /i /q "%ROOT%\vue-frontend\dist\*" "%ROOT%\resource\public\" >nul
    echo Copied Vue dist to resource/public
) else (
    echo Warning: Vue dist not found, skipping
)

REM ============================================================
REM Step 3: Install Python dependencies in condaenv-coiner
REM ============================================================
echo.
echo === Install Python dependencies ===
set "CONDA_ENV_PY=D:\ProgramData\anaconda3\envs\condaenv-coiner\python.exe"
if not exist "%CONDA_ENV_PY%" (
    echo Error: condaenv-coiner not found at %CONDA_ENV_PY%
    echo Please create it first using: conda create -n condaenv-coiner python=3.11
    exit /b 1
)
"%CONDA_ENV_PY%" -m pip install -r "%ROOT%\requirements.txt" >nul 2>&1
"%CONDA_ENV_PY%" -m pip install pyinstaller >nul 2>&1
echo Python dependencies installed (condaenv-coiner)

REM ============================================================
REM Step 4: Build with PyInstaller
REM ============================================================
if not defined SKIP_PYINSTALLER (
    echo.
    echo === Build with PyInstaller ===
    rmdir /s /q "%ROOT%\dist" 2>nul
    rmdir /s /q "%ROOT%\build" 2>nul
    del "%ROOT%\*.spec" 2>nul

    "%CONDA_ENV_PY%" -m PyInstaller --onedir --name coiner "%ROOT%\main.py" ^
        --hidden-import uvicorn.logging ^
        --hidden-import uvicorn.loops.auto ^
        --hidden-import uvicorn.loops.asyncio ^
        --hidden-import uvicorn.protocols.http.auto ^
        --hidden-import uvicorn.protocols.http.h11_impl ^
        --hidden-import uvicorn.protocols.websockets.auto ^
        --hidden-import uvicorn.protocols.websockets.wsproto_impl ^
        --hidden-import dashscope ^
        --hidden-import google.generativeai ^
        --hidden-import azure.cognitiveservices.speech ^
        --hidden-import faster_whisper ^
        --hidden-import ctranslate2 ^
        --collect-submodules app

    echo PyInstaller output at: %ROOT%\dist\coiner
)

REM ============================================================
REM Step 5: Stage installer files
REM ============================================================
if not defined SKIP_STAGE (
    echo.
    echo === Stage installer files ===
    set "STAGE=%ROOT%\build-installer"
    rmdir /s /q "!STAGE!" 2>nul
    mkdir "!STAGE!\_internal" >nul 2>&1

    if exist "%ROOT%\dist\coiner\coiner.exe" (
        copy /y "%ROOT%\dist\coiner\coiner.exe" "!STAGE!\main.exe" >nul
        xcopy /e /i /q "%ROOT%\dist\coiner\_internal\*" "!STAGE!\_internal\" >nul
    ) else (
        echo Warning: PyInstaller output not found
    )

    if exist "%ROOT%\resource" (
        xcopy /e /i /q "%ROOT%\resource\*" "!STAGE!\resource\" >nul
    )
    copy /y "%ROOT%\config.example.toml" "!STAGE!\config.toml" >nul
    powershell -NoProfile -Command "$f='!STAGE!\config.toml'; $v='!VERSION!'; $c=Get-Content $f -Raw; if($c -match '(?m)^project_version\s*=.*$'){$c=[regex]::Replace($c,'(?m)^project_version\s*=.*$','project_version = \"'+$v+'\"')}else{$c='project_version = \"'+$v+'\"'+[Environment]::NewLine+$c}; Set-Content $f -Value $c -NoNewLine"
    copy /y "%ROOT%\installer\start.bat" "!STAGE!\start.bat" >nul
    if exist "%ROOT%\LICENSE" copy /y "%ROOT%\LICENSE" "!STAGE!\LICENSE" >nul

    echo Installer files staged at: !STAGE!
)

REM ============================================================
REM Step 6: Compile installer with Inno Setup
REM ============================================================
if not defined SKIP_COMPILE (
    echo.
    echo === Compile installer with Inno Setup ===
    set "ISCC="
    where iscc.exe >nul 2>&1
    if not errorlevel 1 (
        set "ISCC=iscc.exe"
    )
    if "!ISCC!"=="" (
        for /f "skip=2 tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" /v InstallLocation 2^>nul') do set "ISCC=%%b\ISCC.exe"
    )
    if "!ISCC!"=="" (
        for /f "skip=2 tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" /v InstallLocation 2^>nul') do set "ISCC=%%b\ISCC.exe"
    )
    if "!ISCC!"=="" (
        for /f "skip=2 tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1" /v InstallLocation 2^>nul') do set "ISCC=%%b\ISCC.exe"
    )
    if "!ISCC!"=="" (
        for /f "skip=2 tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 5_is1" /v InstallLocation 2^>nul') do set "ISCC=%%b\ISCC.exe"
    )
    if "!ISCC!"=="" (
        echo Inno Setup not found. Install via: choco install innosetup
        echo Or download from: https://jrsoftware.org/isdl.php
        exit /b 1
    )

    "!ISCC!" "%ROOT%\installer\installer.iss" /DMyAppVersion="%VERSION%" /DStageDir="%ROOT%\build-installer"

    echo.
    echo ============================================
    echo Installer compiled successfully!
    dir "%ROOT%\installer\output\*.exe" /b
    echo ============================================
)

endlocal
