from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter
from accounts.views import RoleViewSet, UserViewSet, RoleRequestViewSet
from common.dashboard import DashboardView
from common.frontend import index

router = SimpleRouter(trailing_slash=False)
router.register('roles', RoleViewSet)
router.register('users', UserViewSet)
router.register('role-requests', RoleRequestViewSet)

urlpatterns = [
    path('', index, name='workspace'),
    path('login', index, name='workspace-login'),
    path('admin/', admin.site.urls),
   
    path('api/v1/', include([
        path('dashboard', DashboardView.as_view()),
        path('', include(router.urls)),
        path('', include('accounts.urls')),
        path('', include('brand.urls')),
        path('', include('category.urls')),
        path('', include('product.urls')),
        path('', include('tenant.urls')),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Direct browser links enter the guarded React workspace.
urlpatterns += [re_path(r'^(?:dashboard|products|product-lines|categories|brands|tenants|users|roles|role-requests|profile|help)/?$', index)]
