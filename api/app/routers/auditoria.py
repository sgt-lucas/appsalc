from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

# CORREÇÃO: Importações absolutas
from app import models, schemas
from app.database import get_db
from app.routers.autenticacao import get_current_admin_user

router = APIRouter(
    prefix="/audit-logs",
    tags=["Auditoria"],
    dependencies=[Depends(get_current_admin_user)]
)

@router.get("", response_model=List[schemas.AuditLogInDB], summary="Retorna o log de auditoria do sistema")
def read_audit_logs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    logs = db.query(models.AuditLog).order_by(desc(models.AuditLog.timestamp)).offset(skip).limit(limit).all()
    return logs