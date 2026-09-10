"""Only used by the frontend's isolated browser-test server."""
import os

os.environ['DB_ENGINE'] = 'sqlite'
os.environ['DJANGO_DEBUG'] = 'True'
os.environ['SECRET_KEY'] = 'browser-tests-only-not-a-deployment-secret'
from .settings import *  # noqa: E402,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.environ['PHONE_SHOP_E2E_DB']}}
MEDIA_ROOT = os.environ['PHONE_SHOP_E2E_MEDIA']
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
