"""Configuración leída de variables de entorno. Sin secretos por defecto."""
import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    # Token compartido entre el servidor Nuxt y la API para el panel editorial.
    # Si está vacío, el panel queda deshabilitado (respuesta 503).
    editorial_api_token: str
    editorial_actor: str
    allowed_hosts: tuple[str, ...]
    redis_url: str
    site_url: str
    cookie_secure: bool
    legacy_editorial_enabled: bool
    registration_enabled: bool = True
    account_email_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    token = os.environ.get("EDITORIAL_API_TOKEN", "")
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        editorial_api_token=token if len(token) >= 32 else "",
        editorial_actor=os.environ.get("EDITORIAL_ACTOR", "equipo-editorial")[:80],
        allowed_hosts=tuple(
            h.strip() for h in os.environ.get("ALLOWED_HOSTS", "api,localhost,127.0.0.1").split(",") if h.strip()
        ),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        site_url=os.environ.get("SITE_URL", "http://localhost:3000").rstrip("/"),
        cookie_secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        legacy_editorial_enabled=os.environ.get("LEGACY_EDITORIAL_ENABLED", "false").lower() == "true",
        registration_enabled=os.environ.get("REGISTRATION_ENABLED", "true").lower() == "true",
        account_email_enabled=os.environ.get("ACCOUNT_EMAIL_ENABLED", "true").lower() == "true",
    )
