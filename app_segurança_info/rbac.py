from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from models import SessionLocal, Usuario
from typing import List

# Dependência para acessar o banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Função para verificar se usuário possui um papel
def verificar_papel(usuario_id: int, papeis_requeridos: List[str], db: Session):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    nomes_papeis = [papel.nome for papel in usuario.papeis]
    if not any(papel in nomes_papeis for papel in papeis_requeridos):
        raise HTTPException(status_code=403, detail="Permissão negada")
