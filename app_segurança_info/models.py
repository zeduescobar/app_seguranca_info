from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime

DB_USER = 'root'
DB_PASSWORD = 'root123'
DB_HOST = 'localhost'
DB_PORT = '3306'
DB_NAME = 'sistema_usuarios'


DATABASE_URL = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'


engine = create_engine(DATABASE_URL, echo=True) 
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

usuario_papel = Table(
    'usuario_papel',
    Base.metadata,
    Column('usuario_id', Integer, ForeignKey('usuarios.id'), primary_key=True),
    Column('papel_id', Integer, ForeignKey('papeis.id'), primary_key=True)
)

# Modelo de Usuário
class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    senha_hash = Column(String(250), nullable=False)
    data_criacao = Column(DateTime, default=datetime.datetime.utcnow)
    data_exclusao = Column(DateTime, nullable=True)
    ativo = Column(Boolean, default=True)
    anonimizado = Column(Boolean, default=False)

    papeis = relationship('Papel', secondary=usuario_papel, back_populates='usuarios')
    tokens_reset = relationship('TokenReset', back_populates='usuario')
    logs_acesso = relationship('LogAcesso', back_populates='usuario')

# Modelo de Papel
class Papel(Base):
    __tablename__ = 'papeis'

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), nullable=False)

    usuarios = relationship('Usuario', secondary=usuario_papel, back_populates='papeis')

# Modelo de Token de Reset de Senha
class TokenReset(Base):
    __tablename__ = 'tokens_reset'

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    token = Column(String(250), unique=True, nullable=False)
    data_expiracao = Column(DateTime, nullable=False)
    em_uso = Column(Boolean, default=False)

    usuario = relationship('Usuario', back_populates='tokens_reset')

# Modelo de Log de Acesso
class LogAcesso(Base):
    __tablename__ = 'logs_acesso'

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=True)
    ip = Column(String(45))
    acao = Column(String(50))
    data_hora = Column(DateTime, default=datetime.datetime.utcnow)

    usuario = relationship('Usuario', back_populates='logs_acesso')

# Função para criar as tabelas no banco
def criar_banco():
    Base.metadata.create_all(bind=engine)

