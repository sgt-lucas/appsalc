from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# CORREÇÃO: Importações absolutas
from app import models, schemas
from app.database import get_db
from app.routers.autenticacao import get_current_admin_user, get_current_user, get_password_hash, log_audit_action

router = APIRouter(
    prefix="/admin",
    tags=["Administração"],
    dependencies=[Depends(get_current_admin_user)]
)

@router.post("/users", response_model=schemas.UserInDB, status_code=status.HTTP_201_CREATED, summary="Cria um novo utilizador")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), admin_user: models.User = Depends(get_current_admin_user)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Nome de utilizador já existe")
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="E-mail já registado")
    try:
        hashed_password = get_password_hash(user.password)
        new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_password, role=user.role)
        db.add(new_user)
        log_audit_action(db, admin_user.username, "USER_CREATED", f"Utilizador '{user.username}' criado com perfil '{user.role.value}'.")
        db.commit()
        db.refresh(new_user)
        return new_user
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ocorreu um erro ao criar o utilizador.")

@router.get("/users", response_model=List[schemas.UserInDB], summary="Lista todos os utilizadores")
def read_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.username).all()

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui um utilizador")
def delete_user(user_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(get_current_admin_user)):
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Não é permitido excluir o próprio utilizador.")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")
    username = db_user.username
    db.delete(db_user)
    log_audit_action(db, admin_user.username, "USER_DELETED", f"Utilizador '{username}' (ID: {user_id}) foi excluído.")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/secoes", response_model=schemas.SeçãoInDB, status_code=status.HTTP_201_CREATED, summary="Adiciona uma nova seção")
def create_secao(secao: schemas.SeçãoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        db_secao = models.Seção(nome=secao.nome)
        db.add(db_secao)
        log_audit_action(db, current_user.username, "SECTION_CREATED", f"Seção '{secao.nome}' criada.")
        db.commit()
        db.refresh(db_secao)
        return db_secao
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Uma seção com este nome já existe.")

@router.get("/secoes", response_model=List[schemas.SeçãoInDB], summary="Lista todas as seções", dependencies=[Depends(get_current_user)])
def read_secoes(db: Session = Depends(get_db)):
    return db.query(models.Seção).order_by(models.Seção.nome).all()

@router.put("/secoes/{secao_id}", response_model=schemas.SeçãoInDB, summary="Atualiza o nome de uma seção")
def update_secao(secao_id: int, secao_update: schemas.SeçãoCreate, db: Session = Depends(get_db), admin_user: models.User = Depends(get_current_admin_user)):
    db_secao = db.query(models.Seção).filter(models.Seção.id == secao_id).first()
    if not db_secao:
        raise HTTPException(status_code=404, detail="Seção não encontrada.")
    old_name = db_secao.nome
    db_secao.nome = secao_update.nome
    try:
        log_audit_action(db, admin_user.username, "SECTION_UPDATED", f"Seção '{old_name}' (ID: {secao_id}) renomeada para '{secao_update.nome}'.")
        db.commit()
        db.refresh(db_secao)
        return db_secao
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Uma seção com este novo nome já existe.")

@router.delete("/secoes/{secao_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui uma seção")
def delete_secao(secao_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(get_current_admin_user)):
    db_secao = db.query(models.Seção).filter(models.Seção.id == secao_id).first()
    if not db_secao:
        raise HTTPException(status_code=404, detail="Seção não encontrada.")
    if db.query(models.NotaCredito).filter(models.NotaCredito.secao_responsavel_id == secao_id).first():
        raise HTTPException(status_code=400, detail=f"Não é possível excluir '{db_secao.nome}', pois está vinculada a Notas de Crédito.")
    if db.query(models.Empenho).filter(models.Empenho.secao_requisitante_id == secao_id).first():
        raise HTTPException(status_code=400, detail=f"Não é possível excluir '{db_secao.nome}', pois está vinculada a Empenhos.")
    secao_nome = db_secao.nome
    db.delete(db_secao)
    log_audit_action(db, admin_user.username, "SECTION_DELETED", f"Seção '{secao_nome}' (ID: {secao_id}) foi excluída.")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)