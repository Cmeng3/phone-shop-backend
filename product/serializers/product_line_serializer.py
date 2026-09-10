from rest_framework import serializers
from product.models import ProductLine
from category.models import Category
from brand.models import Brand


class ProductLineSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        category = attrs.get('category', getattr(self.instance, 'category', None))
        brand = attrs.get('brand', getattr(self.instance, 'brand', None))
        user = self.context['request'].user
        if category.tenant_id != brand.tenant_id:
            raise serializers.ValidationError('Category and brand must belong to the same shop.')
        if not user.is_superuser and category.tenant_id != user.profile.tenant_id:
            raise serializers.ValidationError('Choose records from your own shop.')
        if self.instance and category.tenant_id != self.instance.category.tenant_id:
            raise serializers.ValidationError('Shop ownership cannot be changed.')
        if self.instance and (category.pk != self.instance.category_id or brand.pk != self.instance.brand_id) and self.instance.products.exists():
            raise serializers.ValidationError('Detach products before changing a product line category or brand.')
        return attrs

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category'
    )
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(),
        source='brand'
    )

    class Meta:
        model = ProductLine
        fields = ['id', 'category_id', 'brand_id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
