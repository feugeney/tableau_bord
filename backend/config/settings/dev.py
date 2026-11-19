from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
SERVIR_FRONTEND_LOCAL = env.bool("SERVIR_FRONTEND_LOCAL", default=True)
# Développement : la base Oracle interrogée (devdep) n'est pas la production.
ORACLE_RESTRICTION_HEURES_OUVREES = env.bool("ORACLE_RESTRICTION_HEURES_OUVREES", default=False)
if not REDIS_URL:  # noqa: F405
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    CELERY_TASK_ALWAYS_EAGER = True
