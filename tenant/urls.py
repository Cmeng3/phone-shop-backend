from rest_framework.routers import SimpleRouter
from tenant.views import TenantViewSet

router = SimpleRouter(trailing_slash=False)
router.register('tenants', TenantViewSet)
urlpatterns = router.urls
