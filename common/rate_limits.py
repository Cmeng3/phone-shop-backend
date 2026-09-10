"""Request budgets with atomic Redis counters and a per-process fallback."""
import hashlib
import ipaddress
import math
import threading
import time
from functools import lru_cache

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle

_lock = threading.Lock()
_script = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('PEXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('PTTL', KEYS[1])}
"""


class LimiterUnavailable(APIException):
    status_code = 503
    default_detail = 'Request checks are temporarily unavailable. Please try again shortly.'


@lru_cache(maxsize=4)
def redis_client(url):
    from redis import Redis
    return Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)


def consume(scope, identity, limit):
    """Return remaining wait seconds if a one-minute budget has been exceeded."""
    key = 'phoneshop:rate:v1:' + scope + ':' + hashlib.sha256(str(identity).encode()).hexdigest()
    if settings.RATE_LIMIT_REDIS_URL:
        from redis.exceptions import RedisError
        try:
            count, ttl = redis_client(settings.RATE_LIMIT_REDIS_URL).eval(_script, 1, key, 60000)
        except RedisError:
            raise LimiterUnavailable() from None
        wait = max(1, math.ceil(ttl / 1000))
    else:
        with _lock:
            now = time.time()
            count, deadline = cache.get(key, (0, now + 60))
            if deadline <= now:
                count, deadline = 0, now + 60
            count += 1
            wait = max(1, math.ceil(deadline - now))
            cache.set(key, (count, deadline), timeout=wait)
    return wait if count > limit else 0


def client_ip(request):
    value = request.META.get('REMOTE_ADDR', '')
    # Render documents that its edge sets the first XFF entry to the client IP.
    # Do not trust arbitrary forwarded headers on a directly exposed local server.
    if settings.RATE_LIMIT_TRUST_RENDER_PROXY:
        value = request.META.get('HTTP_X_FORWARDED_FOR', value).split(',')[0].strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return 'unknown'


def error_response(status, message, wait):
    response = JsonResponse({'code': status, 'message': message, 'source': 'API',
                             'data': None, 'errors': {'detail': message}}, status=status)
    response['Retry-After'] = str(wait)
    response['Cache-Control'] = 'private, no-store'
    return response


class APIRateLimitMiddleware:
    """Bound traffic before token lookup, permissions, or request body parsing."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/api' or request.path.startswith('/api/'):
            ip = client_ip(request)
            limits = [('ip', settings.RATE_LIMIT_IP_PER_MINUTE)]
            if not request.META.get('HTTP_AUTHORIZATION'):
                limits.append(('anonymous', settings.RATE_LIMIT_ANON_PER_MINUTE))
            if request.path.rstrip('/') == '/api/v1/auth/login':
                limits.append(('login', settings.RATE_LIMIT_LOGIN_PER_MINUTE))
            try:
                waits = [consume(scope, ip, limit) for scope, limit in limits]
            except LimiterUnavailable as error:
                return error_response(503, str(error.detail), 5)
            if max(waits):
                return error_response(429, 'Too many requests. Please wait before trying again.', max(waits))
        return self.get_response(request)


class UserAndUploadThrottle(BaseThrottle):
    def allow_request(self, request, view):
        self.retry_after = 0
        if request.user and request.user.is_authenticated:
            self.retry_after = consume('user', request.user.pk, settings.RATE_LIMIT_USER_PER_MINUTE)
            if request.method in ('POST', 'PUT', 'PATCH') and request.content_type.startswith('multipart/'):
                self.retry_after = max(self.retry_after, consume('upload', request.user.pk,
                                                               settings.RATE_LIMIT_UPLOAD_PER_MINUTE))
        return not self.retry_after

    def wait(self):
        return self.retry_after
