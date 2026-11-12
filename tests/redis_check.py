"""Comprobación real en Redis: ejecutar dentro del contenedor API por stdin."""
import asyncio
import hashlib
import uuid

from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.limits import SCRIPT, get_redis, limit


async def main():
    identity = 'check-' + uuid.uuid4().hex
    key = 'foroia:limit:real-check:' + hashlib.sha256(identity.encode()).hexdigest()
    first = get_redis()
    second = Redis.from_url(get_settings().redis_url)
    try:
        results = await asyncio.gather(*(limit('real-check', identity, 5, 60) for _ in range(20)), return_exceptions=True)
        assert sum(result is None for result in results) == 5
        assert sum(isinstance(result, HTTPException) and result.status_code == 429 for result in results) == 15
        assert 0 < await first.ttl(key) <= 60
        assert int(await second.get(key)) == 20
        assert await second.eval(SCRIPT, 1, key, 60) == 21
        print('Redis real: atomicidad, concurrencia, TTL y contador compartido correctos.')
    finally:
        await first.delete(key)
        await second.aclose()
        await first.aclose()


asyncio.run(main())
