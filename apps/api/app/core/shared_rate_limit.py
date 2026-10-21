"""Tekrar başlatma ve çok işçi arasında ortak Redis hız sınırı.

Anahtarlar ham IP içermez; anonim SHA256 ile indekslenir. Redis Lua betiği
sayım/eklemeyi atomik yapar; sunucu zamanı saat kayması riskini azaltır.
"""
import hashlib
import uuid
from functools import lru_cache
from typing import Optional

LUA_RATE_LIMIT = """
local current = redis.call('TIME')
local now = tonumber(current[1]) * 1000 + math.floor(tonumber(current[2]) / 1000)
local window = tonumber(ARGV[1])
local maximum = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= maximum then
  return 0
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window + 1000)
return 1
"""

@lru_cache(maxsize=2)
def get_redis_client(redis_url: str):
    import redis.asyncio as redis
    return redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2, health_check_interval=30)

async def acquire_redis_quota(redis_url: str, client_ip: str, *, max_requests: int) -> bool:
    if max_requests < 1:
        raise ValueError("Hız sınırı 1 veya daha büyük olmalı")
    # Doğrudan ağ eşiğindeki güvenilir bağlantının IP'si kullanılır;
    # istekçinin taklit edebileceği X-Forwarded-For'a güvenilmez.
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
    nonce = uuid.uuid4().hex
    accepted = await get_redis_client(redis_url).eval(
        LUA_RATE_LIMIT, 1, "carpet:rl:v1:" + ip_hash, 60000, max_requests, nonce
    )
    return int(accepted) == 1

async def close_redis_clients() -> None:
    for client in list(get_redis_client.cache_info() and []):
        await client.aclose()
    get_redis_client.cache_clear()
