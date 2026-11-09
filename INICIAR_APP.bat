@echo off
title Gerador de Relatorios Fotograficos
setlocal
cd /d "%~dp0"

:: Requer o uv (instala o Python 3.12 sozinho): https://docs.astral.sh/uv/
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O uv nao foi encontrado.
    echo Instale pelo PowerShell: irm https://astral.sh/uv/install.ps1 ^| iex
    echo Depois execute este arquivo novamente.
    pause
    exit /b 1
)

echo Preparando o ambiente...
uv sync --quiet
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao preparar o ambiente.
    pause
    exit /b 1
)

:: Compila a interface na primeira vez (precisa do Node.js 20 ou superior)
if not exist "frontend\dist\index.html" (
    where npm >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] A interface ainda nao foi compilada e o Node.js nao foi encontrado.
        echo Instale o Node.js 20 ou superior em https://nodejs.org/ e execute este arquivo novamente.
        pause
        exit /b 1
    )
    echo Compilando a interface pela primeira vez... Isso pode levar alguns minutos.
    call npm --prefix frontend ci --no-audit --no-fund
    if %errorlevel% neq 0 goto :frontend_error
    call npm --prefix frontend run build
    if %errorlevel% neq 0 goto :frontend_error
)

uv run python -m report_works --open
goto :eof

:frontend_error
echo [ERRO] Falha ao compilar a interface.
pause
exit /b 1
