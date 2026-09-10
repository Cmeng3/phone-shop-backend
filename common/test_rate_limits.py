from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from common.rate_limits import APIRateLimitMiddleware, UserAndUploadThrottle, client_ip, consume, LimiterUnavailable


@override_settings(RATE_LIMIT_REDIS_URL='', RATE_LIMIT_TRUST_RENDER_PROXY=False)
class RateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.factory = RequestFactory()

    def test_login_limit_runs_before_view_even_with_forged_token(self):
        calls = []
        middleware = APIRateLimitMiddleware(lambda request: calls.append(request) or HttpResponse())
        for _ in range(5):
            self.assertEqual(middleware(self.factory.post('/api/v1/auth/login', HTTP_AUTHORIZATION='Token fake')).status_code, 200)
        response = middleware(self.factory.post('/api/v1/auth/login', HTTP_AUTHORIZATION='Token different'))
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(len(calls), 5)

    @override_settings(RATE_LIMIT_ANON_PER_MINUTE=2, RATE_LIMIT_IP_PER_MINUTE=3)
    def test_anonymous_and_invalid_token_requests_are_bounded(self):
        middleware = APIRateLimitMiddleware(lambda request: HttpResponse())
        for _ in range(2):
            self.assertEqual(middleware(self.factory.get('/api/v1/products')).status_code, 200)
        self.assertEqual(middleware(self.factory.get('/api/v1/products')).status_code, 429)
        self.assertEqual(middleware(self.factory.get('/api/v1/products', HTTP_AUTHORIZATION='Token fake')).status_code, 429)
        self.assertEqual(middleware(self.factory.get('/login')).status_code, 200)
        self.assertEqual(middleware(self.factory.get('/api/v1/products', REMOTE_ADDR='192.0.2.2')).status_code, 200)

    def test_untrusted_forwarded_headers_cannot_change_identity(self):
        request = self.factory.get('/', REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR='198.51.100.8')
        self.assertEqual(client_ip(request), '192.0.2.1')
        with override_settings(RATE_LIMIT_TRUST_RENDER_PROXY=True):
            self.assertEqual(client_ip(request), '198.51.100.8')

    def test_simultaneous_requests_do_not_exceed_local_budget(self):
        with ThreadPoolExecutor(max_workers=12) as executor:
            waits = list(executor.map(lambda _: consume('concurrency', 'same-user', 5), range(30)))
        self.assertEqual(waits.count(0), 5)

    def test_window_resets_without_extending_on_rejection(self):
        with patch('common.rate_limits.time.time', return_value=100):
            self.assertEqual(consume('time', 'user', 1), 0)
            self.assertEqual(consume('time', 'user', 1), 60)
        with patch('common.rate_limits.time.time', return_value=161):
            self.assertEqual(consume('time', 'user', 1), 0)

    @override_settings(RATE_LIMIT_REDIS_URL='redis://localhost:6379/15')
    def test_storage_failure_returns_503_without_running_view(self):
        from redis.exceptions import ConnectionError
        with patch('common.rate_limits.redis_client') as client:
            client.return_value.eval.side_effect = ConnectionError('unavailable')
            response = APIRateLimitMiddleware(lambda request: self.fail('View ran'))(self.factory.get('/api/v1/products'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '5')

    @override_settings(RATE_LIMIT_USER_PER_MINUTE=2, RATE_LIMIT_UPLOAD_PER_MINUTE=1)
    def test_user_budget_across_ips_and_separate_upload_budget(self):
        class View(APIView):
            permission_classes = [AllowAny]
            throttle_classes = [UserAndUploadThrottle]
            def get(self, request):
                return Response({'ok': True})
            post = get
        factory = APIRequestFactory()
        def call(user, method='get', ip='192.0.2.1'):
            request = (factory.post('/api/v1/products', {'name': 'upload form'}, format='multipart', REMOTE_ADDR=ip)
                       if method == 'post' else factory.get('/api/v1/products', REMOTE_ADDR=ip))
            force_authenticate(request, user=SimpleNamespace(pk=user, is_authenticated=True))
            return View.as_view()(request)
        self.assertEqual(call(1).status_code, 200)
        self.assertEqual(call(1, ip='192.0.2.2').status_code, 200)
        response = call(1, ip='192.0.2.3')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertEqual(call(2, 'post').status_code, 200)
        self.assertEqual(call(2, 'post').status_code, 429)
        self.assertEqual(call(3, 'post').status_code, 200)
