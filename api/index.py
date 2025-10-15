import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Adiciona o diretório da API ao caminho do Python para garantir que os módulos sejam encontrados
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, Base
from app.routers import autenticacao, administracao, notas_credito, empenhos, dashboard, relatorios, auditoria

# Carrega as variáveis de ambiente (só funciona localmente, não na Vercel)
load_dotenv()

# Função de Lifespan: O código aqui só é executado quando a aplicação arranca.
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Aplicação a arrancar...")
    # Garante que as tabelas sejam criadas no banco de dados, se necessário.
    # Isto agora só acontece no arranque, quando as variáveis de ambiente estão disponíveis.
    Base.metadata.create_all(bind=engine)
    print("Tabelas verificadas/criadas com sucesso.")
    yield
    print("Aplicação a desligar.")

# Cria a aplicação FastAPI com o gestor de lifespan
app = FastAPI(
    title="Sistema de Gestão de Notas de Crédito",
    version="3.0.0",
    description="Backend refatorado para o Sistema de Gestão de NC do 2º CGEO.",
    lifespan=lifespan
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os diferentes módulos (roteadores) da aplicação
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
    return {"status": "API de Gestão de Notas de Crédito v3.0.0 no ar."}