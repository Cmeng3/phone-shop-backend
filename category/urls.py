from rest_framework.routers import SimpleRouter
from category.views import CategoryViewSet

router = SimpleRouter(trailing_slash=False)
router.register('categories', CategoryViewSet)
urlpatterns = router.urls
