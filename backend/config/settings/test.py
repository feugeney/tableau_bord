import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403

DEBUG = False
TDB_EXERCICE_TEST = None
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_CLASSES": []}  # noqa: F405
SECRET_KEY = "cle-de-test-suffisamment-longue-pour-hs256-0123456789"
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="tdb-tests-"))
DEPOT_ROOT = Path(tempfile.mkdtemp(prefix="tdb-depot-"))
EVENEMENTS_AMQP_URL = ""
