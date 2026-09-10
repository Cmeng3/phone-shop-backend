from common.api import CatalogViewSet
from product.models import Product
from product.serializers.product_serializer import ProductSerializer
from rest_framework.filters import SearchFilter, OrderingFilter


class ProductViewSet(CatalogViewSet):
    queryset = Product.objects.select_related('tenant', 'category', 'brand', 'product_line')
    serializer_class = ProductSerializer
    search_fields = ['name', 'sku', 'description']
    filter_backends = [SearchFilter, OrderingFilter]
    ordering_fields = ['name', 'price', 'stock', 'created_at', 'id']
    ordering = ['-created_at', '-id']
    filter_fields = {'tenant_id': 'tenant_id', 'category_id': 'category_id', 'brand_id': 'brand_id', 'status': 'status'}
