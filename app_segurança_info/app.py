from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from models import SessionLocal, Usuario, Papel, TokenReset, LogAcesso
from auth import gerar_hash_senha, verificar_senha
from rbac import verificar_papel
from email_service import enviar_email_reset
from pydantic import BaseModel, EmailStr
import uuid
import datetime
import random
import string

app = FastAPI()

# Configuração de CORS para permitir acesso do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class AtribuirPapelRequest(BaseModel):
    usuario_id: int
    nome_papel: str

class ResetSenhaRequest(BaseModel):
    email: EmailStr

class NovaSenhaRequest(BaseModel):
    token: str
    nova_senha: str

# Dependência para obter sessão de banco de dados

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Registra logs de acesso e eventos
async def registrar_log(acao: str, usuario_id: int, request: Request, db: Session):
    ip = request.client.host if request.client else "IP não detectado"
    novo_log = LogAcesso(
        usuario_id=usuario_id,
        ip=ip,
        acao=acao
    )
    db.add(novo_log)
    db.commit()

@app.post("/cadastrar")
def cadastrar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=gerar_hash_senha(usuario.senha)
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return {"mensagem": "Usuário cadastrado com sucesso", "usuario_id": novo_usuario.id}

@app.post("/login")
async def login_usuario(dados_login: UsuarioLogin, request: Request, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados_login.email).first()

    if not usuario or not verificar_senha(dados_login.senha, usuario.senha_hash):
        await registrar_log("falha_login", None, request, db)
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Conta desativada")

    if usuario.anonimizado:
        raise HTTPException(status_code=403, detail="Conta anonimizada")

    await registrar_log("login", usuario.id, request, db)

    return {"mensagem": "Login realizado com sucesso", "usuario_id": usuario.id}

@app.post("/atribuir-papel")
def atribuir_papel(dados: AtribuirPapelRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == dados.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    papel = db.query(Papel).filter(Papel.nome == dados.nome_papel).first()
    if not papel:
        papel = Papel(nome=dados.nome_papel)
        db.add(papel)
        db.commit()
        db.refresh(papel)

    if papel not in usuario.papeis:
        usuario.papeis.append(papel)
        db.commit()

    return {"mensagem": f"Papel '{dados.nome_papel}' atribuído ao usuário {usuario.nome}"}

@app.get("/area-admin")
def area_admin(usuario_id: int, db: Session = Depends(get_db)):
    verificar_papel(usuario_id, ["admin"], db)
    return {"mensagem": "Bem-vindo à área de administração"}

@app.post("/reset-solicitar")
def solicitar_reset(dados: ResetSenhaRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = str(uuid.uuid4())
    data_expiracao = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)

    novo_token = TokenReset(
        usuario_id=usuario.id,
        token=token,
        data_expiracao=data_expiracao,
        em_uso=False
    )

    db.add(novo_token)
    db.commit()

    enviar_email_reset(usuario.email, token)

    return {"mensagem": "Email de reset enviado com sucesso"}

@app.post("/reset-confirmar")
async def confirmar_reset(dados: NovaSenhaRequest, request: Request, db: Session = Depends(get_db)):
    token_obj = db.query(TokenReset).filter(TokenReset.token == dados.token, TokenReset.em_uso == False).first()
    if not token_obj or token_obj.data_expiracao < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    usuario = db.query(Usuario).filter(Usuario.id == token_obj.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    token_obj.em_uso = True
    db.commit()

    await registrar_log("reset_senha", usuario.id, request, db)

    return {"mensagem": "Senha atualizada com sucesso"}

@app.post("/logout")
async def logout(usuario_id: int, request: Request, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    await registrar_log("logout", usuario.id, request, db)

    return {"mensagem": "Logout realizado com sucesso"}

@app.post("/solicitar-exclusao")
async def solicitar_exclusao(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if not usuario.ativo:
        raise HTTPException(status_code=400, detail="Usuário já inativo")

    usuario.ativo = False
    usuario.data_exclusao = datetime.datetime.utcnow()
    db.commit()

    return {"mensagem": "Solicitação de exclusão realizada com sucesso"}

@app.post("/anonimizar-usuario")
async def anonimizar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario.anonimizado:
        raise HTTPException(status_code=400, detail="Usuário já anonimizado")

    usuario.nome = "Usuário Anonimizado"
    usuario.email = f"anonimo-{uuid.uuid4().hex[:8]}@exemplo.com"
    nova_senha = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    usuario.senha_hash = gerar_hash_senha(nova_senha)
    usuario.anonimizado = True
    db.commit()

    return {"mensagem": "Usuário anonimizado com sucesso"}
