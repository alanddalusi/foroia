"""Cuentas y sesiones opacas. Tokens almacenados únicamente como hashes."""
import asyncio
import hashlib
import hmac
import re
import secrets
from datetime import UTC, timedelta
from typing import Annotated
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.limits import client_address, limit
from app.models import AccountToken, AuditLog, MailOutbox, User, UserSession, utcnow

router = APIRouter(prefix="/auth", tags=["accounts"])
DB = Annotated[AsyncSession, Depends(get_db)]
PH = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_HASH = PH.hash(secrets.token_urlsafe(24))
SESSION_COOKIE = "foroia_session"
CSRF_COOKIE = "foroia_csrf"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class EmailPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value):
            raise ValueError("Correo no válido")
        return value


class Login(EmailPayload):
    password: str = Field(min_length=12, max_length=128)


class Registration(Login):
    display_name: str = Field(min_length=2, max_length=80)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2 or any(ord(c) < 32 for c in value):
            raise ValueError("Nombre no válido")
        return value


class TokenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class Reset(TokenPayload):
    password: str = Field(min_length=12, max_length=128)


def check_origin(request: Request):
    configured = get_settings().site_url
    allowed = {configured}
    site = urlsplit(configured)
    if not get_settings().cookie_secure and site.hostname in {"localhost", "127.0.0.1"}:
        allowed.add(f"http://127.0.0.1:{site.port or 80}")
        allowed.add(f"http://localhost:{site.port or 80}")
    if request.headers.get("origin") not in allowed:
        raise HTTPException(403, "Origen no permitido")
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise HTTPException(415, "Se requiere JSON")


async def current_session(request: Request, db: DB) -> UserSession:
    raw = request.cookies.get(SESSION_COOKIE, "")
    session = await db.get(UserSession, digest(raw)) if 32 <= len(raw) <= 128 else None
    if not session or aware(session.expires_at) <= utcnow():
        raise HTTPException(401, "Inicia sesión")
    return session


async def current_user(db: DB, session: Annotated[UserSession, Depends(current_session)]) -> User:
    user = await db.get(User, session.user_id)
    if not user or user.blocked:
        raise HTTPException(403, "Cuenta no disponible")
    return user


async def csrf(request: Request, session: Annotated[UserSession, Depends(current_session)]):
    check_origin(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied or not hmac.compare_digest(digest(supplied), session.csrf_hash):
        raise HTTPException(403, "Protección CSRF")


def roles(*allowed):
    async def require(user: Annotated[User, Depends(current_user)]):
        if not user.verified or user.role not in allowed:
            raise HTTPException(403, "Permisos insuficientes")
        return user
    return require


def me(user: User):
    return {"id": user.id, "display_name": user.display_name, "role": user.role, "verified": user.verified}


async def account_mail(db, user, purpose):
    # Un token nuevo invalida los anteriores del mismo propósito.
    await db.execute(delete(AccountToken).where(AccountToken.user_id == user.id, AccountToken.purpose == purpose))
    raw = secrets.token_urlsafe(40)
    db.add(AccountToken(token_hash=digest(raw), user_id=user.id, purpose=purpose,
                        expires_at=utcnow() + timedelta(minutes=30 if purpose == "reset" else 1440)))
    link = f"{get_settings().site_url}/cuenta#{purpose}={raw}"
    db.add(MailOutbox(recipient=user.email, subject="ForoIA: recuperar contraseña" if purpose == "reset" else "ForoIA: verificar correo",
                      body=f"Abre este enlace para continuar:\n{link}\nSi no lo solicitaste, ignora este mensaje."))


@router.post("/register", status_code=202, dependencies=[Depends(check_origin)])
async def register(payload: Registration, request: Request, db: DB):
    if not get_settings().registration_enabled or not get_settings().account_email_enabled:
        raise HTTPException(503, "El registro de nuevas cuentas está temporalmente cerrado")
    await limit("register-ip", client_address(request), 10, 3600)
    hashed = await asyncio.to_thread(PH.hash, payload.password)
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user:
        user = User(email=payload.email, display_name=payload.display_name, password_hash=hashed)
        db.add(user)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
        else:
            await account_mail(db, user, "verify")
            await db.commit()
    return {"message": "Si el registro puede completarse, recibirás un correo de verificación."}


@router.post("/login", dependencies=[Depends(check_origin)])
async def login(payload: Login, request: Request, response: Response, db: DB):
    await limit("login-ip", client_address(request), 30, 900)
    await limit("login-account", payload.email, 10, 900)
    user = await db.scalar(select(User).where(User.email == payload.email))
    def verify():
        try:
            return PH.verify(user.password_hash if user else DUMMY_HASH, payload.password)
        except (VerificationError, InvalidHashError):
            return False
    valid = await asyncio.to_thread(verify)
    if not valid or not user or user.blocked:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    old = request.cookies.get(SESSION_COOKIE)
    if old:
        await db.execute(delete(UserSession).where(UserSession.token_hash == digest(old)))
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < utcnow()))
    # Limitar sesiones simultáneas por cuenta.
    existing = list((await db.scalars(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.expires_at.desc()))).all())
    for item in existing[9:]:
        await db.delete(item)
    token, csrf_token = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
    db.add(UserSession(token_hash=digest(token), user_id=user.id, csrf_hash=digest(csrf_token), expires_at=utcnow() + timedelta(days=7)))
    await db.commit()
    secure = get_settings().cookie_secure
    response.set_cookie(SESSION_COOKIE, token, max_age=604800, httponly=True, secure=secure, samesite="lax", path="/")
    response.set_cookie(CSRF_COOKIE, csrf_token, max_age=604800, httponly=False, secure=secure, samesite="strict", path="/")
    return me(user)


@router.get("/me")
async def whoami(user: Annotated[User, Depends(current_user)]):
    return me(user)


@router.post("/logout", dependencies=[Depends(csrf)])
async def logout(response: Response, db: DB, session: Annotated[UserSession, Depends(current_session)]):
    await db.delete(session)
    await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"message": "Sesión cerrada"}


async def consume_token(db, raw, purpose):
    # Bloqueo de fila: dos peticiones simultáneas no pueden consumir el mismo token.
    item = await db.scalar(select(AccountToken).where(AccountToken.token_hash == digest(raw)).with_for_update())
    if not item or item.purpose != purpose or aware(item.expires_at) <= utcnow():
        raise HTTPException(400, "Enlace no válido o caducado")
    user = await db.get(User, item.user_id)
    if not user or user.blocked:
        raise HTTPException(400, "Enlace no válido o caducado")
    await db.delete(item)
    return user


@router.post("/verify", dependencies=[Depends(check_origin)])
async def verify_email(payload: TokenPayload, request: Request, db: DB):
    await limit("verify-ip", client_address(request), 30, 900)
    user = await consume_token(db, payload.token, "verify")
    user.verified = True
    await db.commit()
    return {"message": "Correo verificado. Ya puedes iniciar sesión y comentar."}


@router.post("/forgot", status_code=202, dependencies=[Depends(check_origin)])
async def forgot(payload: EmailPayload, request: Request, db: DB):
    if not get_settings().account_email_enabled:
        raise HTTPException(503, "La recuperación por correo está temporalmente deshabilitada")
    await limit("forgot-ip", client_address(request), 10, 3600)
    await limit("forgot-account", payload.email, 3, 3600)
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user and not user.blocked:
        await account_mail(db, user, "reset")
        await db.commit()
    return {"message": "Si la cuenta existe, recibirás un enlace de recuperación."}


@router.post("/resend", status_code=202, dependencies=[Depends(check_origin)])
async def resend(payload: EmailPayload, request: Request, db: DB):
    if not get_settings().account_email_enabled:
        raise HTTPException(503, "La verificación por correo está temporalmente deshabilitada")
    await limit("resend-ip", client_address(request), 10, 3600)
    await limit("resend-account", payload.email, 3, 3600)
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user and not user.verified and not user.blocked:
        await account_mail(db, user, "verify")
        await db.commit()
    return {"message": "Si corresponde, recibirás un enlace de verificación."}


@router.post("/reset", dependencies=[Depends(check_origin)])
async def reset(payload: Reset, request: Request, db: DB):
    await limit("reset-ip", client_address(request), 10, 900)
    hashed = await asyncio.to_thread(PH.hash, payload.password)
    user = await consume_token(db, payload.token, "reset")
    user.password_hash = hashed
    await db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.add(AuditLog(actor=f"user:{user.id}", action="password_reset", entity_type="user", entity_id=user.id))
    await db.commit()
    return {"message": "Contraseña actualizada. Inicia sesión de nuevo."}
