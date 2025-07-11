"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 4.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

from pathlib import Path
import os
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

class SuppressTankLevelFilter(logging.Filter):
    def filter(self, record):
        # Diagnostic print for any record seen by this filter
        # print(f"FILTER CHECKING: Logger='{record.name}', Path='{record.pathname}', Message: {record.getMessage()[:100]}...")
        if record.name in ['uvicorn.access', 'daphne.access']:
            if "GET /core/api/get-single-tank-level/" in record.getMessage():
                # print(f"FILTER SUPPRESSING: Logger='{record.name}', Message: {record.getMessage()[:100]}...")
                return False  # Suppress this log record
        return True # Allow other logs

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(os.environ.get('DEBUG', 0)))

ALLOWED_HOSTS = []
ALLOWED_HOSTS.extend(
    filter(
        None,
        os.environ.get('ALLOWED_HOSTS', '').split(','),
    )
)

# CSRF Trusted Origins - Required for HTTPS | NOTE: for Django 3.2, must NOT include scheme (https://)
CSRF_TRUSTED_ORIGINS = [
    '192.168.178.169:1338',
    '*.192.168.178.169:1338',
    '192.168.178.168:1337',
    '*.192.168.178.168:1337',
    '192.168.178.168:1338',
    '*.192.168.178.168:1338',
    'localhost:1338',
    '192.168.178.101:1338',
    '*.192.168.178.101:1338',
]

# Security settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Session security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_USE_SESSIONS = True  # Store CSRF token in the session instead of a cookie
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to access the cookie
CSRF_COOKIE_SAMESITE = 'Lax'  # More permissive SameSite policy

# Channels specific settings
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('kpk-app_redis_1', 6379)],
        },
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'core',
    'import_export',
    'rest_framework',
    'kpklauncher',
    'prodverse',
    'crispy_forms',
    'crispy_bootstrap5',
    'django',
    'croniter',
    'core.templatetags',
    'nav3d',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

SESSION_COOKIE_AGE = 43200

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'app.customMiddleware.TerminalFrameMiddleware',
    'app.customMiddleware.SessionTimeoutMiddleware',
]

ROOT_URLCONF = 'app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'

ASGI_APPLICATION = 'core.asgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ.get('DB_HOST'),
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASS'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Chicago'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = '/static/static/'
MEDIA_URL = '/static/media/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

IMPORT_EXPORT_SKIP_ADMIN_LOG = True

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

Q_CLUSTER = {
    'name': 'kpk-app',
    'workers': 8,
    'recycle': 500,
    'timeout': 60,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'label': 'Django Q2',
    'redis': {
        'host': 'redis',
        'port': 6379,
        'db': 0, }
}

# --- Redis-backed low-latency cache for the Tank Usage Monitor -------------
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://kpk-app_redis_1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'IGNORE_EXCEPTIONS': True,
            'COMPRESS_MIN_LEN': 50,
        },
        'TIMEOUT': 60 * 15,
    }
}

# Configure logging to see our middleware messages
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'suppress_tank_access_filter': {
            # Assuming settings.py is app.settings module
            '()': 'app.settings.SuppressTankLevelFilter',
        }
    },
    'formatters': {
        'verbose': { # For Django logs, root logger
            'format': '{levelname} {asctime} {name} {module} {message}',
            'style': '{',
        },
        'access_log_formatter': { # For dedicated access logs
            'format': '{message}',
            'style': '{',
        }
    },
    'handlers': {
        'default_console': { # For Django, root, etc.
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'filtered_access_console': { # For uvicorn/daphne access logs
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'access_log_formatter',
            'filters': ['suppress_tank_access_filter'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['default_console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'uvicorn.access': {
            'handlers': ['filtered_access_console'],
            'level': 'INFO',
            'propagate': False,
        },
        'daphne.access': { # Also explicitly handle daphne access logs
            'handlers': ['filtered_access_console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Example for app.customMiddleware if it was active:
        # 'app.customMiddleware': {
        #     'handlers': ['default_console'],
        #     'level': 'INFO',
        #     'propagate': False, # Typically false if specific handler is assigned
        # },
    },
    'root': { # Catch-all for other logs not specified above
        'handlers': ['default_console'],
        'level': 'INFO',
    },
}