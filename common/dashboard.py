from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from common.permissions import CatalogAccess
from product.models import Product
from product.serializers.product_serializer import ProductSerializer
from category.models import Category
from brand.models import Brand
from tenant.models import Tenant
from accounts.models import RoleRequest


class DashboardView(APIView):
    permission_classes = [CatalogAccess]

    def get(self, request):
        products = Product.objects.all()
        brands = Brand.objects.all()
        categories = Category.objects.all()
        requests = RoleRequest.objects.all()
        if not request.user.is_superuser:
            shop = request.user.profile.tenant_id
            products = products.filter(tenant_id=shop)
            brands = brands.filter(tenant_id=shop)
            categories = categories.filter(tenant_id=shop)
            requests = requests.filter(user=request.user)
        value = ExpressionWrapper(F('price') * F('stock'), output_field=DecimalField(max_digits=24, decimal_places=2))
        totals = products.aggregate(units=Sum('stock'), value=Sum(value))
        today = timezone.localdate()
        month_index = today.year * 12 + today.month - 1
        months = [date(index // 12, index % 12 + 1, 1) for index in range(month_index - 5, month_index + 1)]
        monthly = {row['month'].date(): row['count'] for row in products.filter(created_at__date__gte=months[0]).annotate(month=TruncMonth('created_at')).values('month').annotate(count=Count('id'))}
        distribution = list(products.values('category__name').annotate(count=Count('id')).order_by('-count', 'category__name'))
        data = {
            'products': products.count(), 'brands': brands.count(), 'categories': categories.count(),
            'units': totals['units'] or 0, 'inventory_value': str(totals['value'] or Decimal('0.00')),
            'low_stock': products.filter(stock__lte=5).exclude(status='ARCHIVED').count(),
            'pending_requests': requests.filter(status='PENDING').count(),
            'availability': [{'name': status.title(), 'count': products.filter(status=status).count()} for status in ['AVAILABLE', 'UNAVAILABLE', 'ARCHIVED']],
            'monthly_products': [{'month': month.strftime('%b'), 'period': month.isoformat(), 'count': monthly.get(month, 0)} for month in months],
            'category_distribution': [{'name': row['category__name'], 'count': row['count']} for row in distribution],
            'recent_products': ProductSerializer(products.select_related('brand', 'category', 'tenant').order_by('-created_at')[:5], many=True, context={'request': request}).data,
        }
        if request.user.is_superuser:
            data.update(tenants=Tenant.objects.count(), active_tenants=Tenant.objects.filter(status='ACTIVE').count(), users=get_user_model().objects.count())
        return Response(data)
