from tenant.models import Tenant


def get_all_tenants():
    return Tenant.objects.all().order_by('-created_at')


def get_tenant_by_id(tenant_id):
    try:
        return Tenant.objects.get(id=tenant_id)
    except (Tenant.DoesNotExist, ValueError):
        return None


def create_tenant(data: dict) -> Tenant:
    return Tenant.objects.create(**data)


def update_tenant(tenant: Tenant, data: dict) -> Tenant:
    for field, value in data.items():
        setattr(tenant, field, value)
    tenant.save()
    return tenant
