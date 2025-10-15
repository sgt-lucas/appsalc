import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# CORREÇÃO: Importações absolutas
from app import models, schemas
from app.database import get_db

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

if not SECRET_KEY:
    raise RuntimeError("FATAL: A variável de ambiente SECRET_KEY não está configurada.")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token") # CORREÇÃO: Caminho completo para o token

router = APIRouter(
    tags=["Autenticação"]
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def log_audit_action(db: Session, username: str, action: str, details: str = None):
    log = models.AuditLog(username=username, action=action, details=details)
    db.add(log)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas. Por favor, faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.ADMINISTRADOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return current_user

@router.post("/token", response_model=schemas.Token, summary="Autentica o utilizador e retorna um token JWT")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        log_audit_action(db, form_data.username, "LOGIN_FAILED", "Tentativa de login com credenciais incorretas")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilizador ou senha incorretos")

    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    log_audit_action(db, user.username, "LOGIN_SUCCESS")
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=schemas.UserInDB, summary="Retorna informações do utilizador logado")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user