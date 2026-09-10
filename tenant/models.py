from common.models import TimeStampedModel
from django.db import models
from common.constants import Status

# Create your models here.
class Tenant(TimeStampedModel):

    STATUS_CHOICES = [
        (Status.ACTIVE.value, Status.ACTIVE.label),
        (Status.INACTIVE.value, Status.INACTIVE.label),
    ]

    name = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=30)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=Status.ACTIVE.value
    )