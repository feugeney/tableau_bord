"""Réglages communs du tableau de bord de la Ministre (MEFB)."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
TDB_EXERCICE_TEST = env.int("TDB_EXERCICE_TEST", default=0) or None
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_celery_beat",
    "apps.core",
    "apps.referentiels",
    "apps.depense",
    "apps.recettes_fiscales",
    "apps.douanes",
    "apps.tresor",
    "apps.dette",
    "apps.investissement",
    "apps.paie",
    "apps.patrimoine",
    "apps.portefeuille",
    "apps.marches_publics",
    "apps.qualite",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# Entrepôt PostgreSQL : les schémas staging, ref, dw et mart sont créés
# avant les migrations (voir apps.core.signals). search_path garde "public"
# pour les tables Django et ajoute les schémas métier.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="tdb"),
        "USER": env("POSTGRES_USER", default="tdb"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="tdb"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"options": "-c search_path=public,ref,dw,mart,staging"},
    }
}

# Interdiction d'interroger la production Oracle en semaine aux heures ouvrées (7 h 30 – 18 h 30).
# Active par défaut (production) ; désactivée en développement (settings/dev.py).
ORACLE_RESTRICTION_HEURES_OUVREES = env.bool("ORACLE_RESTRICTION_HEURES_OUVREES", default=True)

# Sources externes en lecture seule (comptes dédiés, jamais la production aux heures ouvrées).
SOURCES_EXTERNES = {
    "chaine_depense_oracle": {
        "dsn": env("CHAINE_DEPENSE_ORACLE_DSN", default=""),
        "user": env("CHAINE_DEPENSE_ORACLE_USER", default=""),
        "password": env("CHAINE_DEPENSE_ORACLE_PASSWORD", default=""),
        "client_lib_dir": env("CHAINE_DEPENSE_ORACLE_CLIENT_LIB_DIR", default=""),
        "thick": env.bool("CHAINE_DEPENSE_ORACLE_THICK", default=False),
        "connect_timeout": env.int("CHAINE_DEPENSE_ORACLE_CONNECT_TIMEOUT", default=10),
        "call_timeout_ms": env.int("CHAINE_DEPENSE_ORACLE_CALL_TIMEOUT_MS", default=30000),
    },
    "sicom": {"url": env("SICOM_DATABASE_URL", default="")},
    "sysop": {"url": env("SYSOP_DATABASE_URL", default="")},
    # Telemo (marchés publics) : API ; le jeton reste dans l'environnement.
    "telemo": {"url": env("TELEMO_API_URL", default=""), "jeton": env("TELEMO_API_TOKEN", default="")},
    # SIDOF-ENTREPOT (API, en-tête X-API-Key) : lignes budgétaires de la Chaîne Dépense (vue vm_lbudg).
    "sidof": {
        "url": env("SIDOF_API_URL", default="https://sidof-api.mefb.gov.gn"),
        "cle": env("SIDOF_API_KEY", default=""),
        "timeout": env.int("SIDOF_API_TIMEOUT", default=120),
    },
}

AUTH_USER_MODEL = "core.Utilisateur"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.core.validators.ComplexiteValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Conakry"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "apps.core.partage.JetonPartageAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"login": "10/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=10),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API — Tableau de bord des finances publiques (MEFB)",
    "DESCRIPTION": "Entrepôt de données financières de l'État — République de Guinée.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 15 * 60,
            "KEY_PREFIX": "tdb",
        }
        if REDIS_URL
        # Poste de développement sans Redis : cache mémoire local.
        else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "TIMEOUT": 15 * 60}
    )
}
API_CACHE_SECONDES = 15 * 60

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

OTP_TOTP_ISSUER = "MEFB — Tableau de bord"

# Courriels des alertes (arbitrages de la Ministre, relances). Sans serveur SMTP configuré, les messages
# sont écrits dans le journal du processus (console) au lieu d'être envoyés.
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.smtp.EmailBackend"
        if EMAIL_HOST
        else "django.core.mail.backends.console.EmailBackend"
    ),
)
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=30)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Tableau de bord <ne-pas-repondre@localhost>")
# Adresse de l'application, pour les liens des courriels (ex. https://tdb.exemple.gn).
TDB_URL_PUBLIQUE = env("TDB_URL_PUBLIQUE", default="http://localhost:5173")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}

# Dépôt de fichiers des partenaires (SFTP) : un dossier par source, relevé périodiquement.
DEPOT_ROOT = Path(env("DEPOT_ROOT", default=str(BASE_DIR / "depot")))
DEPOT_STABILITE_SECONDES = env.int("DEPOT_STABILITE_SECONDES", default=60)
DEPOT_RELEVE_MINUTES = env.int("DEPOT_RELEVE_MINUTES", default=5)
# Messagerie AMQP 0.9.1 (RabbitMQ) : événements publiés pour les partenaires. Vide = pas de publication.
EVENEMENTS_AMQP_URL = env(
    "EVENEMENTS_AMQP_URL", default=CELERY_BROKER_URL if str(CELERY_BROKER_URL).startswith("amqp") else ""
)
IMPORT_TAILLE_MAX = env.int("IMPORT_TAILLE_MAX", default=100 * 1024 * 1024)
