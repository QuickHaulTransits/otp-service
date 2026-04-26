from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis
from shared.config import settings

mongo_client: Optional[AsyncIOMotorClient] = None
database: Optional[AsyncIOMotorDatabase] = None
redis_client: Optional[Redis] = None


async def connect_to_db():
    global mongo_client, database, redis_client
    try:
        mongo_client = AsyncIOMotorClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
        database = mongo_client[settings.mongo_db_name]
        # Check connection
        await mongo_client.admin.command('ping')
        print("Connected to MongoDB successfully")
    except Exception as e:
        print(f"FAILED to connect to MongoDB: {e}")
        database = None

    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        print("Connected to Redis successfully")
    except Exception as e:
        print(f"FAILED to connect to Redis: {e}")
        redis_client = None


async def close_db():
    global mongo_client, redis_client
    if mongo_client:
        mongo_client.close()
    if redis_client:
        await redis_client.close()


def get_db() -> AsyncIOMotorDatabase:
    if database is None:
        raise RuntimeError("MongoDB is not connected")
    return database


def get_redis() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis is not connected")
    return redis_client
