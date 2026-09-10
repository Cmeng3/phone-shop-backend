from brand.models import Brand
from rest_framework import serializers
from tenant.models import Tenant
from common.serializers import TenantScopedSerializer

class BrandSerializer(TenantScopedSerializer):
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(),
        source='tenant',
        required=False,
    )

    class Meta:
        model = Brand
        fields = ['id', 'tenant_id', 'name', 'description', 'logo_url', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
