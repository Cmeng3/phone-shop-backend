from django.contrib.auth import get_user_model, logout
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, mixins, serializers, viewsets, filters
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import Profile, Role, RoleRequest
from accounts.serializers import ProfileSerializer, UserCreateSerializer, RoleSerializer, RoleRequestSerializer, check_password_strength
from common.api import CatalogViewSet
from common.permissions import SuperAdmin, confirm_password
from tenant.models import Tenant

User = get_user_model()


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_authenticate_header(self, request):
        return 'Token'

    def post(self, request):
        class Input(serializers.Serializer):
            identifier = serializers.CharField(max_length=254)
            password = serializers.CharField(trim_whitespace=False, max_length=1024)
        data = Input(data=request.data)
        data.is_valid(raise_exception=True)
        identifier = data.validated_data['identifier'].strip()
        phone = identifier.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        users = list(User.objects.filter(Q(username=identifier) | Q(email__iexact=identifier) | Q(profile__phone=phone)).distinct()[:2])
        user = users[0] if len(users) == 1 else None
        if user is None:
            User().set_password(data.validated_data['password'])
        valid = user is not None and user.check_password(data.validated_data['password'])
        if not valid or not user.is_active:
            raise AuthenticationFailed('Invalid credentials.')
        with transaction.atomic():
            # Serialize issuance with account state changes and token revocation.
            user = User.objects.select_for_update().get(pk=user.pk)
            if not user.is_active or not user.check_password(data.validated_data['password']):
                raise AuthenticationFailed('Invalid credentials.')
            token, _ = Token.objects.get_or_create(user=user)
        request.session.cycle_key()
        request.session['workspace_token'] = token.key
        return Response({'token': token.key, 'user': ProfileSerializer(user).data})


class LogoutView(APIView):
    def post(self, request):
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            Token.objects.filter(user=request.user).delete()
        logout(request)
        return Response({'detail': 'Logged out.'})


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


class PasswordView(APIView):
    def post(self, request):
        class Input(serializers.Serializer):
            current_password = serializers.CharField(trim_whitespace=False)
            new_password = serializers.CharField(trim_whitespace=False, max_length=1024)
        data = Input(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(data.validated_data['current_password']):
                raise ValidationError({'current_password': 'Incorrect password.'})
            check_password_strength(data.validated_data['new_password'], user)
            user.set_password(data.validated_data['new_password'])
            user.save(update_fields=['password'])
            Token.objects.filter(user=user).delete()
        logout(request)
        return Response({'detail': 'Password changed. Log in again.'})


class RoleViewSet(CatalogViewSet):
    permission_classes = [SuperAdmin]
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [SuperAdmin]
    queryset = User.objects.select_related('profile').order_by('pk')
    serializer_class = ProfileSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'profile__phone']

    def get_serializer_class(self):
        return UserCreateSerializer if self.action == 'create' else ProfileSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action != 'list':
            return qs
        role = self.request.query_params.get('role_id')
        status = self.request.query_params.get('status')
        if role:
            if not role.isascii() or not role.isdigit():
                raise ValidationError({'role_id': 'Expected an integer.'})
            qs = qs.filter(profile__role_id=role)
        if status:
            if status not in ['ACTIVE', 'BANNED']:
                raise ValidationError({'status': 'Use ACTIVE or BANNED.'})
            qs = qs.filter(is_active=status == 'ACTIVE')
        return qs

    def target(self):
        user = self.get_object()
        user = User.objects.select_for_update().get(pk=user.pk)
        if user.pk == self.request.user.pk or user.is_superuser:
            raise PermissionDenied('Super admin accounts cannot be changed through user management.')
        return user

    @action(detail=True, methods=['post'], url_path='change-role')
    @transaction.atomic
    def change_role(self, request, pk=None):
        confirm_password(request)
        user = self.target()
        class Input(serializers.Serializer):
            role_id = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())
            tenant_id = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False)
        data = Input(data=request.data)
        data.is_valid(raise_exception=True)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = data.validated_data['role_id']
        if 'tenant_id' in data.validated_data:
            profile.tenant = data.validated_data['tenant_id']
        if not profile.tenant_id:
            raise ValidationError({'tenant_id': 'Assign a shop before assigning a role.'})
        profile.save()
        Token.objects.filter(user=user).delete()
        return Response(ProfileSerializer(User.objects.get(pk=user.pk)).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def ban(self, request, pk=None):
        confirm_password(request)
        user = self.target()
        user.is_active = False
        user.save(update_fields=['is_active'])
        Token.objects.filter(user=user).delete()
        return Response({'detail': 'User banned.'})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def unban(self, request, pk=None):
        user = self.target()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': 'User unbanned.'})

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        confirm_password(request)
        self.target().delete()
        return Response(status=204)


class RoleRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = RoleRequestSerializer
    queryset = RoleRequest.objects.select_related('user', 'role').order_by('-pk')

    def get_permissions(self):
        return [SuperAdmin()] if self.action in ['approve', 'reject'] else [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        status = self.request.query_params.get('status')
        if status:
            if status not in ['PENDING', 'APPROVED', 'REJECTED']:
                raise ValidationError({'status': 'Invalid request status.'})
            qs = qs.filter(status=status)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        User.objects.select_for_update().get(pk=self.request.user.pk)
        if RoleRequest.objects.filter(user=self.request.user, status='PENDING').exists():
            raise ValidationError('You already have a pending request.')
        serializer.save(user=self.request.user)

    @transaction.atomic
    def decide(self, request, approved):
        item = self.get_object()
        user = User.objects.select_for_update().get(pk=item.user_id)
        item = RoleRequest.objects.select_for_update().get(pk=item.pk)
        if item.status != 'PENDING':
            raise ValidationError('This request was already reviewed.')
        if approved:
            profile = getattr(user, 'profile', None)
            if user.is_superuser or not user.is_active or not profile or not profile.tenant_id or profile.tenant.status != 'ACTIVE':
                raise ValidationError('User must be active and assigned to an active shop.')
            profile.role = item.role
            profile.save(update_fields=['role'])
            Token.objects.filter(user=user).delete()
        item.status = 'APPROVED' if approved else 'REJECTED'
        item.reviewed_by = request.user
        item.reviewed_at = timezone.now()
        item.save()
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self.decide(request, True)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self.decide(request, False)


class AvailableRolesView(generics.ListAPIView):
    queryset = Role.objects.all().order_by('name')
    serializer_class = RoleSerializer
