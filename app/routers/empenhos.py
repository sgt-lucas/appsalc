from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db
from .autenticacao import get_current_user, get_current_admin_user, log_audit_action

router = APIRouter(
    tags=["Empenhos e Movimentações"],
    dependencies=[Depends(get_current_user)]
)

# --- Endpoints de Empenhos ---

@router.post("/empenhos", response_model=schemas.EmpenhoInDB, status_code=status.HTTP_201_CREATED, summary="Cria um novo Empenho")
def create_empenho(empenho_in: schemas.EmpenhoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_nc = db.query(models.NotaCredito).filter(models.NotaCredito.id == empenho_in.nota_credito_id).with_for_update().first()
    
    if not db_nc:
        raise HTTPException(status_code=404, detail="Nota de Crédito associada não encontrada.")
    if db_nc.status != "Ativa":
        raise HTTPException(status_code=400, detail=f"Não é possível empenhar em uma NC com status '{db_nc.status}'.")
    if empenho_in.valor > db_nc.saldo_disponivel + 0.01: # Tolerância para ponto flutuante
        raise HTTPException(status_code=400, detail=f"Valor do empenho (R$ {empenho_in.valor:,.2f}) excede o saldo disponível (R$ {db_nc.saldo_disponivel:,.2f}).")
    
    try:
        db_empenho = models.Empenho(**empenho_in.dict())
        db.add(db_empenho)
        
        db_nc.saldo_disponivel -= empenho_in.valor
        if db_nc.saldo_disponivel < 0.01:
            db_nc.saldo_disponivel = 0
            db_nc.status = "Totalmente Empenhada"
        
        log_audit_action(db, current_user.username, "EMPENHO_CREATED", f"Empenho '{empenho_in.numero_ne}' no valor de R$ {empenho_in.valor:,.2f} lançado na NC '{db_nc.numero_nc}'.")
        
        db.commit()
        
        # Recarrega o objeto com os relacionamentos para a resposta
        empenho_completo = db.query(models.Empenho).options(
            joinedload(models.Empenho.secao_requisitante),
            joinedload(models.Empenho.nota_credito).joinedload(models.NotaCredito.secao_responsavel)
        ).filter(models.Empenho.id == db_empenho.id).first()

        return empenho_completo

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Um Empenho com este número de NE já existe.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado: {str(e)}")


@router.get("/empenhos", response_model=schemas.PaginatedEmpenhos, summary="Lista e filtra Empenhos")
def read_empenhos(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=1000),
    nota_credito_id: Optional[int] = Query(None),
    numero_ne: Optional[str] = Query(None, description="Busca parcial pelo número da NE")
):
    query = db.query(models.Empenho).options(
        joinedload(models.Empenho.secao_requisitante),
        joinedload(models.Empenho.nota_credito).joinedload(models.NotaCredito.secao_responsavel)
    )
    if nota_credito_id:
        query = query.filter(models.Empenho.nota_credito_id == nota_credito_id)
    if numero_ne:
        query = query.filter(models.Empenho.numero_ne.ilike(f"%{numero_ne}%"))
        
    total = query.count()
    results = query.order_by(desc(models.Empenho.data_empenho)).offset((page - 1) * size).limit(size).all()
    
    return {"total": total, "page": page, "size": size, "results": results}

@router.delete("/empenhos/{empenho_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui um Empenho (Apenas Admin)")
def delete_empenho(empenho_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(get_current_admin_user)):
    db_empenho = db.query(models.Empenho).filter(models.Empenho.id == empenho_id).first()
    if not db_empenho:
        raise HTTPException(status_code=404, detail="Empenho não encontrado.")
    
    if db.query(models.AnulacaoEmpenho).filter(models.AnulacaoEmpenho.empenho_id == empenho_id).first():
        raise HTTPException(status_code=400, detail="Não é possível excluir empenho, pois ele possui anulações registadas.")
    
    db_nc = db.query(models.NotaCredito).filter(models.NotaCredito.id == db_empenho.nota_credito_id).with_for_update().first()
    if db_nc:
        db_nc.saldo_disponivel += db_empenho.valor
        if db_nc.status in ["Totalmente Empenhada", "Recolhida"]:
            db_nc.status = "Ativa"

    empenho_numero = db_empenho.numero_ne
    log_audit_action(db, admin_user.username, "EMPENHO_DELETED", f"Empenho '{empenho_numero}' (ID: {empenho_id}) excluído. Valor de R$ {db_empenho.valor:,.2f} devolvido ao saldo da NC.")
    db.delete(db_empenho)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Endpoints de Anulações ---

@router.post("/anulacoes-empenho", response_model=schemas.AnulacaoEmpenhoInDB, summary="Regista uma Anulação de Empenho")
def create_anulacao(anulacao_in: schemas.AnulacaoEmpenhoBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_empenho = db.query(models.Empenho).filter(models.Empenho.id == anulacao_in.empenho_id).with_for_update().first()
    if not db_empenho:
        raise HTTPException(status_code=404, detail="Empenho a ser anulado não encontrado.")
    
    soma_anulacoes = db.query(func.sum(models.AnulacaoEmpenho.valor)).filter(models.AnulacaoEmpenho.empenho_id == db_empenho.id).scalar() or 0
    saldo_empenho = db_empenho.valor - soma_anulacoes
    
    if anulacao_in.valor > saldo_empenho + 0.01:
        raise HTTPException(status_code=400, detail=f"Valor da anulação (R$ {anulacao_in.valor:,.2f}) excede o saldo executado do empenho (R$ {saldo_empenho:,.2f}).")
    
    db_nc = db.query(models.NotaCredito).filter(models.NotaCredito.id == db_empenho.nota_credito_id).with_for_update().first()
    if db_nc:
        db_nc.saldo_disponivel += anulacao_in.valor
        if db_nc.status in ["Totalmente Empenhada", "Recolhida"]:
            db_nc.status = "Ativa"
    
    db_anulacao = models.AnulacaoEmpenho(**anulacao_in.dict())
    db.add(db_anulacao)
    log_audit_action(db, current_user.username, "ANULACAO_CREATED", f"Anulação de R$ {anulacao_in.valor:,.2f} no empenho '{db_empenho.numero_ne}'.")
    db.commit()
    db.refresh(db_anulacao)
    return db_anulacao

@router.get("/anulacoes-empenho", response_model=List[schemas.AnulacaoEmpenhoInDB], summary="Lista anulações por empenho")
def read_anulacoes(empenho_id: int, db: Session = Depends(get_db)):
    return db.query(models.AnulacaoEmpenho).filter(models.AnulacaoEmpenho.empenho_id == empenho_id).order_by(models.AnulacaoEmpenho.data).all()

# --- Endpoints de Recolhimentos ---

@router.post("/recolhimentos-saldo", response_model=schemas.RecolhimentoSaldoInDB, summary="Regista um Recolhimento de Saldo de uma NC")
def create_recolhimento(recolhimento_in: schemas.RecolhimentoSaldoBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_nc = db.query(models.NotaCredito).filter(models.NotaCredito.id == recolhimento_in.nota_credito_id).with_for_update().first()
    if not db_nc:
        raise HTTPException(status_code=404, detail="Nota de Crédito não encontrada.")
    if recolhimento_in.valor > db_nc.saldo_disponivel + 0.01:
        raise HTTPException(status_code=400, detail=f"Valor do recolhimento (R$ {recolhimento_in.valor:,.2f}) excede o saldo disponível da NC (R$ {db_nc.saldo_disponivel:,.2f}).")
    
    db_nc.saldo_disponivel -= recolhimento_in.valor
    if db_nc.saldo_disponivel < 0.01:
        db_nc.saldo_disponivel = 0
        db_nc.status = "Recolhida" # Status mais apropriado
    
    db_recolhimento = models.RecolhimentoSaldo(**recolhimento_in.dict())
    db.add(db_recolhimento)
    log_audit_action(db, current_user.username, "RECOLHIMENTO_CREATED", f"Recolhimento de saldo de R$ {recolhimento_in.valor:,.2f} da NC '{db_nc.numero_nc}'.")
    db.commit()
    db.refresh(db_recolhimento)
    return db_recolhimento

@router.get("/recolhimentos-saldo", response_model=List[schemas.RecolhimentoSaldoInDB], summary="Lista recolhimentos por nota de crédito")
def read_recolhimentos(nota_credito_id: int, db: Session = Depends(get_db)):
    return db.query(models.RecolhimentoSaldo).filter(models.RecolhimentoSaldo.nota_credito_id == nota_credito_id).order_by(models.RecolhimentoSaldo.data).all()