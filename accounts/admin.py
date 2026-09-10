from django.contrib import admin
from accounts.models import Profile, Role, RoleRequest

admin.site.register(Profile)
admin.site.register(Role)
admin.site.register(RoleRequest)
