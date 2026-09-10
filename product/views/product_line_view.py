from common.api import CatalogViewSet
from product.models import ProductLine
from product.serializers import ProductLineSerializer


class ProductLineViewSet(CatalogViewSet):
    queryset = ProductLine.objects.select_related('category', 'brand')
    serializer_class = ProductLineSerializer
    tenant_lookup = 'category__tenant_id'
    filter_fields = {'tenant_id': 'category__tenant_id', 'category_id': 'category_id', 'brand_id': 'brand_id'}

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(brand__tenant_id=self.request.user.profile.tenant_id)
        return qs
