from common.api import CatalogViewSet
from brand.models import Brand
from brand.serializers import BrandSerializer


class BrandViewSet(CatalogViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filter_fields = {'tenant_id': 'tenant_id', 'status': 'status'}
