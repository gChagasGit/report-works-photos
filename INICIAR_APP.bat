@echo off
title Gerador de Relatorios Fotograficos
setlocal

:: Requer apenas o uv (ele instala o Python 3.12 sozinho): https://docs.astral.sh/uv/
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

echo Iniciando Servidor Backend (FastAPI) em http://127.0.0.1:8000/docs
uv run python main.py
