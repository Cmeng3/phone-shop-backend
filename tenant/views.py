from common.api import CatalogViewSet
from common.permissions import SuperAdmin
from tenant.models import Tenant
from tenant.serializers import TenantSerializer


class TenantViewSet(CatalogViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [SuperAdmin]
    filter_fields = {'status': 'status', 'type': 'type'}
