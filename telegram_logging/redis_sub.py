import redis
from telegram import Bot


def log_listener(bot: Bot, redis_connection):
    r = redis.StrictRedis(**redis_connection)
    pubsub = r.pubsub()
    pubsub.subscribe("log-channel")
