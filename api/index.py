import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Adiciona o diretório da API ao caminho do Python para garantir que os módulos sejam encontrados
sys.path.insert(0, os.path.dirname(__file__))

# As importações agora são absolutas a partir da pasta 'app'
from app.database import engine, Base
from app.routers import autenticacao, administracao, notas_credito, empenhos, dashboard, relatorios, auditoria

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Aplicação a arrancar...")
    # Isto agora só acontece no arranque, quando as variáveis de ambiente estão disponíveis.
    Base.metadata.create_all(bind=engine)
    print("Tabelas verificadas/criadas com sucesso.")
    yield
    print("Aplicação a desligar.")

app = FastAPI(
    title="Sistema de Gestão de Notas de Crédito",
    version="4.0.0",
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

# Adiciona um prefixo /api a todos os endpoints para corresponder à configuração da Vercel
api_router = APIRouter(prefix="/api")

api_router.include_router(autenticacao.router)
api_router.include_router(administracao.router)
api_router.include_router(notas_credito.router)
api_router.include_router(empenhos.router)
api_router.include_router(dashboard.router)
api_router.include_router(relatorios.router)
api_router.include_router(auditoria.router)

app.include_router(api_router)

@app.get("/api", summary="Verificação de status da API", tags=["Status"])
def read_root():
    """Endpoint principal para verificar se a API está online."""
    return {"status": "API de Gestão de Notas de Crédito v4.0.0 no ar."}