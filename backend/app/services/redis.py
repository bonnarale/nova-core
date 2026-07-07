from redis.asyncio import Redis

from app.core.config import Settings


async def init_redis(settings: Settings) -> Redis:
    client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=5)
    await client.ping()
    return client


async def close_redis(client: Redis) -> None:
    await client.aclose()


async def redis_ready(client: Redis) -> bool:
    try:
        return bool(await client.ping())
    except Exception:
        return False

