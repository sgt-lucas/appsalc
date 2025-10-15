import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# --- INÍCIO DA CORREÇÃO CRÍTICA ---
# Adiciona o diretório 'api' e o diretório 'api/app' ao caminho de pesquisa do Python
# Isto garante que 'from app...' e 'from ..' funcionem de forma fiável
API_DIR = os.path.dirname(__file__)
sys.path.insert(0, API_DIR)
sys.path.insert(0, os.path.join(API_DIR, 'app'))
# --- FIM DA CORREÇÃO CRÍTICA ---

from app.database import engine, Base
from app.routers import autenticacao, administracao, notas_credito, empenhos, dashboard, relatorios, auditoria

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Aplicação a arrancar...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas verificadas/criadas com sucesso.")
    yield
    print("Aplicação a desligar.")

app = FastAPI(
    title="Sistema de Gestão de Notas de Crédito",
    version="3.1.0",
    description="Backend refatorado para o Sistema de Gestão de NC do 2º CGEO.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(autenticacao.router)
app.include_router(administracao.router)
app.include_router(notas_credito.router)
app.include_router(empenhos.router)
app.include_router(dashboard.router)
app.include_router(relatorios.router)
app.include_router(auditoria.router)

@app.get("/api", summary="Verificação de status da API", tags=["Status"])
def read_root():
    """Endpoint principal para verificar se a API está online."""
    return {"status": "API de Gestão de Notas de Crédito v3.1.0 no ar."}