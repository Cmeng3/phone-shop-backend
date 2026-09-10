from common.api import CatalogViewSet
from category.models import Category
from category.serializers import CategorySerializer


class CategoryViewSet(CatalogViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ['name', 'slug', 'description']
    filter_fields = {'tenant_id': 'tenant_id'}
