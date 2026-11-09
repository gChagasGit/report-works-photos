import os
import yaml
import tkinter as tk
from tkinter import filedialog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Gerador de Relatórios API")

# Configuração de CORS para permitir que o frontend (React) faça requisições locais
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConfigData(BaseModel):
    config: dict

@app.get("/api/config")
def get_config():
    """Retorna os dados do arquivo config.yaml"""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

@app.post("/api/config")
def save_config(data: ConfigData):
    """Salva as configurações alteradas no frontend de volta no arquivo YAML"""
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data.config, f, allow_unicode=True)
    return {"message": "Configuração salva com sucesso!"}

@app.get("/api/select-folder")
def select_folder(default_path: str = ""):
    """Abre a janela do Windows para selecionar uma pasta (via Tkinter)"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(initialdir=default_path or os.getcwd())
    root.destroy()
    return {"path": path}

@app.get("/api/select-file")
def select_file(default_path: str = ""):
    """Abre a janela do Windows para selecionar o arquivo Excel (via Tkinter)"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askopenfilename(
        initialdir=default_path or os.getcwd(), 
        filetypes=[("Excel files", "*.xlsx")]
    )
    root.destroy()
    return {"path": path}

if __name__ == "__main__":
    import uvicorn
    # Executa o servidor localmente na porta 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)