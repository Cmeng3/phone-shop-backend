from django.db import models


class StatusChoices(models.TextChoices):
    """
    Common status choices for models across the application.
    """
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    AVAILABLE = 'AVAILABLE', 'Available'
    UNAVAILABLE = 'UNAVAILABLE', 'Unavailable'
    ARCHIVED = 'ARCHIVED', 'Archived'
    DELETED = 'DELETED', 'Deleted'


# Aliases for convenience
Status = StatusChoices
StatusEnum = StatusChoices
