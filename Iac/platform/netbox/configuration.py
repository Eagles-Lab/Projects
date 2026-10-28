import os

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "netbox"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "netbox", "USER": "netbox", "HOST": "postgres",
    "PASSWORD": os.environ["DB_PASSWORD"], "CONN_MAX_AGE": 300, "CONN_HEALTH_CHECKS": True,
}}
REDIS = {
    "tasks": {"HOST": "redis", "PORT": 6379, "DATABASE": 0,
              "PASSWORD": os.environ["REDIS_PASSWORD"], "SSL": False},
    "caching": {"HOST": "redis", "PORT": 6379, "DATABASE": 1,
                "PASSWORD": os.environ["REDIS_PASSWORD"], "SSL": False},
}
SECRET_KEY = os.environ["SECRET_KEY"]
API_TOKEN_PEPPERS = {1: os.environ["API_TOKEN_PEPPER"]}
TIME_ZONE = "Asia/Shanghai"
