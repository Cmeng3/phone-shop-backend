from django.conf import settings
from django.db import models
from common.models import TimeStampedModel


class Role(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    can_manage_catalog = models.BooleanField(default=False)


class Profile(models.Model):
    email = models.EmailField(unique=True, null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=32, unique=True, null=True, blank=True)
    tenant = models.ForeignKey('tenant.Tenant', on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True, blank=True)


class RoleRequest(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reviewed_role_requests')
    reviewed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user'], condition=models.Q(status='PENDING'), name='one_pending_role_request')]
