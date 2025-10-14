from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc

from .. import models, schemas
from ..database import get_db
from .autenticacao import get_current_user, get_current_admin_user, log_audit_action

router = APIRouter(
    prefix="/notas-credito",
    tags=["Notas de Crédito"],
    dependencies=[Depends(get_current_user)]
)

@router.post("", response_model=schemas.NotaCreditoInDB, status_code=status.HTTP_201_CREATED, summary="Cria uma nova Nota de Crédito")
def create_nota_credito(nc_in: schemas.NotaCreditoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not db.query(models.Seção).filter(models.Seção.id == nc_in.secao_responsavel_id).first():
        raise HTTPException(status_code=404, detail="Seção responsável não encontrada.")
    try:
        # PGD/PGA-SIGA 2024.01.29 - Ajuste ND (Natureza de Despesa) para aceitar 8 dígitos, conforme Manual SIAFI 2024.
        db_nc = models.NotaCredito(**nc_in.dict(), saldo_disponivel=nc_in.valor, status="Ativa")
        db.add(db_nc)
        log_audit_action(db, current_user.username, "NC_CREATED", f"NC '{nc_in.numero_nc}' criada com valor R$ {nc_in.valor:,.2f}.")
        db.commit()
        db.refresh(db_nc)
        return db_nc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Uma Nota de Crédito com este número já existe.")

@router.get("", response_model=schemas.PaginatedNCS, summary="Lista e filtra as Notas de Crédito")
def read_notas_credito(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=1000),
    numero_nc: Optional[str] = Query(None, description="Busca parcial pelo número da NC"),
    plano_interno: Optional[str] = Query(None),
    nd: Optional[str] = Query(None),
    secao_responsavel_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None)
):
    query = db.query(models.NotaCredito).options(joinedload(models.NotaCredito.secao_responsavel))
    
    if numero_nc: query = query.filter(models.NotaCredito.numero_nc.ilike(f"%{numero_nc}%"))
    if plano_interno: query = query.filter(models.NotaCredito.plano_interno.ilike(f"%{plano_interno}%"))
    if nd: query = query.filter(models.NotaCredito.nd.ilike(f"%{nd}%"))
    if secao_responsavel_id: query = query.filter(models.NotaCredito.secao_responsavel_id == secao_responsavel_id)
    if status: query = query.filter(models.NotaCredito.status == status)
    
    total = query.count()
    results = query.order_by(desc(models.NotaCredito.data_chegada)).offset((page - 1) * size).limit(size).all()
    
    return {"total": total, "page": page, "size": size, "results": results}

@router.get("/{nc_id}", response_model=schemas.NotaCreditoInDB, summary="Obtém detalhes de uma Nota de Crédito")
def read_nota_credito(nc_id: int, db: Session = Depends(get_db)):
    db_nc = db.query(models.NotaCredito).options(joinedload(models.NotaCredito.secao_responsavel)).filter(models.NotaCredito.id == nc_id).first()
    if not db_nc:
        raise HTTPException(status_code=404, detail="Nota de Crédito não encontrada.")
    return db_nc

@router.put("/{nc_id}", response_model=schemas.NotaCreditoInDB, summary="Atualiza uma Nota de Crédito")
def update_nota_credito(nc_id: int, nc_update: schemas.NotaCreditoUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_nc = db.query(models.NotaCredito).filter(models.NotaCredito.id == nc_id).first()
    if not db_nc:
        raise HTTPException(status_code=404, detail="Nota de Crédito não encontrada.")
    
    valor_ja_empenhado = db_nc.valor - db_nc.saldo_disponivel
    novo_saldo = nc_update.valor - valor_ja_empenhado
    
    if novo_saldo < -0.01: # Usar uma pequena tolerância para erros de ponto flutuante
        raise HTTPException(status_code=400, detail=f"O novo valor total (R$ {nc_update.valor:,.2f}) é menor que o valor já comprometido (R$ {valor_ja_empenhado:,.2f}) nesta NC.")

    update_data = nc_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_nc, key, value)
    
    db_nc.saldo_disponivel = novo_saldo
    
    try:
        log_audit_action(db, current_user.username, "NC_UPDATED", f"NC '{db_nc.numero_nc}' (ID: {nc_id}) atualizada.")
        db.commit()
        db.refresh(db_nc)
        return db_nc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma Nota de Crédito com o número informado.")

@router.delete("/{nc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Exclui uma Nota de Crédito (Apenas Admin)")
def delete_nota_credito(nc_id: int, db: Session = Depends(get_db), admin_user: models.User = Depends(get_current_admin_user)):
    db_nc = db.query(models.NotaCredito).filter(models.NotaCredito.id == nc_id).first()
    if not db_nc:
        raise HTTPException(status_code=404, detail="Nota de Crédito não encontrada.")
    
    if db.query(models.Empenho).filter(models.Empenho.nota_credito_id == nc_id).first():
        raise HTTPException(status_code=400, detail=f"Não é possível excluir a NC '{db_nc.numero_nc}', pois ela possui empenho(s) vinculado(s). Exclua os empenhos primeiro.")
    
    nc_numero = db_nc.numero_nc
    db.delete(db_nc)
    log_audit_action(db, admin_user.username, "NC_DELETED", f"NC '{nc_numero}' (ID: {nc_id}) foi excluída.")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)