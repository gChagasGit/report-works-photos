@echo off
title Gerador de Relatórios Fotográficos
setlocal

echo ======================================================
echo   INSTALADOR AUTOMATICO - RELATORIO DE OBRAS
echo ======================================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python pela Microsoft Store ou pela site oficial (python.org).
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
    pip install --upgrade pip --quiet
    if exist "requirements.txt" (
        pip install -r requirements.txt --quiet
    ) else (
        echo [ERRO] Arquivo requirements.txt nao encontrado!
        pause
        exit /b
    )
)

:: 3. Rodar o App
echo Iniciando interface...
call .venv\Scripts\activate 
streamlit run app.py

pause