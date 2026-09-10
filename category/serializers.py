from category.models import Category
from rest_framework import serializers
from tenant.models import Tenant
from common.serializers import TenantScopedSerializer


class CategorySerializer(TenantScopedSerializer):
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(),
        source='tenant',
        write_only=False,
        allow_null=False,
        required=False,
    )

    class Meta:
        model = Category
        fields = ['id', 'tenant_id', 'name', 'slug', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
