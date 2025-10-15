from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func

from app import models, schemas
from app.database import get_db
from app.autenticacao import get_current_user

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/kpis", summary="Retorna os KPIs principais do dashboard")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    saldo_total = db.query(func.sum(models.NotaCredito.saldo_disponivel)).scalar() or 0.0
    ncs_ativas = db.query(models.NotaCredito).filter(models.NotaCredito.status == "Ativa").count()
    
    soma_empenhos_bruto = db.query(func.sum(models.Empenho.valor)).scalar() or 0.0
    soma_anulacoes = db.query(func.sum(models.AnulacaoEmpenho.valor)).scalar() or 0.0
    
    valor_empenhado_liquido = soma_empenhos_bruto - soma_anulacoes
    
    return {
        "saldo_disponivel_total": saldo_total,
        "valor_empenhado_total": valor_empenhado_liquido,
        "ncs_ativas": ncs_ativas
    }

@router.get("/avisos", response_model=List[schemas.NotaCreditoInDB], summary="Retorna NCs com prazo de empenho próximo")
def get_dashboard_avisos(db: Session = Depends(get_db)):
    # Retorna NCs ativas cujo prazo de empenho é hoje ou nos próximos 7 dias.
    data_limite = date.today() + timedelta(days=7) 
    avisos = db.query(models.NotaCredito).options(joinedload(models.NotaCredito.secao_responsavel)).filter(
        models.NotaCredito.prazo_empenho <= data_limite,
        models.NotaCredito.status == "Ativa"
    ).order_by(models.NotaCredito.prazo_empenho).all()
    return avisos