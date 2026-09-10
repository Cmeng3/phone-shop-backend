from rest_framework.routers import SimpleRouter
from brand.views import BrandViewSet

router = SimpleRouter(trailing_slash=False)
router.register('brands', BrandViewSet)
urlpatterns = router.urls
