@echo off
title Gerador de Relatórios Fotográficos
setlocal

echo ======================================================
echo   INSTALADOR AUTOMATICO - RELATORIO DE OBRAS
echo ======================================================
echo.

:: 1. Verificar se o Python existe e se a versão é compatível (Min 3.12)
python -c "import sys; exit(0) if sys.version_info >= (3, 12) else exit(1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado ou versao desatualizada!
    echo.
    echo Requisitos: Python 3.12 ou superior.
    echo.
    echo O que fazer?
    echo 1. Abra a Microsoft Store.
    echo 2. Pesquise por "Python 3.12" e instale.
    echo 3. Apos instalar, execute este arquivo novamente.
    echo.
    pause
    exit /b
)

:: 2. Criar Ambiente Virtual se nao existir
if not exist ".venv" (
    echo [1/2] Criando ambiente isolado... Isso ocorre apenas na primeira vez.
    python -m venv .venv

    :: 2.1. Instalar Dependencias
    echo [2/2] Instalando bibliotecas necessarias... Aguarde.
    call .venv\Scripts\activate 
    python -m pip install --upgrade pip --quiet
    if exist "requirements.txt" (
        pip install -r requirements.txt --quiet
    ) else (
        echo [ERRO] Arquivo requirements.txt nao encontrado!
        pause
        exit /b
    )
)

:: Garante que as novas dependencias do Backend (FastAPI) estao instaladas
call .venv\Scripts\activate 
python -m pip install fastapi uvicorn pydantic --quiet

:: 3. Rodar o App
echo Iniciando Servidor Backend (FastAPI)...
call .venv\Scripts\activate 
python main.py