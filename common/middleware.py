from django.shortcuts import redirect
from rest_framework.authtoken.models import Token


class WorkspaceLoginRequiredMiddleware:
    """Guard browser pages; DRF continues to authenticate API requests by token."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path == '/login' or path.startswith('/static/'):
            return self.get_response(request)
        is_api = path == '/api' or path.startswith('/api/')
        navigation = request.headers.get('Sec-Fetch-Mode') == 'navigate' or (
            request.method in ('GET', 'HEAD') and 'text/html' in request.headers.get('Accept', '')
        )
        if is_api and (not navigation or path == '/api/v1/auth/login'):
            return self.get_response(request)
        token = request.session.get('workspace_token')
        authenticated = bool(token and Token.objects.filter(key=token, user__is_active=True).exists())
        if not authenticated and not request.user.is_authenticated:
            request.session.pop('workspace_token', None)
            response = redirect('/login')
            response['Cache-Control'] = 'no-store'
            return response
        return self.get_response(request)
