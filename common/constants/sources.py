from django.db import models


class SourceChoices(models.TextChoices):
    """
    Common source choices across the application.
    """
    BRAND = 'BRAND', 'Brand'
    CATEGORY = 'CATEGORY', 'Category'
    PRODUCT = 'PRODUCT', 'Product'
    PRODUCT_LINE = 'PRODUCT-LINE', 'Product-Line'
    TENANT = 'TENANT', 'Tenant'


# Aliases for convenience
Source = SourceChoices
SourceEnum = SourceChoices
