from rest_framework import serializers
from common.serializers import TenantScopedSerializer
from product.models import Product


class ProductSerializer(TenantScopedSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {'tenant': {'required': False}, 'price': {'min_value': 0}}

    def validate(self, attrs):
        attrs = super().validate(attrs)
        def value(name):
            return attrs.get(name, getattr(self.instance, name, None))
        tenant, category, brand, line = (value(n) for n in ('tenant', 'category', 'brand', 'product_line'))
        if category.tenant_id != tenant.pk or brand.tenant_id != tenant.pk:
            raise serializers.ValidationError('Product, category and brand must belong to the same shop.')
        if line and (line.category_id != category.pk or line.brand_id != brand.pk):
            raise serializers.ValidationError({'product_line': 'Product line must match category and brand.'})
        return attrs
