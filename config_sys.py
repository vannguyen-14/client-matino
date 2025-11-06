import os
from dotenv import load_dotenv
from datetime import timedelta, timezone

load_dotenv()

# OPENAI & SERP
SECRET_KEY = os.getenv("SECRET_KEY")

# Redis config
# REDIS_HOST = "redis-matino"
# REDIS_PORT = 6379
REDIS_HOST = "localhost"
REDIS_PORT = 6381
REDIS_DB = int(os.getenv("REDIS_DB", 0))

MYANMAR_TZ = timezone(timedelta(hours=6, minutes=30))

