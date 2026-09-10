# pyrefly: ignore [missing-import]
from common.models import TimeStampedModel
from django.db import models
from category.models import Category
from brand.models import Brand

class ProductLine(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='product_lines')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='product_lines')
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'product_line'
        unique_together = ('category', 'brand', 'name')

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    tenant = models.ForeignKey('tenant.Tenant', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    product_line = models.ForeignKey(ProductLine, on_delete=models.PROTECT, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('AVAILABLE', 'Available'), ('UNAVAILABLE', 'Unavailable'), ('ARCHIVED', 'Archived')], default='AVAILABLE')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'sku'], name='product_shop_sku'),
            models.CheckConstraint(condition=models.Q(price__gte=0), name='product_price_nonnegative'),
        ]
