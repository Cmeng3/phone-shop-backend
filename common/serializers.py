from rest_framework import serializers


class TenantScopedSerializer(serializers.ModelSerializer):
    def get_validators(self):
        # Tenant defaults are resolved in validate before checking composite keys.
        return []

    def validate(self, attrs):
        user = self.context['request'].user
        tenant = attrs.get('tenant', getattr(self.instance, 'tenant', None))
        if not user.is_superuser:
            if tenant and tenant.pk != user.profile.tenant_id:
                raise serializers.ValidationError({'tenant_id': 'Choose your own shop.'})
            tenant = user.profile.tenant
            attrs['tenant'] = tenant
        if tenant is None:
            raise serializers.ValidationError({'tenant_id': 'This field is required.'})
        if self.instance and tenant.pk != self.instance.tenant_id:
            raise serializers.ValidationError({'tenant_id': 'Shop ownership cannot be changed.'})
        attrs['tenant'] = tenant
        for constraint in self.Meta.model._meta.constraints:
            fields = getattr(constraint, 'fields', ())
            if fields and 'tenant' in fields:
                values = {field: attrs.get(field, getattr(self.instance, field, None)) for field in fields}
                query = self.Meta.model.objects.filter(**values)
                if self.instance:
                    query = query.exclude(pk=self.instance.pk)
                if query.exists():
                    raise serializers.ValidationError('A record with these values already exists in this shop.')
        return super().validate(attrs)
