import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("FATAL: A variável de ambiente DATABASE_URL não está configurada.")

# Pequena correção para compatibilidade com o Heroku/Render que usam "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Função de dependência para ser usada nos endpoints.
# Garante que cada requisição tenha sua própria sessão de banco de dados
# e que a conexão seja fechada ao final.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()