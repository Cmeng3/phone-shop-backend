from django.db import models
from common.models import TimeStampedModel
from common.utils import BrandIdGenerator
from common.constants.status import Status
from tenant.models import Tenant

class Brand(TimeStampedModel):
    STATUS_CHOICES = [
        (Status.ACTIVE.value, Status.ACTIVE.label),
        (Status.INACTIVE.value, Status.INACTIVE.label),
    ]

    id = models.CharField(max_length=20, primary_key=True, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='brands')
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    logo_url = models.ImageField(upload_to='brand_images/', blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=Status.ACTIVE.value
    )

    class Meta:
        db_table = 'brand'
        constraints = [models.UniqueConstraint(fields=['tenant', 'name'], name='brand_shop_name')]

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = BrandIdGenerator.generate(Brand)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.name}"
