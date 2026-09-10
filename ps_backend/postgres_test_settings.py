"""Run against a uniquely named disposable PostgreSQL test database."""
from uuid import uuid4
from .settings import *  # noqa: F403

if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':  # noqa: F405
    raise RuntimeError('Set DB_ENGINE=postgresql for PostgreSQL tests.')
DATABASES['default']['TEST'] = {'NAME': 'test_phoneshop_' + uuid4().hex[:12]}  # noqa: F405
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ALLOWED_HOSTS = ['testserver', 'localhost']
