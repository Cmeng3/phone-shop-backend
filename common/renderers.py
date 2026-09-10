from rest_framework.renderers import JSONRenderer
from common.responses import extract_error_message


class APIJSONRenderer(JSONRenderer):
    """Keep the project's original JSON envelope across all API endpoints."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        context = renderer_context or {}
        response = context.get('response')
        code = response.status_code if response is not None else 200
        if code == 204:
            return super().render(None, accepted_media_type, renderer_context)
        view = context.get('view')
        source = getattr(view, 'basename', None) or view.__class__.__module__.split('.')[0]
        source = {'productline': 'product-line', 'rolerequest': 'role-request'}.get(source, source)
        payload = {'code': code, 'message': 'Success', 'source': source.upper().replace('_', '-'), 'data': data}
        if code >= 400:
            payload.update(message=extract_error_message(data), data=None, errors=data)
        elif isinstance(data, dict) and 'results' in data and 'count' in data:
            payload['data'] = data['results']
            payload['pagination'] = {key: data[key] for key in ('count', 'next', 'previous')}
        return super().render(payload, accepted_media_type, renderer_context)
