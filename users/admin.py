from django.contrib import admin
from .models import User, RoleCounter

admin.site.register(User)
admin.site.register(RoleCounter)