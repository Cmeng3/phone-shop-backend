from django.db import IntegrityError
from rest_framework.views import exception_handler
from rest_framework.response import Response


def api_exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        return Response({'detail': 'Conflicting record or invalid relationship.'}, status=400)
    return exception_handler(exc, context)
