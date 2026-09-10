from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from accounts.models import Profile, Role, RoleRequest
from tenant.models import Tenant

User = get_user_model()


def check_password_strength(password, user):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({'password': exc.messages})


class ProfileSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='profile.tenant.name', read_only=True, default=None)
    role_name = serializers.CharField(source='profile.role.name', read_only=True, default=None)
    can_manage_catalog = serializers.SerializerMethodField()

    def get_can_manage_catalog(self, user):
        from common.permissions import CatalogAccess
        request = type('ProfileRequest', (), {'user': user})()
        return CatalogAccess().has_permission(request, None)

    phone = serializers.CharField(source='profile.phone', required=False, allow_null=True, allow_blank=True, max_length=32)
    tenant_id = serializers.IntegerField(source='profile.tenant_id', read_only=True)
    role_id = serializers.IntegerField(source='profile.role_id', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'tenant_id', 'role_id', 'is_active', 'is_superuser', 'tenant_name', 'role_name', 'can_manage_catalog']
        read_only_fields = ['id', 'is_active', 'is_superuser']
        extra_kwargs = {'email': {'required': True, 'allow_blank': False}}

    def validate_email(self, value):
        value = value.strip().lower()
        users = User.objects.filter(email__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError('Email is already in use.')
        return value

    def validate_phone(self, value):
        if not value:
            return None
        # Store one canonical international representation.
        value = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not value.startswith('+') or not value[1:].isascii() or not value[1:].isdigit() or not 8 <= len(value[1:]) <= 15:
            raise serializers.ValidationError('Use international format, for example +85512345678.')
        profiles = Profile.objects.filter(phone=value)
        if self.instance:
            profiles = profiles.exclude(user=self.instance)
        if profiles.exists():
            raise serializers.ValidationError('Phone is already in use.')
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        instance = super().update(instance, validated_data)
        profile, _ = Profile.objects.get_or_create(user=instance)
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.email = instance.email.strip().lower() or None
        profile.save()
        return instance


class UserCreateSerializer(ProfileSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    tenant_id = serializers.PrimaryKeyRelatedField(source='profile.tenant', queryset=Tenant.objects.all())
    role_id = serializers.PrimaryKeyRelatedField(source='profile.role', queryset=Role.objects.all())

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + ['password']

    def validate(self, attrs):
        candidate = User(username=attrs.get('username'), email=attrs.get('email'))
        check_password_strength(attrs['password'], candidate)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, email=user.email, **profile_data)
        return user


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'can_manage_catalog', 'created_at', 'updated_at']


class RoleRequestSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    class Meta:
        model = RoleRequest
        fields = ['id', 'user', 'username', 'role', 'role_name', 'reason', 'status', 'reviewed_by', 'reviewed_at', 'created_at', 'updated_at']
        read_only_fields = ['user', 'status', 'reviewed_by', 'reviewed_at']
        validators = []

    def validate(self, attrs):
        user = self.context['request'].user
        if user.is_superuser:
            raise serializers.ValidationError('Super admins do not need catalog roles.')
        profile = getattr(user, 'profile', None)
        if not profile or not profile.tenant_id or profile.tenant.status != 'ACTIVE':
            raise serializers.ValidationError('An active shop assignment is required.')
        if profile.role_id == attrs['role'].pk:
            raise serializers.ValidationError('You already have this role.')
        if RoleRequest.objects.filter(user=user, status='PENDING').exists():
            raise serializers.ValidationError('You already have a pending request.')
        return attrs
