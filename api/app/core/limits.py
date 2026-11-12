"""Límites compartidos y atómicos. Sin Redis se rechazan las escrituras."""
import hashlib
import hmac
from functools import lru_cache

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

SCRIPT = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return n
"""


@lru_cache
def get_redis():
    return Redis.from_url(get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2)


def client_address(request: Request) -> str:
    # Solo el proxy interno autenticado puede transmitir una IP; no confiar en X-Forwarded-For.
    token = get_settings().editorial_api_token
    supplied = request.headers.get("x-internal-token", "")
    if token and hmac.compare_digest(token.encode(), supplied.encode()):
        return request.headers.get("x-client-ip", "unknown")[:64]
    return request.client.host if request.client else "unknown"


async def limit(bucket: str, identity: str, maximum: int, seconds: int):
    key = "foroia:limit:" + bucket + ":" + hashlib.sha256(identity.encode()).hexdigest()
    try:
        count = await get_redis().eval(SCRIPT, 1, key, seconds)
    except RedisError:
        raise HTTPException(503, "Servicio temporalmente no disponible") from None
    if count > maximum:
        raise HTTPException(429, "Demasiados intentos; inténtalo más tarde", headers={"Retry-After": str(seconds)})
