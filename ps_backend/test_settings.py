import os

os.environ['DB_ENGINE'] = 'sqlite'
os.environ['DJANGO_DEBUG'] = 'False'
os.environ.setdefault('SECRET_KEY', 'test-only-secret-key-not-for-deployment')
from .settings import *  # noqa: E402,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ALLOWED_HOSTS = ['testserver', 'localhost']
