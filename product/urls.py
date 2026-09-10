from rest_framework.routers import SimpleRouter
from product.views import ProductViewSet, ProductLineViewSet

router = SimpleRouter(trailing_slash=False)
router.register('products', ProductViewSet)
router.register('product-lines', ProductLineViewSet)
urlpatterns = router.urls
