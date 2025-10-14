import re
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator

from .models import UserRole

# Schemas de Dados (Pydantic)

# --- Autenticação e Usuários ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: UserRole

    @validator('password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('A senha deve ter pelo menos 8 caracteres.')
        if not re.search("[a-z]", v):
            raise ValueError('A senha deve conter pelo menos uma letra minúscula.')
        if not re.search("[A-Z]", v):
            raise ValueError('A senha deve conter pelo menos uma letra maiúscula.')
        if not re.search("[0-9]", v):
            raise ValueError('A senha deve conter pelo menos um número.')
        return v

class UserInDB(UserBase):
    id: int
    role: UserRole
    class Config:
        from_attributes = True

# --- Seções ---
class SeçãoBase(BaseModel):
    nome: str

class SeçãoCreate(SeçãoBase):
    pass

class SeçãoInDB(SeçãoBase):
    id: int
    class Config:
        from_attributes = True

# --- Notas de Crédito ---
class NotaCreditoBase(BaseModel):
    numero_nc: str
    valor: float = Field(..., gt=0)
    esfera: str
    fonte: str = Field(..., max_length=10)
    ptres: str = Field(..., max_length=6)
    plano_interno: str
    nd: str = Field(..., max_length=8, pattern=r'^\d{6,8}$') # Permitir 6 a 8 dígitos
    data_chegada: date
    prazo_empenho: date
    descricao: Optional[str] = None
    secao_responsavel_id: int

class NotaCreditoCreate(NotaCreditoBase):
    pass
    
class NotaCreditoUpdate(NotaCreditoBase):
    pass

class NotaCreditoInDB(NotaCreditoBase):
    id: int
    saldo_disponivel: float
    status: str
    secao_responsavel: SeçãoInDB
    class Config:
        from_attributes = True

# --- Empenhos ---
class EmpenhoBase(BaseModel):
    numero_ne: str
    valor: float = Field(..., gt=0)
    data_empenho: date
    observacao: Optional[str] = None
    nota_credito_id: int
    secao_requisitante_id: int

class EmpenhoCreate(EmpenhoBase):
    pass

class EmpenhoInDB(EmpenhoBase):
    id: int
    secao_requisitante: SeçãoInDB
    nota_credito: NotaCreditoInDB
    class Config:
        from_attributes = True

# --- Anulações e Recolhimentos ---
class AnulacaoEmpenhoBase(BaseModel):
    empenho_id: int
    valor: float = Field(..., gt=0)
    data: date
    observacao: Optional[str] = None

class AnulacaoEmpenhoInDB(AnulacaoEmpenhoBase):
    id: int
    class Config:
        from_attributes = True

class RecolhimentoSaldoBase(BaseModel):
    nota_credito_id: int
    valor: float = Field(..., gt=0)
    data: date
    observacao: Optional[str] = None

class RecolhimentoSaldoInDB(RecolhimentoSaldoBase):
    id: int
    class Config:
        from_attributes = True

# --- Auditoria ---
class AuditLogInDB(BaseModel):
    id: int
    timestamp: datetime
    username: str
    action: str
    details: Optional[str] = None
    class Config:
        from_attributes = True

# --- Paginação ---
class PaginatedNCS(BaseModel):
    total: int
    page: int
    size: int
    results: List[NotaCreditoInDB]

class PaginatedEmpenhos(BaseModel):
    total: int
    page: int
    size: int
    results: List[EmpenhoInDB]