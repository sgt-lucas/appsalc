import enum
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Float, Date, ForeignKey, 
                        DateTime, Enum as SQLAlchemyEnum)
from sqlalchemy.orm import relationship
from .database import Base

# Modelos do Banco de Dados (SQLAlchemy)

class UserRole(str, enum.Enum):
    OPERADOR = "OPERADOR"
    ADMINISTRADOR = "ADMINISTRADOR"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLAlchemyEnum(UserRole), nullable=False, default=UserRole.OPERADOR)

class Seção(Base):
    __tablename__ = "secoes"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)
    notas_credito = relationship("NotaCredito", back_populates="secao_responsavel")
    empenhos = relationship("Empenho", back_populates="secao_requisitante")

class NotaCredito(Base):
    __tablename__ = "notas_credito"
    id = Column(Integer, primary_key=True, index=True)
    numero_nc = Column(String, unique=True, nullable=False, index=True)
    valor = Column(Float, nullable=False)
    esfera = Column(String)
    fonte = Column(String(10))
    ptres = Column(String(6))
    plano_interno = Column(String, index=True)
    nd = Column(String(8), index=True) # Aumentado para 8 para comportar formatação
    data_chegada = Column(Date)
    prazo_empenho = Column(Date)
    descricao = Column(String, nullable=True)
    secao_responsavel_id = Column(Integer, ForeignKey("secoes.id", ondelete="RESTRICT"), index=True)
    saldo_disponivel = Column(Float, nullable=False)
    status = Column(String, default="Ativa", index=True)

    secao_responsavel = relationship("Seção", back_populates="notas_credito")
    empenhos = relationship("Empenho", back_populates="nota_credito", cascade="all, delete-orphan", passive_deletes=True)
    recolhimentos = relationship("RecolhimentoSaldo", back_populates="nota_credito", cascade="all, delete-orphan", passive_deletes=True)

class Empenho(Base):
    __tablename__ = "empenhos"
    id = Column(Integer, primary_key=True, index=True)
    numero_ne = Column(String, unique=True, nullable=False, index=True)
    valor = Column(Float, nullable=False)
    data_empenho = Column(Date)
    observacao = Column(String, nullable=True)
    nota_credito_id = Column(Integer, ForeignKey("notas_credito.id", ondelete="CASCADE"))
    secao_requisitante_id = Column(Integer, ForeignKey("secoes.id", ondelete="RESTRICT"))

    nota_credito = relationship("NotaCredito", back_populates="empenhos")
    secao_requisitante = relationship("Seção", back_populates="empenhos")
    anulacoes = relationship("AnulacaoEmpenho", back_populates="empenho", cascade="all, delete-orphan", passive_deletes=True)

class AnulacaoEmpenho(Base):
    __tablename__ = "anulacoes_empenho"
    id = Column(Integer, primary_key=True, index=True)
    empenho_id = Column(Integer, ForeignKey("empenhos.id", ondelete="CASCADE"))
    valor = Column(Float, nullable=False)
    data = Column(Date, nullable=False)
    observacao = Column(String, nullable=True)

    empenho = relationship("Empenho", back_populates="anulacoes")

class RecolhimentoSaldo(Base):
    __tablename__ = "recolhimentos_saldo"
    id = Column(Integer, primary_key=True, index=True)
    nota_credito_id = Column(Integer, ForeignKey("notas_credito.id", ondelete="CASCADE"))
    valor = Column(Float, nullable=False)
    data = Column(Date, nullable=False)
    observacao = Column(String, nullable=True)

    nota_credito = relationship("NotaCredito", back_populates="recolhimentos")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(String, nullable=True)