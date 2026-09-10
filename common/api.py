from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from rest_framework import viewsets, filters
from rest_framework.exceptions import ValidationError
from common.permissions import CatalogAccess, confirm_password


class CatalogViewSet(viewsets.ModelViewSet):
    permission_classes = [CatalogAccess]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    tenant_lookup = 'tenant_id'
    filter_fields = {}

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError('Conflicting record or invalid relationship.')

    def perform_update(self, serializer):
        self.perform_create(serializer)

    def get_queryset(self):
        qs = super().get_queryset().order_by('-pk')
        if not self.request.user.is_superuser:
            qs = qs.filter(**{self.tenant_lookup: self.request.user.profile.tenant_id})
        if self.action == 'list' and 'stock' in [field.name for field in qs.model._meta.fields] and self.request.query_params.get('low_stock') == 'true':
            qs = qs.filter(stock__lte=5).exclude(status='ARCHIVED')
        for parameter, field in self.filter_fields.items():
            value = self.request.query_params.get(parameter)
            if value is not None:
                try:
                    qs = qs.filter(**{field: value})
                except (ValueError, TypeError):
                    raise ValidationError({parameter: 'Invalid filter value.'})
        return qs

    def perform_destroy(self, instance):
        if self.request.user.is_superuser:
            confirm_password(self.request)
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('Remove dependent records before deleting this record.')
