from django.conf import settings
from django.http import FileResponse, HttpResponse


def index(request):
    path = settings.BASE_DIR.parent / 'phone-shop-frontend' / 'dist' / 'index.html'
    if not path.exists():
        return HttpResponse('Frontend is not built yet. Run npm install and npm run build in the frontend directory, or use npm run dev.', status=503, content_type='text/plain')
    response = FileResponse(path.open('rb'), content_type='text/html')
    response['Cache-Control'] = 'no-store'
    return response
