from django.db import models
from common.models import TimeStampedModel
from common.utils import CategoryIdGenerator
from tenant.models import Tenant


# Create your models here.
class Category(TimeStampedModel):
    id = models.CharField(max_length=20, primary_key=True, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='categories', null=False, blank=False)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'category'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='category_shop_name'),
            models.UniqueConstraint(fields=['tenant', 'slug'], name='category_shop_slug'),
        ]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = CategoryIdGenerator.generate(Category)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.name}"
