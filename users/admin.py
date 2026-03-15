from django.contrib import admin
from .models import User, RoleCounter, TeacherProfile

admin.site.register(User)
admin.site.register(RoleCounter)
admin.site.register(TeacherProfile)
