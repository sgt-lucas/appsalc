import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import engine, Base
from app.routers import autenticacao, administracao, notas_credito, empenhos, dashboard, relatorios, auditoria

# Carrega as variáveis de ambiente (DATABASE_URL, SECRET_KEY) do arquivo .env
load_dotenv()

# Esta linha garante que, ao iniciar, todas as tabelas definidas em models.py
# sejam criadas no banco de dados, caso ainda não existam.
print("Iniciando aplicação e criando tabelas da base de dados, se necessário...")
Base.metadata.create_all(bind=engine)
print("Tabelas verificadas/criadas com sucesso.")

app = FastAPI(
    title="Sistema de Gestão de Notas de Crédito",
    version="3.0.0",
    description="Backend refatorado para o Sistema de Gestão de NC do 2º CGEO."
)

# Configuração do CORS (Cross-Origin Resource Sharing)
# Essencial para permitir que seu frontend (hospedado em outro lugar)
# possa se comunicar com esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, seria ideal restringir para o domínio do seu frontend.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os diferentes módulos (roteadores) da aplicação.
# Cada um é responsável por um conjunto de endpoints (ex: /token, /users, /notas-credito).
app.include_router(autenticacao.router)
app.include_router(administracao.router)
app.include_router(notas_credito.router)
app.include_router(empenhos.router)
app.include_router(dashboard.router)
app.include_router(relatorios.router)
app.include_router(auditoria.router)

@app.get("/", summary="Verificação de status da API", tags=["Status"])
def read_root():
    """Endpoint principal para verificar se a API está online."""
    return {"status": "API de Gestão de Notas de Crédito v3.0.0 no ar."}

print("Aplicação iniciada com sucesso.")